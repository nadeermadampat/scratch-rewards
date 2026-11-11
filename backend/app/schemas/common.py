"""Response envelope shared by every endpoint."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """`{"success": true, "data": ...}`; errors use `{"success": false, "error": {...}}`."""

    success: bool = True
    data: T


def ok(data: T) -> ApiResponse[T]:
    return ApiResponse(data=data)
