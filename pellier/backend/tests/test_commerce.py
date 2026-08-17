"""Offline contracts for proof-carrying storefront commerce."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from models import VerifiedUser
from routes import commerce as commerce_routes
from services.cognito_auth import require_user
from services.commerce import CommerceError, CommerceService, SandboxPaymentAdapter


class _QuoteCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self._catalog_pending = False

    async def __aenter__(self) -> "_QuoteCursor":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def execute(self, query: str, params: Any = None) -> None:
        self.executed.append((query, params))
        self._catalog_pending = "FROM pellier.product_catalog pc" in query

    async def fetchall(self) -> list[dict[str, Any]]:
        if not self._catalog_pending:
            return []
        self._catalog_pending = False
        return [
            {
                "product_id": "7",
                "name": "Linen Field Jacket",
                "image_url": "/images/jacket.jpg",
                "price": Decimal("80.00"),
                "catalog_quantity": 9,
                "available_quantity": 9,
            }
        ]


class _QuoteConnection:
    def __init__(self) -> None:
        self.cursor_instance = _QuoteCursor()
        self.commits = 0

    def cursor(self) -> _QuoteCursor:
        return self.cursor_instance

    async def commit(self) -> None:
        self.commits += 1


class _QuoteDB:
    def __init__(self) -> None:
        self.connection = _QuoteConnection()

    @asynccontextmanager
    async def get_connection(self):
        yield self.connection


def test_quote_uses_catalog_price_and_deterministic_rules() -> None:
    db = _QuoteDB()
    quote = asyncio.run(
        CommerceService(db).create_quote(
            principal_sub="principal-1",
            lines=[{"product_id": 7, "quantity": 2}],
            now=datetime(2026, 8, 16, tzinfo=timezone.utc),
        )
    )

    assert quote["amounts"] == {
        "subtotal": "160.00",
        "shipping": "0.00",
        "tax": "13.20",
        "total": "173.20",
    }
    assert quote["rules"]["policy"] == "pellier-commerce-v1"
    assert quote["rules"]["paymentMode"] == "sandbox"
    assert len(quote["quoteHash"]) == 64
    assert db.connection.commits == 1
    inserts = [
        (query, params)
        for query, params in db.connection.cursor_instance.executed
        if "INSERT INTO pellier.commerce_quote_lines" in query
    ]
    assert inserts[0][1][4] == Decimal("80.00")


@pytest.mark.parametrize(
    ("configured", "expected_status", "expected_event"),
    [
        ("settled", "settled", "payment.settled"),
        ("declined", "declined", "payment.declined"),
        ("unknown", "failed", "payment.failed"),
    ],
)
def test_sandbox_payment_outcomes_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
    expected_status: str,
    expected_event: str,
) -> None:
    monkeypatch.setenv("PELLIER_SANDBOX_PAYMENT_OUTCOME", configured)
    result = asyncio.run(
        SandboxPaymentAdapter().settle(
            order_id=uuid4(),
            amount=Decimal("12.00"),
            currency="USD",
        )
    )

    assert result.status == expected_status
    assert result.event_type == expected_event
    assert result.provider_ref.startswith("sbx_")


def test_migration_defines_durable_append_only_evidence() -> None:
    repo = Path(__file__).resolve().parents[3]
    sql = (
        repo / "scripts" / "migrations" / "015_proof_carrying_commerce.sql"
    ).read_text()

    for table in (
        "commerce_quotes",
        "commerce_confirmation_grants",
        "commerce_orders",
        "commerce_inventory_reservations",
        "commerce_payment_attempts",
        "commerce_payment_events",
        "commerce_outbox",
        "commerce_receipts",
    ):
        assert f"CREATE TABLE IF NOT EXISTS pellier.{table}" in sql
    assert "commerce_payment_events_append_only" in sql
    assert "commerce_receipts_append_only" in sql
    assert "UNIQUE (principal_sub, idempotency_key)" in sql
    assert "'reservation'" in sql and "'release'" in sql


class _RouteService:
    def __init__(self) -> None:
        self.quote_call: dict[str, Any] | None = None

    async def create_quote(self, **kwargs: Any) -> dict[str, Any]:
        self.quote_call = kwargs
        return {
            "quoteId": str(uuid4()),
            "quoteHash": "a" * 64,
            "status": "open",
        }


def test_quote_route_requires_identity_and_forwards_verified_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = FastAPI()
    api.include_router(commerce_routes.router)
    anonymous = TestClient(api)
    assert anonymous.post(
        "/api/commerce/quotes",
        json={"lines": [{"productId": 7, "quantity": 1}]},
    ).status_code == 401

    route_service = _RouteService()
    monkeypatch.setattr(commerce_routes, "_service", lambda _db: route_service)
    api.dependency_overrides[require_user] = lambda: VerifiedUser(
        user_id="principal-1",
        email="shopper@example.com",
        given_name="Shopper",
    )
    api.dependency_overrides[commerce_routes.get_db_service] = lambda: object()
    response = TestClient(api).post(
        "/api/commerce/quotes",
        json={
            "lines": [{"productId": 7, "quantity": 2}],
            "sessionId": "session-1",
        },
    )

    assert response.status_code == 201
    assert route_service.quote_call == {
        "principal_sub": "principal-1",
        "lines": [{"product_id": 7, "quantity": 2}],
        "session_id": "session-1",
        "turn_id": None,
    }


class _ReceiptDB:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row
        self.params: tuple[Any, ...] | None = None

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any]:
        assert "r.principal_sub = %s" in query
        self.params = params
        return self.row


class _ExistingOrderDB:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any]:
        assert "FROM pellier.commerce_orders" in query
        return self.row


def test_idempotency_key_cannot_cross_confirmation_grants() -> None:
    service = CommerceService(
        _ExistingOrderDB(
            {
                "order_id": uuid4(),
                "status": "paid",
                "confirmation_grant_id": uuid4(),
            }
        )
    )

    with pytest.raises(CommerceError, match="idempotency_key_reused") as error:
        asyncio.run(
            service.execute_order(
                principal_sub="principal-1",
                confirmation_grant_id=uuid4(),
                idempotency_key="checkout-reused-key",
            )
        )

    assert error.value.status_code == 409


def test_receipt_read_is_scoped_to_same_verified_principal() -> None:
    order_id = uuid4()
    row = {
        "order_id": order_id,
        "order_number": "PEL-ABC12345",
        "status": "paid",
        "payment_status": "settled",
        "currency": "USD",
        "subtotal": Decimal("80.00"),
        "shipping": Decimal("12.00"),
        "tax": Decimal("6.60"),
        "total": Decimal("98.60"),
        "created_at": datetime(2026, 8, 16, tzinfo=timezone.utc),
        "receipt_id": uuid4(),
        "receipt_hash": "b" * 64,
        "receipt_created_at": datetime(2026, 8, 16, tzinfo=timezone.utc),
        "evidence": {
            "payment": {
                "provider": "pellier-sandbox",
                "mode": "sandbox",
                "status": "settled",
            }
        },
    }
    db = _ReceiptDB(row)
    result = asyncio.run(
        CommerceService(db).get_receipt(
            principal_sub="principal-1",
            order_id=order_id,
        )
    )

    assert db.params == (order_id, "principal-1", "principal-1")
    assert result["payment"]["mode"] == "sandbox"
    assert result["receipt"]["receiptHash"] == "b" * 64
    assert result["receipt"]["verified"] is False


class _NoCommitConnection:
    """Keep service commits inside the integration test's outer transaction."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def cursor(self):
        return self.connection.cursor()

    async def commit(self) -> None:
        return None


class _LiveTransactionDB:
    def __init__(self, connection: Any) -> None:
        self.connection = connection
        self.proxy = _NoCommitConnection(connection)

    @asynccontextmanager
    async def get_connection(self):
        yield self.proxy

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any] | None:
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchone()


@pytest.mark.skipif(
    not os.environ.get("PELLIER_LIVE_POSTGRES_URL"),
    reason="set PELLIER_LIVE_POSTGRES_URL for rollback-only SQL proof",
)
def test_live_commerce_transaction_and_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        connection = await psycopg.AsyncConnection.connect(
            os.environ["PELLIER_LIVE_POSTGRES_URL"],
            row_factory=dict_row,
        )
        try:
            await connection.execute("BEGIN")
            await connection.execute(
                """
                CREATE SCHEMA pellier;
                CREATE TABLE pellier.product_catalog (
                    "productId" TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    "imgUrl" TEXT,
                    price NUMERIC(10,2) NOT NULL,
                    quantity INTEGER NOT NULL,
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb
                );
                CREATE TABLE pellier.warehouses (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE pellier.warehouse_inventory (
                    warehouse_id TEXT NOT NULL
                        REFERENCES pellier.warehouses(id),
                    product_id TEXT NOT NULL
                        REFERENCES pellier.product_catalog("productId"),
                    quantity INTEGER NOT NULL CHECK (quantity >= 0),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (warehouse_id, product_id)
                );
                CREATE TABLE pellier.inventory_ledger (
                    entry_id BIGSERIAL PRIMARY KEY,
                    product_id TEXT NOT NULL
                        REFERENCES pellier.product_catalog("productId"),
                    warehouse_id TEXT,
                    delta INTEGER NOT NULL CHECK (delta <> 0),
                    reason TEXT NOT NULL
                        CHECK (reason IN (
                            'restock', 'return_damaged', 'return_resellable',
                            'sale', 'seed', 'adjustment'
                        )),
                    idempotency_key TEXT,
                    principal_sub TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE UNIQUE INDEX inventory_ledger_idempotency_idx
                    ON pellier.inventory_ledger (idempotency_key, product_id)
                    WHERE idempotency_key IS NOT NULL;
                INSERT INTO pellier.product_catalog
                    ("productId", name, "imgUrl", price, quantity)
                VALUES ('7', 'Linen Field Jacket', '/jacket.jpg', 80.00, 4);
                INSERT INTO pellier.warehouses (id) VALUES ('BK-01');
                INSERT INTO pellier.warehouse_inventory
                    (warehouse_id, product_id, quantity)
                VALUES ('BK-01', '7', 4);
                INSERT INTO pellier.inventory_ledger (
                    product_id, warehouse_id, delta, reason, idempotency_key
                )
                VALUES ('7', 'BK-01', 4, 'seed', 'seed:BK-01:7');
                """
            )
            migration_path = (
                Path(__file__).resolve().parents[3]
                / "scripts"
                / "migrations"
                / "015_proof_carrying_commerce.sql"
            )
            migration = "\n".join(
                line
                for line in migration_path.read_text().splitlines()
                if not line.startswith("\\")
                and line.strip() not in {"BEGIN;", "COMMIT;"}
            )
            await connection.execute(migration)

            db = _LiveTransactionDB(connection)
            service = CommerceService(db)
            quote = await service.create_quote(
                principal_sub="principal-live",
                lines=[{"product_id": 7, "quantity": 2}],
            )
            grant = await service.confirm_quote(
                principal_sub="principal-live",
                quote_id=UUID(quote["quoteId"]),
                quote_hash=quote["quoteHash"],
                acknowledged=True,
            )
            receipt = await service.execute_order(
                principal_sub="principal-live",
                confirmation_grant_id=UUID(grant["confirmationGrantId"]),
                idempotency_key="checkout-live-fixed-key",
            )
            replay = await service.execute_order(
                principal_sub="principal-live",
                confirmation_grant_id=UUID(grant["confirmationGrantId"]),
                idempotency_key="checkout-live-fixed-key",
            )

            assert receipt["status"] == "paid"
            assert replay["orderId"] == receipt["orderId"]
            assert receipt["receipt"]["verified"] is True
            assert receipt["evidence"]["order"]["lines"] == [
                {
                    "productId": 7,
                    "name": "Linen Field Jacket",
                    "unitPrice": "80.00",
                    "quantity": 2,
                    "lineTotal": "160.00",
                }
            ]
            assert receipt["evidence"]["inventory"]["status"] == "captured"
            assert receipt["evidence"]["inventory"]["ledgerEntryIds"]
            row = await db.fetch_one(
                """
                SELECT pc.quantity AS catalog_quantity, wi.quantity AS warehouse_quantity
                  FROM pellier.product_catalog pc
                  JOIN pellier.warehouse_inventory wi
                    ON wi.product_id = pc."productId"
                 WHERE pc."productId" = '7'
                """
            )
            assert row == {"catalog_quantity": 2, "warehouse_quantity": 2}

            monkeypatch.setenv("PELLIER_SANDBOX_PAYMENT_OUTCOME", "declined")
            declined_quote = await service.create_quote(
                principal_sub="principal-live",
                lines=[{"product_id": 7, "quantity": 1}],
            )
            declined_grant = await service.confirm_quote(
                principal_sub="principal-live",
                quote_id=UUID(declined_quote["quoteId"]),
                quote_hash=declined_quote["quoteHash"],
                acknowledged=True,
            )
            declined = await service.execute_order(
                principal_sub="principal-live",
                confirmation_grant_id=UUID(
                    declined_grant["confirmationGrantId"]
                ),
                idempotency_key="checkout-live-declined",
            )
            assert declined["status"] == "payment_declined"
            assert declined["evidence"]["inventory"]["status"] == "released"
            restored = await db.fetch_one(
                """
                SELECT pc.quantity AS catalog_quantity, wi.quantity AS warehouse_quantity
                  FROM pellier.product_catalog pc
                  JOIN pellier.warehouse_inventory wi
                    ON wi.product_id = pc."productId"
                 WHERE pc."productId" = '7'
                """
            )
            assert restored == {"catalog_quantity": 2, "warehouse_quantity": 2}
        finally:
            await connection.rollback()
            await connection.close()

    asyncio.run(run())
