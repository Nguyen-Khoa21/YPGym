from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.exceptions import AppError, ConflictError, register_exception_handlers
from app.core.logging import add_request_logging


class ExamplePayload(BaseModel):
    name: str = Field(min_length=2, max_length=20)


def build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    add_request_logging(app)

    @app.get("/conflict")
    async def conflict():
        raise ConflictError("This record has already changed.", {"field": "status"})

    @app.post("/validate")
    async def validate(payload: ExamplePayload):
        return payload

    return app


def test_app_error_initializes_the_base_exception() -> None:
    error = AppError("EXAMPLE", "Useful exception message.", 409)

    assert str(error) == "Useful exception message."
    assert error.args == ("Useful exception message.",)


@pytest.mark.asyncio
async def test_app_error_mapping_preserves_safe_payload_and_request_id() -> None:
    request_id = str(uuid4())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=build_app()),
        base_url="http://test",
    ) as client:
        response = await client.get("/conflict", headers={"x-request-id": request_id})

    assert response.status_code == 409
    assert response.headers["x-request-id"] == request_id
    assert response.json() == {
        "error": {
            "code": "CONFLICT",
            "message": "This record has already changed.",
            "details": {"field": "status"},
        }
    }


@pytest.mark.asyncio
async def test_validation_mapping_keeps_fields_without_echoing_submitted_values() -> None:
    private_value = "PRIVATE_SUBMITTED_VALUE_123"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=build_app()),
        base_url="http://test",
    ) as client:
        response = await client.post("/validate", json={"name": private_value})

    assert response.status_code == 422
    payload = response.json()["error"]
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["details"][0]["loc"] == ["body", "name"]
    assert set(payload["details"][0]) == {"type", "loc", "msg"}
    assert private_value not in response.text
    assert response.headers.get("x-request-id")
