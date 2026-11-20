import json
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import HTTPException, status

from app.db.database import database, utc_now


_Result = TypeVar("_Result")


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _credit_balance(connection: Any, user_id: str) -> int:
    row = connection.execute(
        "SELECT COALESCE(SUM(delta), 0) AS balance FROM business_credit_ledger WHERE user_id=?",
        (user_id,),
    ).fetchone()
    return int(row["balance"])


def ensure_monthly_credits(connection: Any, user_id: str) -> int:
    month = _month_key()
    ledger_key = f"monthly-grant:{month}"
    existing = connection.execute(
        "SELECT id FROM business_credit_ledger WHERE user_id=? AND idempotency_key=?",
        (user_id, ledger_key),
    ).fetchone()
    if existing is None:
        plan = connection.execute(
            """
            SELECT p.credits_grant FROM business_subscriptions s
            JOIN business_plans p ON p.id=s.plan_id
            WHERE s.user_id=? AND s.status='active'
            ORDER BY s.updated_at DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if plan:
            grant = int(plan["credits_grant"])
        else:
            setting = connection.execute(
                "SELECT setting_value FROM business_settings WHERE setting_key='free_monthly_credits'"
            ).fetchone()
            grant = int(setting["setting_value"]) if setting else 20
        if grant > 0:
            balance = _credit_balance(connection, user_id) + grant
            connection.execute(
                "INSERT INTO business_credit_ledger"
                "(id, user_id, delta, balance_after, entry_type, operation, idempotency_key, created_at) "
                "VALUES (?, ?, ?, ?, 'monthly_grant', 'monthly_allowance', ?, ?)",
                (str(uuid.uuid4()), user_id, grant, balance, ledger_key, utc_now()),
            )
    return _credit_balance(connection, user_id)


def reserve_ai_operation(user_id: str, operation: str, *, idempotency_key: str) -> dict[str, Any]:
    with database(immediate=True) as connection:
        cost_row = connection.execute(
            "SELECT credit_cost, enabled, required_entitlement "
            "FROM business_operation_pricing WHERE operation=?",
            (operation,),
        ).fetchone()
        if cost_row is None or not cost_row["enabled"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI operation '{operation}' is not currently priced or enabled.",
            )
        required_entitlement = cost_row["required_entitlement"]
        if required_entitlement:
            subscription = connection.execute(
                """
                SELECT p.entitlement_json FROM business_subscriptions s
                JOIN business_plans p ON p.id=s.plan_id
                WHERE s.user_id=? AND s.status='active'
                ORDER BY s.updated_at DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            one_time_plans = connection.execute(
                """
                SELECT p.entitlement_json FROM business_transactions t
                JOIN business_plans p ON p.id=t.plan_id
                WHERE t.user_id=? AND t.status='captured' AND t.purpose='one_time'
                """,
                (user_id,),
            ).fetchall()
            entitlement_sets = [
                json.loads(row["entitlement_json"] or "{}")
                for row in ([subscription] if subscription else []) + one_time_plans
            ]
            if not any(bool(entitlements.get(required_entitlement)) for entitlements in entitlement_sets):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "message": "Your current plan does not include this AI feature.",
                        "required_entitlement": required_entitlement,
                    },
                )
        cost = int(cost_row["credit_cost"])
        existing = connection.execute(
            "SELECT id, credits, status FROM business_credit_reservations "
            "WHERE user_id=? AND idempotency_key=?",
            (user_id, idempotency_key),
        ).fetchone()
        if existing:
            return {
                "reservation_id": existing["id"],
                "credits": int(existing["credits"]),
                "status": existing["status"],
                "balance": _credit_balance(connection, user_id),
            }
        balance = ensure_monthly_credits(connection, user_id)
        pending = connection.execute(
            "SELECT COALESCE(SUM(credits), 0) AS reserved FROM business_credit_reservations "
            "WHERE user_id=? AND status='reserved'",
            (user_id,),
        ).fetchone()["reserved"]
        if balance - int(pending) < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "message": "Your AI credit balance is insufficient for this request.",
                    "required_credits": cost,
                    "available_credits": max(0, balance - int(pending)),
                },
            )
        reservation_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO business_credit_reservations"
            "(id, user_id, operation, idempotency_key, credits, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'reserved', ?, ?)",
            (reservation_id, user_id, operation, idempotency_key, cost, now, now),
        )
        return {
            "reservation_id": reservation_id,
            "credits": cost,
            "status": "reserved",
            "balance": balance,
        }


def complete_ai_operation(user_id: str, reservation_id: str, *, reference_id: str) -> int:
    with database(immediate=True) as connection:
        reservation = connection.execute(
            "SELECT * FROM business_credit_reservations WHERE id=? AND user_id=?",
            (reservation_id, user_id),
        ).fetchone()
        if reservation is None:
            raise HTTPException(status_code=404, detail="AI credit reservation was not found.")
        if reservation["status"] == "completed":
            return _credit_balance(connection, user_id)
        if reservation["status"] != "reserved":
            raise HTTPException(status_code=409, detail="AI credit reservation is no longer active.")
        balance = _credit_balance(connection, user_id)
        if balance < int(reservation["credits"]):
            raise HTTPException(status_code=409, detail="AI credit balance changed before usage settlement.")
        next_balance = balance - int(reservation["credits"])
        connection.execute(
            "INSERT INTO business_credit_ledger"
            "(id, user_id, delta, balance_after, entry_type, operation, idempotency_key, "
            "reference_id, created_at) VALUES (?, ?, ?, ?, 'ai_usage', ?, ?, ?, ?)",
            (
                str(uuid.uuid4()), user_id, -int(reservation["credits"]), next_balance,
                reservation["operation"], reservation["idempotency_key"],
                reference_id, utc_now(),
            ),
        )
        connection.execute(
            "UPDATE business_credit_reservations SET status='completed', updated_at=? WHERE id=?",
            (utc_now(), reservation_id),
        )
        return next_balance


def release_ai_operation(user_id: str, reservation_id: str) -> None:
    with database(immediate=True) as connection:
        connection.execute(
            "UPDATE business_credit_reservations SET status='released', updated_at=? "
            "WHERE id=? AND user_id=? AND status='reserved'",
            (utc_now(), reservation_id, user_id),
        )


async def run_charged_ai_operation(
    user_id: str,
    operation: str,
    action: Callable[[], Awaitable[_Result]],
) -> _Result:
    reservation = reserve_ai_operation(
        user_id,
        operation,
        idempotency_key=f"{operation}:{uuid.uuid4()}",
    )
    succeeded = False
    try:
        result = await action()
        succeeded = True
        return result
    finally:
        if succeeded:
            complete_ai_operation(
                user_id,
                reservation["reservation_id"],
                reference_id=reservation["reservation_id"],
            )
        else:
            release_ai_operation(user_id, reservation["reservation_id"])
