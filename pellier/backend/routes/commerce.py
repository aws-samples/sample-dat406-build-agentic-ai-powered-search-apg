"""Authenticated proof-carrying commerce API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from models import VerifiedUser
from services.cognito_auth import require_user
from services.commerce import CommerceError, CommerceService

router = APIRouter(prefix="/api/commerce", tags=["commerce"])


async def get_db_service() -> Any:
    from app import get_db_service as _app_get_db_service

    return await _app_get_db_service()


class CommerceModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class CartLineRequest(CommerceModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=20)


class QuoteRequest(CommerceModel):
    lines: list[CartLineRequest] = Field(min_length=1, max_length=10)
    session_id: str | None = Field(default=None, max_length=128)
    turn_id: str | None = Field(default=None, max_length=128)


class ConfirmQuoteRequest(CommerceModel):
    quote_hash: str = Field(min_length=64, max_length=64)
    acknowledged: bool

    @field_validator("quote_hash")
    @classmethod
    def validate_quote_hash(cls, value: str) -> str:
        lowered = value.lower()
        if any(character not in "0123456789abcdef" for character in lowered):
            raise ValueError("quoteHash must be a SHA-256 hex digest")
        return lowered


class ExecuteOrderRequest(CommerceModel):
    confirmation_grant_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)


def _service(db: Any) -> CommerceService:
    return CommerceService(db)


def _http_error(error: CommerceError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.code)


@router.post("/quotes", status_code=201)
async def create_quote(
    payload: QuoteRequest,
    user: VerifiedUser = Depends(require_user),
    db: Any = Depends(get_db_service),
) -> dict[str, Any]:
    try:
        return await _service(db).create_quote(
            principal_sub=user.user_id,
            lines=[
                {"product_id": line.product_id, "quantity": line.quantity}
                for line in payload.lines
            ],
            session_id=payload.session_id,
            turn_id=payload.turn_id,
        )
    except CommerceError as error:
        raise _http_error(error) from error


@router.post("/quotes/{quote_id}/confirm", status_code=201)
async def confirm_quote(
    quote_id: UUID,
    payload: ConfirmQuoteRequest,
    user: VerifiedUser = Depends(require_user),
    db: Any = Depends(get_db_service),
) -> dict[str, Any]:
    try:
        return await _service(db).confirm_quote(
            principal_sub=user.user_id,
            quote_id=quote_id,
            quote_hash=payload.quote_hash,
            acknowledged=payload.acknowledged,
        )
    except CommerceError as error:
        raise _http_error(error) from error


@router.post("/orders", status_code=201)
async def execute_order(
    payload: ExecuteOrderRequest,
    user: VerifiedUser = Depends(require_user),
    db: Any = Depends(get_db_service),
) -> dict[str, Any]:
    try:
        return await _service(db).execute_order(
            principal_sub=user.user_id,
            confirmation_grant_id=payload.confirmation_grant_id,
            idempotency_key=payload.idempotency_key,
        )
    except CommerceError as error:
        raise _http_error(error) from error


@router.get("/orders/{order_id}/receipt")
async def get_order_receipt(
    order_id: UUID,
    user: VerifiedUser = Depends(require_user),
    db: Any = Depends(get_db_service),
) -> dict[str, Any]:
    try:
        return await _service(db).get_receipt(
            principal_sub=user.user_id,
            order_id=order_id,
        )
    except CommerceError as error:
        raise _http_error(error) from error
