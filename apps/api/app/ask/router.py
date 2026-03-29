from fastapi import APIRouter
from pydantic import BaseModel

from app.ask.service import ask_question

router = APIRouter(prefix="/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str


@router.post("")
async def ask_endpoint(request: AskRequest):
    """Ask a natural language question about the payment data."""
    result = await ask_question(request.question)
    return result
