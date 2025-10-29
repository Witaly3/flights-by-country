import json
from typing import Any
from openai import AsyncOpenAI

from app.config import settings

# Настраиваем асинхронный клиент
client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


async def get_answer_from_llm(question: str, flight_data: list[dict[str, Any]], airport_code: str) -> str:
    """
    Асинхронно отправляет вопрос и данные в LLM для получения ответа.
    """
    if not flight_data:
        return "К сожалению, не удалось получить данные о рейсах. Попробуйте позже."

    flight_data_str = json.dumps(flight_data, indent=2, ensure_ascii=False)

    prompt = f"""
    You are an expert flight data analyst. Your task is to answer user questions based *only* on the provided JSON data for the airport {airport_code}.
    Do not use any external knowledge or make assumptions. If the data does not contain the answer, state that clearly.
    The data contains both 'arrival' and 'departure' flights. Pay close attention to the 'type' field.

    Here is the flight data:
    {flight_data_str}

    User's question: "{question}"
    """

    try:
        response = await client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[
                {"role": "system", "content": "You are a helpful flight data analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return "Произошла ошибка при обработке вашего вопроса. Пожалуйста, попробуйте снова."
