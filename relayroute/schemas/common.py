"""Consistent error response shape."""
from pydantic import BaseModel


class APIError(BaseModel):
    error: str
    detail: str
