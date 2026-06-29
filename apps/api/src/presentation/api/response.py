from typing import Any

from fastapi.responses import JSONResponse


def ok(
    data: Any,
    message: str = "",
    request_id: str = "",
    status_code: int = 200,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "message": message,
            "request_id": request_id,
        },
    )


def paginated(
    data: list[Any],
    total: int,
    page: int,
    limit: int,
    message: str = "",
    request_id: str = "",
) -> JSONResponse:
    total_pages = max(1, -(-total // limit))
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": data,
            "message": message,
            "request_id": request_id,
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
    )
