from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


class ExecuteRequest(BaseModel):
    sql: str


class FeedbackRequest(BaseModel):
    query_id: str
    rating: Literal["correct", "incorrect"]
    note: str = ""
