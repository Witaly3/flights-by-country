import asyncio
import aiohttp
from typing import Any
from datetime import datetime, timezone
from async_lru import alru_cache

from app.config import settings

FLIGHT_API_BASE_URL = "https://api.flightapi.io/schedule"


def convert_timestamp(ts: int | None) -> str | None:
    """Конвертирует UNIX timestamp в читаемую строку времени ISO 8601."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z') if ts else None


@alru_cache(maxsize=12, ttl=600)
async def get_flight_data(airport_code: str) -> list[dict[str, Any]]:
    """
    Асинхронно получает данные о прибывающих и убывающих рейсах для аэропорта.
    Результаты кэшируются на 10 минут.
    """
    print(f"🚀 Fetching new data from API for {airport_code}")

    tasks = [
        fetch_schedule(airport_code, 'arrival'),
        fetch_schedule(airport_code, 'departure')
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_flights = []
    for result in results:
        if isinstance(result, Exception):
            print(f"An error occurred during API fetch: {result}")
        else:
            all_flights.extend(result)

    return all_flights


async def fetch_schedule(airport_code: str, flight_type: str) -> list[dict[str, Any]]:
    """Вспомогательная функция для выполнения одного запроса к API"""

    url = f"{FLIGHT_API_BASE_URL}/{settings.FLIGHT_API_KEY}"
    api_mode = "arrivals" if flight_type == "arrival" else "departures"
    res = []

    params = {"mode": api_mode, "iata": airport_code, "day": "1"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                print(f"Raw API response for {airport_code} {flight_type}: {data.keys() if isinstance(data, dict) else "not a dict"}")

                if "error" in data:
                    print(f"API returned an error for {airport_code} ({flight_type}): {data["error"]}")
                    return []

                plugin_data = data.get("airport", {}).get("pluginData", {})
                schedule_data = plugin_data.get('schedule', {}).get(api_mode, {}).get("data", [])

                print(f"Found {len(schedule_data)} schedule items")

                flights_list = []
                for item in schedule_data:
                    if flight := item.get("flight"):
                        flights_list.append(flight)
                    else:
                        print(f"Warning: No flight data in item: {item.keys()}")

                print(f"Extracted {len(flights_list)} flights")
                res = simplify_flight_data(flights_list, flight_type)

        except aiohttp.ClientError as e:
            print(f"Error fetching {flight_type} data for {airport_code}: {e}")
        except Exception as e:
            print(f"Unexpected error processing {flight_type} data for {airport_code}: {e}")
        finally:
            return res


def simplify_flight_data(flights: list[dict], flight_type: str) -> list[dict]:
    """
    Упрощает структуру данных о рейсах с обработкой отсутствующих данных.
    """
    simplified_flights = []

    for flight in flights:
        try:
            # Базовая информация о рейсе
            identification = flight.get('identification', {})
            airline_info = flight.get('airline', {})
            status_info = flight.get('status', {})
            aircraft_info = flight.get('aircraft', {})
            airport_info = flight.get('airport', {})
            time_info = flight.get('time', {})

            record = {
                "type": flight_type,
                "flightNumber": identification.get('number', {}).get('default'),
                "airline": airline_info.get('name') if airline_info else None,  # Безопасная проверка
                "status": status_info.get('text'),
                "aircraftModel": aircraft_info.get('model', {}).get('text'),
            }

            if flight_type == 'arrival':
                origin = airport_info.get('origin', {})
                origin_position = origin.get('position', {})
                origin_region = origin_position.get('region', {}) if origin_position else {}
                origin_country = origin_position.get('country', {}) if origin_position else {}

                record.update({
                    "originAirport": origin.get('name'),
                    "originCity": origin_region.get('city') if origin_region else None,
                    "originCountry": origin_country.get('name') if origin_country else None,
                    "scheduledTime": convert_timestamp(time_info.get('scheduled', {}).get('arrival'))
                })
            else:  # departure
                destination = airport_info.get('destination', {})
                destination_position = destination.get('position', {})
                destination_region = destination_position.get('region', {}) if destination_position else {}
                destination_country = destination_position.get('country', {}) if destination_position else {}

                record.update({
                    "destinationAirport": destination.get('name'),
                    "destinationCity": destination_region.get('city') if destination_region else None,
                    "destinationCountry": destination_country.get('name') if destination_country else None,
                    "scheduledTime": convert_timestamp(time_info.get('scheduled', {}).get('departure'))
                })

            simplified_flights.append(record)

        except Exception as e:
            print(f"Error processing flight record: {e}")
            print(f"Problematic flight data keys: {list(flight.keys()) if isinstance(flight, dict) else 'not a dict'}")
            continue

    return simplified_flights