#!/usr/bin/env python3
"""Read a small slice of the Pellier catalog with the backend DB driver.

This is intentionally tiny: it gives workshop verification steps a clean
snake_case ``product_id`` column without shell-escaping the legacy
``"productId"`` catalog column.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_env() -> None:
    for env_path in (_repo_root() / ".env", _repo_root() / "pellier" / "backend" / ".env"):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'\"")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _connect() -> psycopg.Connection[Any]:
    return psycopg.connect(
        host=_require("DB_HOST"),
        port=os.environ.get("DB_PORT", "5432"),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
        dbname=_require("DB_NAME"),
        row_factory=dict_row,
    )


def _fetch_rows(*, product_id: str | None, name_like: str | None, limit: int) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    if product_id:
        clauses.append("product_id = %s")
        params.append(product_id)
    if name_like:
        clauses.append("name ILIKE %s")
        params.append(f"%{name_like}%")
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    sql = f"""
        SELECT product_id, name, quantity
        FROM pellier.product_catalog
        {where_sql}
        ORDER BY
          CASE WHEN product_id ~ '^[0-9]+$' THEN product_id::int END NULLS LAST,
          product_id
        LIMIT %s;
    """
    params.append(limit)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def _print_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No matching catalog rows.")
        return
    headers = ("product_id", "name", "quantity")
    widths = {
        key: max(len(key), *(len(str(row[key])) for row in rows))
        for key in headers
    }
    print(" | ".join(key.ljust(widths[key]) for key in headers))
    print("-+-".join("-" * widths[key] for key in headers))
    for row in rows:
        print(" | ".join(str(row[key]).ljust(widths[key]) for key in headers))


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Pellier catalog rows by product id or name.")
    parser.add_argument("--product-id", help="Exact product_id to read, for example 37.")
    parser.add_argument("--name-like", help="Case-insensitive product name fragment.")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    _load_env()
    rows = _fetch_rows(product_id=args.product_id, name_like=args.name_like, limit=max(1, args.limit))
    _print_rows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
