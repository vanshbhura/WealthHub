from typing import Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class StandardErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
