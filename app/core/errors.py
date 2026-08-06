from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException


def problem(
    status_code: int,
    message: str,
    field_errors: dict[str, str] | None = None,
) -> NoReturn:
    detail: dict[str, object] = {"message": message}
    if field_errors:
        detail["field_errors"] = field_errors
    raise HTTPException(status_code=status_code, detail=detail)

