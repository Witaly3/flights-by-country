from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .models import QueryRequest, QueryResponse
from .services.flight_api_client import get_flight_data
from .services.llm_service import get_answer_from_llm

app = FastAPI(title="Flights by Country Assistant")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse('app/static/index.html')


@app.post("/api/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    valid_airports = {"DXB", "LHR", "CDG", "SIN", "HKG", "AMS"}
    if request.airport not in valid_airports:
        raise HTTPException(status_code=400, detail="Неверный код аэропорта.")

    flight_data = await get_flight_data(request.airport)
    answer = await get_answer_from_llm(request.question, flight_data, request.airport)

    return QueryResponse(answer=answer)
