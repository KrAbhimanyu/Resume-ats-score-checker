import hashlib
import hmac
import base64
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException, Request as FastAPIRequest, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import settings
from app.db.database import database, utc_now
from app.services.business_billing import ensure_monthly_credits
from app.services.data_protection import protect_text, reveal_text
from app.services.job_auth import current_user


router = APIRouter()
_RAZORPAY_API = "https://api.razorpay.com/v1"
_STRIPE_API = "https://api.stripe.com/v1"
_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AUD", "CAD", "SGD"}
_MARKETPLACE_TYPES = {"resume_review", "career_coaching", "resume_template"}


class PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=2, max_length=80, pattern="^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(..., min_length=2, max_length=100)
    tier: str = Field(..., pattern="^(starter|pro|premium|student|enterprise)$")
    billing_interval: str = Field(..., pattern="^(monthly|yearly|one_time)$")
    price_minor: int = Field(..., ge=1, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    credits_grant: int = Field(default=0, ge=0, le=1_000_000)
    entitlements: dict[str, Any] = Field(default_factory=dict)
    active: bool = True

    @model_validator(mode="after")
    def validate_currency_and_price(self) -> "PlanInput":
        self.currency = self.currency.upper()
        if self.currency not in _CURRENCIES:
            raise ValueError("Unsupported payment currency.")
        if self.billing_interval in {"monthly", "yearly"} and self.price_minor <= 0:
            raise ValueError("Paid subscription plans require a positive price.")
        return self


class CheckoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(..., min_length=2, max_length=80)
    coupon_code: Optional[str] = Field(default=None, max_length=60)


class VerifyPaymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    razorpay_order_id: str = Field(..., min_length=3, max_length=100)
    razorpay_payment_id: str = Field(..., min_length=3, max_length=100)
    razorpay_signature: str = Field(..., min_length=20, max_length=256)


class VerifySubscriptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    razorpay_subscription_id: str = Field(..., min_length=3, max_length=100)
    razorpay_payment_id: str = Field(..., min_length=3, max_length=100)
    razorpay_signature: str = Field(..., min_length=20, max_length=256)


class StripeCheckoutVerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., min_length=10, max_length=200, pattern="^cs_(test|live)_[A-Za-z0-9]+$")


class CouponInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=3, max_length=60, pattern="^[A-Za-z0-9_-]+$")
    discount_type: str = Field(..., pattern="^(percent|fixed)$")
    discount_value: int = Field(..., gt=0, le=100_000_000)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    max_redemptions: Optional[int] = Field(default=None, ge=1, le=10_000_000)
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_discount(self) -> "CouponInput":
        if self.currency:
            self.currency = self.currency.upper()
            if self.currency not in _CURRENCIES:
                raise ValueError("Unsupported coupon currency.")
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("Percentage discounts cannot exceed 100.")
        if self.discount_type == "fixed" and not self.currency:
            raise ValueError("Fixed discounts require a currency.")
        return self

    @field_validator("expires_at")
    @classmethod
    def require_timezone_on_expiry(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Coupon expiration must include a timezone.")
        return value


class OperationPricingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credit_cost: int = Field(..., ge=1, le=1_000_000)
    enabled: bool = True
    required_entitlement: Optional[str] = Field(
        default=None, min_length=2, max_length=80, pattern="^[a-z][a-z0-9_]*$"
    )


class ReferralInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=6, max_length=40)


class LeadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_type: str = Field(..., pattern="^(student|enterprise|recruitment|university)$")
    organization: str = Field(..., min_length=2, max_length=200)
    details: str = Field(default="", max_length=4000)


class AffiliateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(default="", max_length=2000)


class MarketplaceListingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_type: str = Field(..., pattern="^(resume_review|career_coaching|resume_template)$")
    title: str = Field(..., min_length=4, max_length=160)
    description: str = Field(..., min_length=20, max_length=5000)
    price_minor: int = Field(..., gt=0, le=10_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_currency(self) -> "MarketplaceListingInput":
        self.currency = self.currency.upper()
        if self.currency not in _CURRENCIES:
            raise ValueError("Unsupported payment currency.")
        return self


class MarketplaceOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: str = Field(default="", max_length=4000)


class MarketplaceOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., pattern="^(in_progress|completed|cancelled|disputed)$")
    note: str = Field(default="", max_length=2000)


class AdminStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., pattern="^(approved|rejected|suspended|reviewing|declined|closed)$")
    commission_basis_points: Optional[int] = Field(default=None, ge=0, le=10000)


class BusinessSettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    free_monthly_credits: int = Field(..., ge=0, le=1_000_000)
    referral_reward_credits: int = Field(..., ge=0, le=1_000_000)


class SubscriptionPlanChangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(..., min_length=2, max_length=80)


class RefundInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=500)


class AffiliateConversionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., pattern="^(approved|reversed)$")


def _admin_user(user: dict[str, str] = Depends(current_user)) -> dict[str, str]:
    allowlist = {
        email.strip().casefold()
        for email in settings.BUSINESS_ADMIN_EMAILS.split(",")
        if email.strip()
    }
    if not allowlist or user["email"].casefold() not in allowlist:
        raise HTTPException(status_code=403, detail="Business administrator access is not configured for this account.")
    return user


def _require_gateway() -> None:
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        raise HTTPException(
            status_code=503,
            detail="Payment checkout is not configured. A merchant administrator must configure Razorpay credentials.",
        )


def _stripe_configured() -> bool:
    urls = (settings.BUSINESS_CHECKOUT_SUCCESS_URL, settings.BUSINESS_CHECKOUT_CANCEL_URL)
    if not settings.STRIPE_SECRET_KEY or "{CHECKOUT_SESSION_ID}" not in urls[0]:
        return False
    for value in urls:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            return False
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            return False
    return True


def _select_payment_provider(currency: str, *, recurring: bool = False) -> str:
    razorpay_configured = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    razorpay_ready = razorpay_configured and (
        not recurring or bool(settings.RAZORPAY_WEBHOOK_SECRET)
    )
    stripe_ready = _stripe_configured() and (
        not recurring or bool(settings.STRIPE_WEBHOOK_SECRET)
    )
    if currency == "INR" and razorpay_ready:
        return "razorpay"
    if stripe_ready:
        return "stripe"
    if currency == "INR" and razorpay_configured:
        return "razorpay"
    if _stripe_configured():
        return "stripe"
    raise HTTPException(
        status_code=503,
        detail="Checkout is not configured for this currency. Configure Razorpay for INR or Stripe with trusted return URLs for international checkout.",
    )


def _require_subscription_webhook() -> None:
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Recurring billing is unavailable until the merchant configures the signed Razorpay webhook.",
        )


def _require_provider_webhook(provider: str) -> None:
    if provider == "stripe":
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=503,
                detail="Stripe recurring billing is unavailable until a signed webhook secret is configured.",
            )
        return
    _require_subscription_webhook()


def _razorpay_request(path: str, *, method: str = "GET", payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    _require_gateway()
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{_RAZORPAY_API}{path}",
        data=body,
        headers={
            "Authorization": "Basic " + base64.b64encode(
                f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
            ).decode(),
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="The payment provider rejected or could not complete this request.",
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The payment provider is currently unreachable. Try again later.",
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail="The payment provider returned an invalid response.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="The payment provider returned an invalid response.")
    return result


def _stripe_request(
    path: str,
    *,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured.")
    body = urlencode(payload or {}).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": "Basic " + base64.b64encode(
            f"{settings.STRIPE_SECRET_KEY}:".encode()
        ).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(
        f"{_STRIPE_API}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Stripe rejected or could not complete this request.",
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Stripe is currently unreachable. Try again later.",
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Stripe returned an invalid response.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Stripe returned an invalid response.")
    return result


def _is_stripe_checkout_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "checkout.stripe.com"
        and not parsed.username
        and not parsed.password
    )


def _stripe_checkout_session(
    *,
    user: dict[str, str],
    name: str,
    amount_minor: int,
    currency: str,
    transaction_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    billing_interval: Optional[str] = None,
) -> dict[str, Any]:
    if not _stripe_configured():
        raise HTTPException(
            status_code=503,
            detail="Stripe requires backend credentials and trusted success/cancel URLs.",
        )
    recurring = billing_interval in {"monthly", "yearly"}
    metadata = {
        key: value
        for key, value in {
            "transaction_id": transaction_id,
            "subscription_id": subscription_id,
            "user_id": user["id"],
        }.items()
        if value
    }
    payload: dict[str, Any] = {
        "mode": "subscription" if recurring else "payment",
        "success_url": settings.BUSINESS_CHECKOUT_SUCCESS_URL,
        "cancel_url": settings.BUSINESS_CHECKOUT_CANCEL_URL,
        "client_reference_id": transaction_id or subscription_id,
        "customer_email": user["email"],
        "expires_at": int((datetime.now(timezone.utc) + timedelta(minutes=35)).timestamp()),
        "line_items[0][price_data][currency]": currency.lower(),
        "line_items[0][price_data][unit_amount]": amount_minor,
        "line_items[0][price_data][product_data][name]": name[:200],
        "line_items[0][quantity]": 1,
    }
    for key, value in metadata.items():
        payload[f"metadata[{key}]"] = value
    if recurring:
        payload["line_items[0][price_data][recurring][interval]"] = (
            "month" if billing_interval == "monthly" else "year"
        )
        payload["subscription_data[metadata][subscription_id]"] = str(subscription_id)
        payload["subscription_data[metadata][user_id]"] = user["id"]
        payload["subscription_data[metadata][plan_id]"] = str(plan_id)
    return _stripe_request("/checkout/sessions", method="POST", payload=payload)


def _row_dict(row: Any) -> dict[str, Any]:
    result = dict(row)
    for key in ("entitlement_json",):
        if key in result:
            result["entitlements"] = json.loads(result.pop(key) or "{}")
    return result


def _verify_signature(message: str, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _stripe_period(value: Any) -> Optional[str]:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _verify_stripe_webhook_signature(body: bytes, signature_header: Optional[str]) -> bool:
    if not signature_header or not settings.STRIPE_WEBHOOK_SECRET:
        return False
    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        key, separator, value = item.partition("=")
        if separator:
            parts.setdefault(key, []).append(value)
    timestamps = parts.get("t", [])
    signatures = parts.get("v1", [])
    if not timestamps or not signatures:
        return False
    try:
        timestamp = int(timestamps[0])
    except ValueError:
        return False
    if abs(datetime.now(timezone.utc).timestamp() - timestamp) > 300:
        return False
    signed_payload = str(timestamp).encode("ascii") + b"." + body
    expected = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return any(hmac.compare_digest(expected, signature) for signature in signatures)


def _new_referral_code() -> str:
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "").upper()


def _business_setting(connection: Any, key: str, fallback: int) -> int:
    row = connection.execute(
        "SELECT setting_value FROM business_settings WHERE setting_key=?",
        (key,),
    ).fetchone()
    return int(row["setting_value"]) if row else fallback


def _award_credits(
    connection: Any,
    *,
    user_id: str,
    delta: int,
    entry_type: str,
    operation: str,
    idempotency_key: str,
    reference_id: Optional[str] = None,
) -> int:
    existing = connection.execute(
        "SELECT balance_after FROM business_credit_ledger WHERE user_id=? AND idempotency_key=?",
        (user_id, idempotency_key),
    ).fetchone()
    if existing:
        return int(existing["balance_after"])
    balance = int(connection.execute(
        "SELECT COALESCE(SUM(delta), 0) AS balance FROM business_credit_ledger WHERE user_id=?",
        (user_id,),
    ).fetchone()["balance"])
    next_balance = balance + delta
    connection.execute(
        "INSERT INTO business_credit_ledger"
        "(id, user_id, delta, balance_after, entry_type, operation, idempotency_key, reference_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()), user_id, delta, next_balance, entry_type, operation,
            idempotency_key, reference_id, utc_now(),
        ),
    )
    return next_balance


def _settle_captured_transaction(connection: Any, transaction: Any, payment_id: str) -> None:
    now = utc_now()
    cursor = connection.execute(
        "UPDATE business_transactions SET provider_payment_id=?, status='captured', captured_at=?, updated_at=? "
        "WHERE id=? AND status='created' AND provider_payment_id IS NULL",
        (payment_id, now, now, transaction["id"]),
    )
    if cursor.rowcount == 0:
        current = connection.execute(
            "SELECT status, provider_payment_id FROM business_transactions WHERE id=?",
            (transaction["id"],),
        ).fetchone()
        if current and current["provider_payment_id"] == payment_id and current["status"] == "captured":
            return
        raise HTTPException(status_code=409, detail="This payment transaction has already been processed.")
    connection.execute(
        "INSERT OR IGNORE INTO business_payment_attempts"
        "(id, transaction_id, provider_payment_id, status, created_at) "
        "VALUES (?, ?, ?, 'captured', ?)",
        (str(uuid.uuid4()), transaction["id"], payment_id, now),
    )

    if transaction["purpose"] in {"credits", "one_time"}:
        credits = connection.execute(
            "SELECT credits_grant FROM business_plans WHERE id=?",
            (transaction["plan_id"],),
        ).fetchone()
        if credits and int(credits["credits_grant"]) > 0:
            _award_credits(
                connection, user_id=transaction["user_id"], delta=int(credits["credits_grant"]),
                entry_type="purchase", operation="credit_package",
                idempotency_key=f"purchase:{transaction['id']}", reference_id=transaction["id"],
            )
    if transaction["marketplace_order_id"]:
        connection.execute(
            "UPDATE business_marketplace_orders SET status='paid', updated_at=? "
            "WHERE id=? AND status='pending_payment'",
            (now, transaction["marketplace_order_id"]),
        )
        connection.execute(
            "INSERT INTO business_marketplace_events(id, order_id, actor_user_id, event_type, note, created_at) "
            "VALUES (?, ?, ?, 'payment_captured', '', ?)",
            (str(uuid.uuid4()), transaction["marketplace_order_id"], transaction["user_id"], now),
        )
    if transaction["coupon_id"]:
        coupon = connection.execute(
            "SELECT * FROM business_coupons WHERE id=?", (transaction["coupon_id"],)
        ).fetchone()
        redemption = connection.execute(
            "UPDATE business_coupon_redemptions SET status='redeemed' "
            "WHERE transaction_id=? AND user_id=? AND status='pending'",
            (transaction["id"], transaction["user_id"]),
        )
        if coupon is None or redemption.rowcount != 1:
            raise HTTPException(status_code=409, detail="Coupon reservation could not be settled for this payment.")
        connection.execute(
            "UPDATE business_coupons SET redemption_count=redemption_count+1 WHERE id=?",
            (coupon["id"],),
        )

    referral = connection.execute(
        "SELECT r.* FROM business_referrals r WHERE r.referred_user_id=? AND r.status='pending'",
        (transaction["user_id"],),
    ).fetchone()
    if referral:
        connection.execute(
            "UPDATE business_referrals SET status='qualified', qualified_transaction_id=?, updated_at=? "
            "WHERE id=? AND status='pending'",
            (transaction["id"], now, referral["id"]),
        )
        reward = _business_setting(connection, "referral_reward_credits", 50)
        if reward > 0:
            _award_credits(
                connection, user_id=referral["referrer_user_id"], delta=reward,
                entry_type="referral_reward", operation="qualified_referral",
                idempotency_key=f"referral:{referral['id']}", reference_id=transaction["id"],
            )
        connection.execute(
            "UPDATE business_referrals SET status='rewarded', reward_credits=? WHERE id=?",
            (reward, referral["id"]),
        )
    affiliate = connection.execute(
        "SELECT a.user_id, a.commission_basis_points FROM business_affiliates a "
        "JOIN business_referrals r ON r.referrer_user_id=a.user_id "
        "WHERE r.referred_user_id=? AND a.status='approved'",
        (transaction["user_id"],),
    ).fetchone()
    if affiliate:
        commission = int(transaction["amount_minor"]) * int(affiliate["commission_basis_points"]) // 10000
        connection.execute(
            "INSERT OR IGNORE INTO business_affiliate_conversions"
            "(id, affiliate_user_id, referred_user_id, transaction_id, commission_minor, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (
                str(uuid.uuid4()), affiliate["user_id"], transaction["user_id"],
                transaction["id"], commission, now,
            ),
        )


def _record_subscription_payment(
    connection: Any,
    subscription: Any,
    payment: dict[str, Any],
) -> None:
    payment_id = payment.get("id")
    if payment.get("status") != "captured" or not isinstance(payment_id, str):
        return
    if payment.get("subscription_id") != subscription["provider_subscription_id"]:
        return
    plan = connection.execute(
        "SELECT id, currency FROM business_plans WHERE id=?",
        (subscription["plan_id"],),
    ).fetchone()
    if plan is None or payment.get("currency") != plan["currency"]:
        return
    amount = payment.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return
    now = utc_now()
    provider_order_id = f"sub:{subscription['provider_subscription_id']}:{payment_id}"
    connection.execute(
        """
        INSERT OR IGNORE INTO business_transactions
        (id, user_id, plan_id, provider, provider_order_id, amount_minor, currency,
         status, purpose, created_at, updated_at)
        VALUES (?, ?, ?, 'razorpay', ?, ?, ?, 'created', 'subscription', ?, ?)
        """,
        (
            str(uuid.uuid4()), subscription["user_id"], subscription["plan_id"],
            provider_order_id, amount, plan["currency"], now, now,
        ),
    )
    transaction = connection.execute(
        "SELECT * FROM business_transactions WHERE provider_order_id=? AND user_id=?",
        (provider_order_id, subscription["user_id"]),
    ).fetchone()
    if transaction and transaction["status"] == "created":
        _settle_captured_transaction(connection, transaction, payment_id)


def _record_stripe_subscription_payment(
    connection: Any,
    subscription: Any,
    invoice: dict[str, Any],
) -> None:
    invoice_id = invoice.get("id")
    amount = invoice.get("amount_paid")
    payment_intent = invoice.get("payment_intent")
    payment_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
    if not isinstance(invoice_id, str) or not invoice_id or not isinstance(amount, int) or amount <= 0:
        return
    if not isinstance(payment_id, str) or not payment_id:
        payment_id = invoice_id
    plan = connection.execute(
        "SELECT id, currency FROM business_plans WHERE id=?",
        (subscription["plan_id"],),
    ).fetchone()
    if plan is None or invoice.get("currency", "").upper() != plan["currency"]:
        return
    now = utc_now()
    provider_order_id = f"stripe-invoice:{invoice_id}"
    connection.execute(
        """
        INSERT OR IGNORE INTO business_transactions
        (id, user_id, plan_id, provider, provider_order_id, amount_minor, currency,
         status, purpose, created_at, updated_at)
        VALUES (?, ?, ?, 'stripe', ?, ?, ?, 'created', 'subscription', ?, ?)
        """,
        (
            str(uuid.uuid4()), subscription["user_id"], subscription["plan_id"],
            provider_order_id, amount, plan["currency"], now, now,
        ),
    )
    transaction = connection.execute(
        "SELECT * FROM business_transactions WHERE provider_order_id=? AND user_id=?",
        (provider_order_id, subscription["user_id"]),
    ).fetchone()
    if transaction and transaction["status"] == "created":
        _settle_captured_transaction(connection, transaction, payment_id)


@router.get("/business/status", tags=["Business and Revenue"])
def business_status(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    razorpay_configured = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    stripe_configured = _stripe_configured()
    with database() as connection:
        return {
            "payment_provider": (
                "multiple" if razorpay_configured and stripe_configured
                else "razorpay" if razorpay_configured
                else "stripe" if stripe_configured
                else None
            ),
            "checkout_configured": razorpay_configured or stripe_configured,
            "webhook_configured": bool(
                settings.RAZORPAY_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET
            ),
            "checkout_providers": {
                "razorpay": razorpay_configured,
                "stripe": stripe_configured,
            },
            "webhook_providers": {
                "razorpay": bool(settings.RAZORPAY_WEBHOOK_SECRET),
                "stripe": bool(settings.STRIPE_WEBHOOK_SECRET),
            },
            "admin": user["email"].casefold() in {
                email.strip().casefold() for email in settings.BUSINESS_ADMIN_EMAILS.split(",") if email.strip()
            },
            "active_plans": connection.execute(
                "SELECT COUNT(*) AS count FROM business_plans WHERE active=1 AND price_minor IS NOT NULL"
            ).fetchone()["count"],
            "currency_options": sorted(_CURRENCIES),
            "billing_note": "Payment and subscription status is confirmed by the provider API or signed webhook, never by browser status alone.",
        }


@router.get("/business/plans", tags=["Business and Revenue"])
def list_plans(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM business_plans WHERE active=1 ORDER BY tier, billing_interval, name"
        ).fetchall()
    return [_row_dict(row) for row in rows]


@router.get("/business/entitlements", tags=["Business and Revenue"])
def get_entitlements(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database(immediate=True) as connection:
        plan = connection.execute(
            """
            SELECT s.id AS subscription_id, s.status, s.provider, s.current_period_end, s.cancel_at_period_end,
                p.id AS plan_id, p.name, p.tier, p.billing_interval, p.entitlement_json, p.credits_grant
            FROM business_subscriptions s JOIN business_plans p ON p.id=s.plan_id
            WHERE s.user_id=? AND s.status='active'
            ORDER BY s.updated_at DESC LIMIT 1
            """,
            (user["id"],),
        ).fetchone()
        balance = ensure_monthly_credits(connection, user["id"])
        one_time_rows = connection.execute(
            """
            SELECT p.entitlement_json FROM business_transactions t
            JOIN business_plans p ON p.id=t.plan_id
            WHERE t.user_id=? AND t.status='captured' AND t.purpose='one_time'
            """,
            (user["id"],),
        ).fetchall()
        purchased_features: dict[str, Any] = {}
        for item in one_time_rows:
            purchased_features.update(json.loads(item["entitlement_json"] or "{}"))
        if plan:
            entitlements = json.loads(plan["entitlement_json"] or "{}")
            entitlements.update(purchased_features)
            return {
                "plan": {
                    "id": plan["plan_id"], "name": plan["name"], "tier": plan["tier"],
                    "billing_interval": plan["billing_interval"],
                },
                "status": plan["status"],
                "provider": plan["provider"],
                "current_period_end": plan["current_period_end"],
                "cancel_at_period_end": bool(plan["cancel_at_period_end"]),
                "features": entitlements,
                "credit_balance": balance,
                "free_tier": False,
            }
    return {
        "plan": {"id": "free", "name": "Free", "tier": "free", "billing_interval": "free"},
        "status": "active",
        "current_period_end": None,
        "cancel_at_period_end": False,
        "features": {"career_workspace": True, **purchased_features},
        "credit_balance": balance,
        "free_tier": True,
    }


@router.get("/business/credits", tags=["Business and Revenue"])
def get_credit_account(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database(immediate=True) as connection:
        balance = ensure_monthly_credits(connection, user["id"])
        rows = connection.execute(
            "SELECT delta, balance_after, entry_type, operation, reference_id, created_at "
            "FROM business_credit_ledger WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
        pending = connection.execute(
            "SELECT COALESCE(SUM(credits), 0) AS credits FROM business_credit_reservations "
            "WHERE user_id=? AND status='reserved'",
            (user["id"],),
        ).fetchone()["credits"]
    return {
        "balance": balance,
        "reserved": pending,
        "available": max(0, balance - int(pending)),
        "transactions": [dict(row) for row in rows],
    }


@router.post("/business/checkout", status_code=201, tags=["Business and Revenue"])
def create_checkout(
    payload: CheckoutInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database(immediate=True) as connection:
        connection.execute(
            """
            UPDATE business_coupon_redemptions SET status='released'
            WHERE status='pending' AND transaction_id IN (
                SELECT id FROM business_transactions
                WHERE status='created' AND (
                    (provider='stripe' AND created_at < datetime('now', '-40 minutes'))
                    OR (provider!='stripe' AND created_at < datetime('now', '-15 minutes'))
                )
            )
            """
        )
        plan = connection.execute(
            "SELECT * FROM business_plans WHERE id=? AND active=1",
            (payload.plan_id,),
        ).fetchone()
        if plan is None or plan["price_minor"] is None or int(plan["price_minor"]) <= 0:
            raise HTTPException(status_code=404, detail="This paid plan is not currently available.")
        if plan["billing_interval"] in {"monthly", "yearly"}:
            raise HTTPException(
                status_code=422,
                detail="Recurring plans must use the subscription checkout flow.",
            )
        provider = _select_payment_provider(plan["currency"])
        coupon_id = None
        discount_minor = 0
        amount = int(plan["price_minor"])
        if payload.coupon_code:
            coupon = connection.execute(
                "SELECT * FROM business_coupons WHERE code=? COLLATE NOCASE AND active=1",
                (payload.coupon_code.strip(),),
            ).fetchone()
            active_redemptions = (
                connection.execute(
                    "SELECT COUNT(*) AS count FROM business_coupon_redemptions "
                    "WHERE coupon_id=? AND status IN ('pending', 'redeemed')",
                    (coupon["id"],),
                ).fetchone()["count"]
                if coupon else 0
            )
            if (
                coupon is None
                or (coupon["expires_at"] and coupon["expires_at"] <= utc_now())
                or (
                    coupon["max_redemptions"] is not None
                    and active_redemptions >= coupon["max_redemptions"]
                )
                or (coupon["currency"] and coupon["currency"] != plan["currency"])
            ):
                raise HTTPException(status_code=422, detail="Coupon is invalid, expired, exhausted, or not valid for this currency.")
            if connection.execute(
                "SELECT id FROM business_coupon_redemptions "
                "WHERE coupon_id=? AND user_id=? AND status IN ('pending', 'redeemed') LIMIT 1",
                (coupon["id"], user["id"]),
            ).fetchone():
                raise HTTPException(status_code=409, detail="This coupon has already been used by your account.")
            discount_minor = (
                amount * int(coupon["discount_value"]) // 100
                if coupon["discount_type"] == "percent"
                else int(coupon["discount_value"])
            )
            discount_minor = min(amount, discount_minor)
            amount -= discount_minor
            coupon_id = coupon["id"]
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Coupon discount cannot reduce a paid checkout to zero.")
        transaction_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO business_transactions"
            "(id, user_id, plan_id, provider, amount_minor, currency, status, coupon_id, discount_minor, purpose, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'created', ?, ?, ?, ?, ?)",
            (
                transaction_id, user["id"], plan["id"], provider, amount, plan["currency"],
                coupon_id, discount_minor,
                "one_time" if plan["billing_interval"] == "one_time" else "credits",
                now, now,
            ),
        )
        if coupon_id:
            connection.execute(
                "INSERT INTO business_coupon_redemptions"
                "(id, coupon_id, user_id, transaction_id, discount_minor, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'pending', ?) "
                "ON CONFLICT(coupon_id, user_id) DO UPDATE SET "
                "transaction_id=excluded.transaction_id, discount_minor=excluded.discount_minor, "
                "status='pending', created_at=excluded.created_at "
                "WHERE business_coupon_redemptions.status='released'",
                (
                    str(uuid.uuid4()), coupon_id, user["id"], transaction_id,
                    discount_minor, now,
                ),
            )

    if provider == "stripe":
        try:
            session = _stripe_checkout_session(
                user=user,
                name=plan["name"],
                amount_minor=amount,
                currency=plan["currency"],
                transaction_id=transaction_id,
            )
        except HTTPException:
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                    (utc_now(), transaction_id),
                )
                connection.execute(
                    "UPDATE business_coupon_redemptions SET status='released' WHERE transaction_id=? AND status='pending'",
                    (transaction_id,),
                )
            raise
        if not isinstance(session.get("id"), str) or not _is_stripe_checkout_url(session.get("url")):
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                    (utc_now(), transaction_id),
                )
                connection.execute(
                    "UPDATE business_coupon_redemptions SET status='released' WHERE transaction_id=? AND status='pending'",
                    (transaction_id,),
                )
            raise HTTPException(status_code=502, detail="Stripe did not return a valid Checkout Session.")
        with database(immediate=True) as connection:
            connection.execute(
                "UPDATE business_transactions SET provider_order_id=?, updated_at=? WHERE id=? AND user_id=?",
                (session["id"], utc_now(), transaction_id, user["id"]),
            )
        return {
            "provider": "stripe",
            "checkout_url": session["url"],
            "session_id": session["id"],
            "amount": amount,
            "currency": plan["currency"],
            "transaction_id": transaction_id,
        }

    _require_gateway()
    expire_by = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
    try:
        order = _razorpay_request(
            "/orders",
            method="POST",
            payload={
                "amount": amount,
                "currency": plan["currency"],
                "receipt": transaction_id[:40],
                "expire_by": expire_by,
                "notes": {"transaction_id": transaction_id, "user_id": user["id"], "plan_id": plan["id"]},
            },
        )
    except HTTPException:
        with database(immediate=True) as connection:
            connection.execute(
                "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                (utc_now(), transaction_id),
            )
            connection.execute(
                "UPDATE business_coupon_redemptions SET status='released' WHERE transaction_id=? AND status='pending'",
                (transaction_id,),
            )
        raise
    if not isinstance(order.get("id"), str):
        with database(immediate=True) as connection:
            connection.execute(
                "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                (utc_now(), transaction_id),
            )
            connection.execute(
                "UPDATE business_coupon_redemptions SET status='released' WHERE transaction_id=? AND status='pending'",
                (transaction_id,),
            )
        raise HTTPException(status_code=502, detail="Payment provider did not return a valid order reference.")
    with database(immediate=True) as connection:
        connection.execute(
            "UPDATE business_transactions SET provider_order_id=?, updated_at=? WHERE id=? AND user_id=?",
            (order["id"], utc_now(), transaction_id, user["id"]),
        )
    return {
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": amount,
        "currency": plan["currency"],
        "name": "Career Platform",
        "description": plan["name"],
        "transaction_id": transaction_id,
        "callback": "Verify payment with the server; a browser callback alone does not activate access.",
    }


@router.post("/business/checkout/verify", tags=["Business and Revenue"])
def verify_checkout(
    payload: VerifyPaymentInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_gateway()
    if not _verify_signature(
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}",
        payload.razorpay_signature,
        settings.RAZORPAY_KEY_SECRET,
    ):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")
    order = _razorpay_request(f"/orders/{payload.razorpay_order_id}")
    payment = _razorpay_request(f"/payments/{payload.razorpay_payment_id}")
    if (
        payment.get("order_id") != payload.razorpay_order_id
        or payment.get("status") != "captured"
        or order.get("status") not in {"paid", "attempted"}
        or int(payment.get("amount", -1)) != int(order.get("amount", -2))
        or payment.get("currency") != order.get("currency")
    ):
        raise HTTPException(status_code=409, detail="The provider has not confirmed a captured payment for this order.")
    with database(immediate=True) as connection:
        transaction = connection.execute(
            "SELECT * FROM business_transactions WHERE provider_order_id=? AND user_id=?",
            (payload.razorpay_order_id, user["id"]),
        ).fetchone()
        if transaction is None or int(transaction["amount_minor"]) != int(payment["amount"]):
            raise HTTPException(status_code=404, detail="Payment order was not found for this account.")
        if transaction["purpose"] == "subscription":
            raise HTTPException(
                status_code=409,
                detail="Recurring subscription payments must be verified through subscription checkout.",
            )
        _settle_captured_transaction(connection, transaction, payload.razorpay_payment_id)
        subscription = connection.execute(
            "SELECT id, status FROM business_subscriptions WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
    return {"status": "captured", "transaction_id": transaction["id"], "subscription": dict(subscription) if subscription else None}


@router.post("/business/stripe/checkout/verify", tags=["Business and Revenue"])
def verify_stripe_checkout(
    payload: StripeCheckoutVerifyInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured.")
    with database() as connection:
        owned_transaction = connection.execute(
            "SELECT id FROM business_transactions WHERE provider_order_id=? AND user_id=? AND provider='stripe'",
            (payload.session_id, user["id"]),
        ).fetchone()
        owned_subscription = connection.execute(
            "SELECT id FROM business_subscriptions WHERE provider_checkout_session_id=? AND user_id=? AND provider='stripe'",
            (payload.session_id, user["id"]),
        ).fetchone()
    if owned_transaction is None and owned_subscription is None:
        raise HTTPException(status_code=404, detail="Checkout Session was not found for this account.")
    session = _stripe_request(f"/checkout/sessions/{payload.session_id}")
    if session.get("id") != payload.session_id or session.get("status") != "complete":
        raise HTTPException(status_code=409, detail="Stripe has not completed this Checkout Session.")
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=409, detail="Stripe has not confirmed payment for this Checkout Session.")

    metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    if session.get("mode") == "payment":
        payment_intent = session.get("payment_intent")
        payment_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
        if not isinstance(payment_id, str) or not payment_id:
            raise HTTPException(status_code=409, detail="Stripe did not return a confirmed payment reference.")
        with database(immediate=True) as connection:
            transaction = connection.execute(
                "SELECT * FROM business_transactions WHERE provider_order_id=? AND user_id=? AND provider='stripe'",
                (payload.session_id, user["id"]),
            ).fetchone()
            if (
                transaction is None
                or metadata.get("transaction_id") != transaction["id"]
                or metadata.get("user_id") != user["id"]
                or session.get("client_reference_id") != transaction["id"]
                or session.get("currency", "").upper() != transaction["currency"]
                or session.get("amount_total") != int(transaction["amount_minor"])
            ):
                raise HTTPException(status_code=404, detail="Checkout Session was not found for this account.")
            if transaction["purpose"] == "subscription":
                raise HTTPException(status_code=409, detail="Use subscription Checkout for recurring payments.")
            _settle_captured_transaction(connection, transaction, payment_id)
        return {"status": "captured", "transaction_id": transaction["id"]}

    if session.get("mode") == "subscription":
        internal_subscription_id = metadata.get("subscription_id")
        provider_subscription_id = session.get("subscription")
        if isinstance(provider_subscription_id, dict):
            provider_subscription_id = provider_subscription_id.get("id")
        if not isinstance(internal_subscription_id, str) or not isinstance(provider_subscription_id, str):
            raise HTTPException(status_code=409, detail="Stripe did not return a valid subscription reference.")
        provider_subscription = _stripe_request(f"/subscriptions/{provider_subscription_id}")
        if provider_subscription.get("status") not in {"active", "trialing"}:
            raise HTTPException(status_code=409, detail="Stripe has not activated this subscription.")
        provider_metadata = (
            provider_subscription.get("metadata")
            if isinstance(provider_subscription.get("metadata"), dict)
            else {}
        )
        if provider_metadata.get("subscription_id") != internal_subscription_id:
            raise HTTPException(status_code=409, detail="Stripe subscription metadata did not match this checkout.")
        now = utc_now()
        with database(immediate=True) as connection:
            subscription = connection.execute(
                "SELECT s.*, p.currency, p.price_minor FROM business_subscriptions s "
                "JOIN business_plans p ON p.id=s.plan_id "
                "WHERE s.id=? AND s.user_id=? AND s.provider='stripe' "
                "AND s.provider_checkout_session_id=?",
                (internal_subscription_id, user["id"], payload.session_id),
            ).fetchone()
            if (
                subscription is None
                or metadata.get("subscription_id") != subscription["id"]
                or session.get("currency", "").upper() != subscription["currency"]
                or session.get("amount_total") != int(subscription["price_minor"])
            ):
                raise HTTPException(status_code=404, detail="Subscription Checkout Session was not found for this account.")
            connection.execute(
                "UPDATE business_subscriptions SET status='active', provider_subscription_id=?, "
                "current_period_start=?, current_period_end=?, updated_at=? WHERE id=? AND user_id=?",
                (
                    provider_subscription_id,
                    _stripe_period(provider_subscription.get("current_period_start")) or now,
                    _stripe_period(provider_subscription.get("current_period_end")),
                    now,
                    subscription["id"],
                    user["id"],
                ),
            )
        return {"status": "active", "subscription_id": internal_subscription_id}
    raise HTTPException(status_code=409, detail="This Checkout Session has an unsupported mode.")


@router.post("/business/subscriptions/checkout", status_code=201, tags=["Business and Revenue"])
def create_subscription_checkout(
    payload: CheckoutInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    if payload.coupon_code:
        raise HTTPException(
            status_code=422,
            detail="Recurring coupon discounts are not supported by this checkout flow.",
        )
    with database() as connection:
        plan = connection.execute(
            "SELECT * FROM business_plans WHERE id=? AND active=1",
            (payload.plan_id,),
        ).fetchone()
    if plan is None or plan["billing_interval"] not in {"monthly", "yearly"}:
        raise HTTPException(status_code=422, detail="Choose an active monthly or yearly subscription plan.")
    provider = _select_payment_provider(plan["currency"], recurring=True)
    _require_provider_webhook(provider)
    if provider == "razorpay" and not plan["gateway_plan_id"]:
        raise HTTPException(status_code=422, detail="This plan has no configured Razorpay subscription plan.")
    with database() as connection:
        existing = connection.execute(
            "SELECT id, plan_id, provider, provider_subscription_id, provider_checkout_session_id, status "
            "FROM business_subscriptions "
            "WHERE user_id=? AND status IN ('active', 'pending') ORDER BY created_at DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
    if existing and existing["status"] == "active":
        raise HTTPException(status_code=409, detail="Cancel or change your active subscription before starting another.")
    if existing and existing["plan_id"] != plan["id"]:
        raise HTTPException(
            status_code=409,
            detail="Finish or cancel the pending subscription checkout before choosing a different plan.",
        )
    if existing:
        if existing["provider"] != provider:
            raise HTTPException(status_code=409, detail="The pending subscription uses a different payment provider.")
        if provider == "stripe":
            session_id = existing["provider_checkout_session_id"]
            if not session_id:
                raise HTTPException(
                    status_code=409,
                    detail="The pending Stripe subscription must be reconciled before another checkout can start.",
                )
            checkout_session = _stripe_request(f"/checkout/sessions/{session_id}")
            if checkout_session.get("status") == "open" and _is_stripe_checkout_url(checkout_session.get("url")):
                return {
                    "provider": "stripe",
                    "checkout_url": checkout_session["url"],
                    "session_id": session_id,
                    "status": "pending",
                    "transaction_id": existing["id"],
                }
            if checkout_session.get("status") == "complete":
                raise HTTPException(
                    status_code=409,
                    detail="This checkout is complete and awaiting provider confirmation.",
                )
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_subscriptions SET status='expired', updated_at=? WHERE id=? AND status='pending'",
                    (utc_now(), existing["id"]),
                )
        else:
            if not existing["provider_subscription_id"]:
                raise HTTPException(status_code=409, detail="Pending Razorpay subscription reference is unavailable.")
            provider_sub = _razorpay_request(f"/subscriptions/{existing['provider_subscription_id']}")
            if provider_sub.get("status") not in {"created", "authenticated"}:
                raise HTTPException(
                    status_code=409,
                    detail="The pending subscription must be reconciled with the payment provider before retrying.",
                )
            return {
                "provider": "razorpay",
                "key_id": settings.RAZORPAY_KEY_ID,
                "subscription_id": existing["provider_subscription_id"],
                "name": "Career Platform",
                "description": plan["name"],
                "status": "pending",
                "transaction_id": existing["id"],
            }

    if provider == "stripe":
        now = utc_now()
        subscription_id = str(uuid.uuid4())
        with database(immediate=True) as connection:
            connection.execute(
                "INSERT INTO business_subscriptions"
                "(id, user_id, plan_id, status, provider, created_at, updated_at) "
                "VALUES (?, ?, ?, 'pending', 'stripe', ?, ?)",
                (subscription_id, user["id"], plan["id"], now, now),
            )
        try:
            checkout_session = _stripe_checkout_session(
                user=user,
                name=plan["name"],
                amount_minor=int(plan["price_minor"]),
                currency=plan["currency"],
                subscription_id=subscription_id,
                plan_id=plan["id"],
                billing_interval=plan["billing_interval"],
            )
        except HTTPException:
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_subscriptions SET status='expired', updated_at=? WHERE id=? AND status='pending'",
                    (utc_now(), subscription_id),
                )
            raise
        if not isinstance(checkout_session.get("id"), str) or not _is_stripe_checkout_url(checkout_session.get("url")):
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_subscriptions SET status='expired', updated_at=? WHERE id=? AND status='pending'",
                    (utc_now(), subscription_id),
                )
            raise HTTPException(status_code=502, detail="Stripe did not return a valid Checkout Session.")
        with database(immediate=True) as connection:
            connection.execute(
                "UPDATE business_subscriptions SET provider_checkout_session_id=?, updated_at=? WHERE id=?",
                (checkout_session["id"], utc_now(), subscription_id),
            )
        return {
            "provider": "stripe",
            "checkout_url": checkout_session["url"],
            "session_id": checkout_session["id"],
            "name": "Career Platform",
            "description": plan["name"],
            "status": "pending",
            "transaction_id": subscription_id,
        }

    _require_gateway()
    provider_sub = _razorpay_request(
        "/subscriptions",
        method="POST",
        payload={
            "plan_id": plan["gateway_plan_id"],
            "total_count": 120,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {"user_id": user["id"], "plan_id": plan["id"]},
        },
    )
    provider_subscription_id = provider_sub.get("id")
    if not isinstance(provider_subscription_id, str):
        raise HTTPException(status_code=502, detail="Payment provider did not return a subscription reference.")
    now = utc_now()
    subscription_id = str(uuid.uuid4())
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO business_subscriptions"
            "(id, user_id, plan_id, status, provider, provider_subscription_id, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', 'razorpay', ?, ?, ?)",
            (subscription_id, user["id"], plan["id"], provider_subscription_id, now, now),
        )
    return {
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
        "subscription_id": provider_subscription_id,
        "name": "Career Platform",
        "description": plan["name"],
        "status": "pending",
        "transaction_id": subscription_id,
    }


@router.post("/business/subscriptions/verify", tags=["Business and Revenue"])
def verify_subscription_checkout(
    payload: VerifySubscriptionInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_gateway()
    if not _verify_signature(
        f"{payload.razorpay_payment_id}|{payload.razorpay_subscription_id}",
        payload.razorpay_signature,
        settings.RAZORPAY_KEY_SECRET,
    ):
        raise HTTPException(status_code=400, detail="Subscription signature verification failed.")
    provider_subscription = _razorpay_request(f"/subscriptions/{payload.razorpay_subscription_id}")
    payment = _razorpay_request(f"/payments/{payload.razorpay_payment_id}")
    if (
        provider_subscription.get("status") not in {"active", "authenticated"}
        or payment.get("status") != "captured"
        or payment.get("subscription_id") != payload.razorpay_subscription_id
    ):
        raise HTTPException(status_code=409, detail="The payment provider has not confirmed the subscription payment.")
    now = utc_now()
    with database(immediate=True) as connection:
        row = connection.execute(
            "SELECT * FROM business_subscriptions WHERE provider_subscription_id=? AND user_id=?",
            (payload.razorpay_subscription_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Pending subscription was not found for this account.")
        if payment.get("currency") != connection.execute(
            "SELECT currency FROM business_plans WHERE id=?", (row["plan_id"],)
        ).fetchone()["currency"]:
            raise HTTPException(status_code=409, detail="The confirmed subscription payment currency does not match the plan.")
        connection.execute(
            "UPDATE business_subscriptions SET status='active', current_period_start=?, "
            "current_period_end=?, updated_at=? WHERE id=?",
            (
                provider_subscription.get("current_start") or now,
                provider_subscription.get("current_end"),
                now,
                row["id"],
            ),
        )
        _record_subscription_payment(connection, row, payment)
    return {"status": "active", "subscription_id": row["id"]}


@router.post("/business/subscriptions/{subscription_id}/cancel", tags=["Business and Revenue"])
def cancel_subscription(
    subscription_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM business_subscriptions WHERE id=? AND user_id=?",
            (subscription_id, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Subscription was not found.")
    if row["status"] != "active":
        raise HTTPException(status_code=409, detail="Only an active subscription can be cancelled.")
    _require_provider_webhook(row["provider"])
    if row["provider"] == "stripe":
        if not row["provider_subscription_id"]:
            raise HTTPException(status_code=409, detail="The Stripe subscription reference is unavailable.")
        provider_result = _stripe_request(
            f"/subscriptions/{row['provider_subscription_id']}",
            method="POST",
            payload={"cancel_at_period_end": "true"},
        )
    else:
        _require_gateway()
        provider_result = _razorpay_request(
            f"/subscriptions/{row['provider_subscription_id']}/cancel",
            method="POST",
            payload={"cancel_at_cycle_end": 1},
        )
    if provider_result.get("id") != row["provider_subscription_id"]:
        raise HTTPException(status_code=502, detail="The payment provider did not confirm cancellation.")
    with database(immediate=True) as connection:
        connection.execute(
            "UPDATE business_subscriptions SET cancel_at_period_end=1, updated_at=? WHERE id=? AND user_id=?",
            (utc_now(), subscription_id, user["id"]),
        )
    return {"status": "active", "cancel_at_period_end": True, "current_period_end": row["current_period_end"]}


@router.post("/business/subscriptions/{subscription_id}/change", tags=["Business and Revenue"])
def change_subscription_plan(
    subscription_id: str,
    payload: SubscriptionPlanChangeInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        subscription = connection.execute(
            "SELECT * FROM business_subscriptions WHERE id=? AND user_id=? AND status='active'",
            (subscription_id, user["id"]),
        ).fetchone()
        target = connection.execute(
            "SELECT * FROM business_plans WHERE id=? AND active=1",
            (payload.plan_id,),
        ).fetchone()
        current_plan = connection.execute(
            "SELECT currency FROM business_plans WHERE id=?",
            (subscription["plan_id"],),
        ).fetchone() if subscription else None
    if subscription is None:
        raise HTTPException(status_code=404, detail="An active subscription was not found.")
    if subscription["provider"] == "stripe":
        raise HTTPException(
            status_code=422,
            detail="Scheduled plan changes are not currently supported for Stripe subscriptions. Cancel at period end and select the new plan after the current period.",
        )
    _require_gateway()
    _require_subscription_webhook()
    if (
        target is None
        or target["billing_interval"] not in {"monthly", "yearly"}
        or not target["gateway_plan_id"]
        or current_plan is None
        or target["currency"] != current_plan["currency"]
    ):
        raise HTTPException(status_code=422, detail="Choose a configured subscription plan in the current currency.")
    if target["id"] == subscription["plan_id"]:
        raise HTTPException(status_code=422, detail="The selected plan is already active.")
    provider_result = _razorpay_request(
        f"/subscriptions/{subscription['provider_subscription_id']}/update",
        method="POST",
        payload={
            "plan_id": target["gateway_plan_id"],
            "schedule_change_at": "cycle_end",
            "customer_notify": 1,
        },
    )
    if provider_result.get("id") != subscription["provider_subscription_id"]:
        raise HTTPException(status_code=502, detail="The payment provider did not confirm the scheduled plan change.")
    with database(immediate=True) as connection:
        connection.execute(
            "UPDATE business_subscriptions SET pending_plan_id=?, updated_at=? WHERE id=? AND user_id=?",
            (target["id"], utc_now(), subscription_id, user["id"]),
        )
    return {
        "status": "scheduled",
        "plan_id": target["id"],
        "effective_at": subscription["current_period_end"],
    }


@router.get("/business/transactions", tags=["Business and Revenue"])
def list_transactions(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT id, plan_id, marketplace_order_id, provider, amount_minor, discount_minor, currency,
                status, purpose, captured_at, created_at, updated_at,
                (SELECT COUNT(*) FROM business_payment_attempts a
                 WHERE a.transaction_id=business_transactions.id AND a.status='failed') AS failed_attempts
            FROM business_transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 100
            """,
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/business/subscriptions", tags=["Business and Revenue"])
def list_subscriptions(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT s.id, s.plan_id, s.provider, p.name AS plan_name, p.tier, p.billing_interval,
                s.status, s.current_period_start, s.current_period_end,
                s.cancel_at_period_end, s.pending_plan_id, s.created_at, s.updated_at
            FROM business_subscriptions s JOIN business_plans p ON p.id=s.plan_id
            WHERE s.user_id=? ORDER BY s.created_at DESC LIMIT 100
            """,
            (user["id"],),
        ).fetchall()
    return [{**dict(row), "cancel_at_period_end": bool(row["cancel_at_period_end"])} for row in rows]


@router.post("/business/webhooks/razorpay", include_in_schema=False)
async def razorpay_webhook(
    request: FastAPIRequest,
    signature: Optional[str] = Header(default=None, alias="X-Razorpay-Signature"),
) -> dict[str, bool]:
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Payment webhook secret is not configured.")
    body = await request.body()
    if not signature or not _verify_signature(
        body.decode("latin-1"), signature, settings.RAZORPAY_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=400, detail="Webhook signature verification failed.")
    try:
        event = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Webhook payload is invalid JSON.") from exc
    event_type = event.get("event")
    payload = event.get("payload", {})
    if event_type in {"payment.captured", "order.paid"}:
        entity = payload.get("payment", {}).get("entity") or payload.get("order", {}).get("entity") or {}
        order_id = entity.get("order_id") or entity.get("id")
        payment_id = entity.get("id") if entity.get("order_id") else None
        if order_id and payment_id:
            with database(immediate=True) as connection:
                transaction = connection.execute(
                    "SELECT * FROM business_transactions WHERE provider_order_id=?",
                    (order_id,),
                ).fetchone()
                if transaction and int(transaction["amount_minor"]) == int(entity.get("amount", -1)):
                    _settle_captured_transaction(connection, transaction, payment_id)
    elif event_type == "payment.failed":
        entity = payload.get("payment", {}).get("entity", {})
        order_id = entity.get("order_id")
        payment_id = entity.get("id")
        if order_id and payment_id:
            with database(immediate=True) as connection:
                transaction = connection.execute(
                    "SELECT id FROM business_transactions WHERE provider_order_id=?",
                    (order_id,),
                ).fetchone()
                if transaction:
                    connection.execute(
                        "INSERT OR IGNORE INTO business_payment_attempts"
                        "(id, transaction_id, provider_payment_id, status, error_code, created_at) "
                        "VALUES (?, ?, ?, 'failed', ?, ?)",
                        (
                            str(uuid.uuid4()), transaction["id"], payment_id,
                            str(entity.get("error_code") or "")[:100] or None, utc_now(),
                        ),
                    )
    elif event_type in {"refund.processed", "refund.failed"}:
        refund = payload.get("refund", {}).get("entity", {})
        payment_id = refund.get("payment_id")
        if payment_id:
            with database(immediate=True) as connection:
                transaction = connection.execute(
                    "SELECT * FROM business_transactions WHERE provider_payment_id=?",
                    (payment_id,),
                ).fetchone()
                if transaction and transaction["status"] in {"refund_pending", "captured"}:
                    refunded = event_type == "refund.processed"
                    connection.execute(
                        "UPDATE business_transactions SET provider_refund_id=?, status=?, updated_at=? WHERE id=?",
                        (
                            refund.get("id"),
                            "refunded" if refunded else "captured",
                            utc_now(),
                            transaction["id"],
                        ),
                    )
                    if refunded and transaction["marketplace_order_id"]:
                        connection.execute(
                            "UPDATE business_marketplace_orders SET status='refunded', updated_at=? WHERE id=?",
                            (utc_now(), transaction["marketplace_order_id"]),
                        )
    elif event_type in {
        "subscription.activated", "subscription.charged", "subscription.updated",
        "subscription.cancelled", "subscription.halted", "subscription.completed",
    }:
        entity = payload.get("subscription", {}).get("entity", {})
        provider_id = entity.get("id")
        new_status = {
            "subscription.activated": "active",
            "subscription.charged": "active",
            "subscription.updated": "active",
            "subscription.cancelled": "cancelled",
            "subscription.halted": "past_due",
            "subscription.completed": "expired",
        }[event_type]
        if provider_id:
            with database(immediate=True) as connection:
                subscription = connection.execute(
                    "SELECT * FROM business_subscriptions WHERE provider_subscription_id=?",
                    (provider_id,),
                ).fetchone()
                if subscription:
                    pending_plan = None
                    if subscription["pending_plan_id"]:
                        pending_plan = connection.execute(
                            "SELECT id, gateway_plan_id FROM business_plans WHERE id=?",
                            (subscription["pending_plan_id"],),
                        ).fetchone()
                    active_plan_id = subscription["plan_id"]
                    if (
                        pending_plan
                        and event_type == "subscription.charged"
                        and entity.get("plan_id") == pending_plan["gateway_plan_id"]
                    ):
                        active_plan_id = pending_plan["id"]
                    pending_plan_id = (
                        None if active_plan_id != subscription["plan_id"]
                        else subscription["pending_plan_id"]
                    )
                    connection.execute(
                        "UPDATE business_subscriptions SET status=?, plan_id=?, pending_plan_id=?, current_period_start=?, "
                        "current_period_end=?, updated_at=? WHERE id=?",
                        (
                            new_status,
                            active_plan_id,
                            pending_plan_id,
                            entity.get("current_start") or subscription["current_period_start"],
                            entity.get("current_end") or subscription["current_period_end"],
                            utc_now(),
                            subscription["id"],
                        ),
                    )
                    payment = payload.get("payment", {}).get("entity", {})
                    if event_type in {"subscription.activated", "subscription.charged"}:
                        _record_subscription_payment(
                            connection,
                            {**dict(subscription), "plan_id": active_plan_id},
                            payment,
                        )
    return {"received": True}


@router.post("/business/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: FastAPIRequest,
    signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, bool]:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured.")
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 1_000_000:
                raise HTTPException(status_code=413, detail="Stripe webhook payload is too large.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Stripe webhook content length is invalid.") from exc
    body_buffer = bytearray()
    async for chunk in request.stream():
        body_buffer.extend(chunk)
        if len(body_buffer) > 1_000_000:
            raise HTTPException(status_code=413, detail="Stripe webhook payload is too large.")
    body = bytes(body_buffer)
    if not _verify_stripe_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Stripe webhook signature verification failed.")
    try:
        event = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Stripe webhook payload is invalid JSON.") from exc
    event_id = event.get("id")
    event_type = event.get("type")
    event_data = event.get("data")
    entity = event_data.get("object") if isinstance(event_data, dict) else None
    if not isinstance(event_id, str) or not isinstance(event_type, str) or not isinstance(entity, dict):
        raise HTTPException(status_code=400, detail="Stripe webhook payload is missing required fields.")

    with database(immediate=True) as connection:
        existing_event = connection.execute(
            "SELECT event_id FROM business_stripe_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
        if existing_event:
            return {"received": True}
        connection.execute(
            "INSERT INTO business_stripe_events(event_id, event_type, received_at) VALUES (?, ?, ?)",
            (event_id, event_type, utc_now()),
        )

        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            session_id = entity.get("id")
            metadata = entity.get("metadata") if isinstance(entity.get("metadata"), dict) else {}
            if entity.get("mode") == "payment" and entity.get("payment_status") == "paid":
                payment_intent = entity.get("payment_intent")
                payment_id = payment_intent.get("id") if isinstance(payment_intent, dict) else payment_intent
                transaction_id = metadata.get("transaction_id")
                if isinstance(session_id, str) and isinstance(transaction_id, str) and isinstance(payment_id, str):
                    transaction = connection.execute(
                        "SELECT * FROM business_transactions WHERE id=? AND provider_order_id=? AND provider='stripe'",
                        (transaction_id, session_id),
                    ).fetchone()
                    if (
                        transaction
                        and metadata.get("user_id") == transaction["user_id"]
                        and entity.get("client_reference_id") == transaction_id
                        and entity.get("currency", "").upper() == transaction["currency"]
                        and entity.get("amount_total") == int(transaction["amount_minor"])
                        and transaction["purpose"] != "subscription"
                    ):
                        _settle_captured_transaction(connection, transaction, payment_id)
            elif entity.get("mode") == "subscription" and entity.get("payment_status") == "paid":
                internal_id = metadata.get("subscription_id")
                provider_id = entity.get("subscription")
                if isinstance(provider_id, dict):
                    provider_id = provider_id.get("id")
                if isinstance(session_id, str) and isinstance(internal_id, str) and isinstance(provider_id, str):
                    subscription = connection.execute(
                        "SELECT s.*, p.currency, p.price_minor FROM business_subscriptions s "
                        "JOIN business_plans p ON p.id=s.plan_id "
                        "WHERE s.id=? AND s.provider_checkout_session_id=? AND s.provider='stripe'",
                        (internal_id, session_id),
                    ).fetchone()
                    if (
                        subscription
                        and metadata.get("user_id") == subscription["user_id"]
                        and entity.get("currency", "").upper() == subscription["currency"]
                        and entity.get("amount_total") == int(subscription["price_minor"])
                    ):
                        connection.execute(
                            "UPDATE business_subscriptions SET status='active', provider_subscription_id=?, "
                            "current_period_start=COALESCE(current_period_start, ?), updated_at=? "
                            "WHERE id=? AND provider='stripe' AND status IN ('pending', 'active')",
                            (provider_id, utc_now(), utc_now(), internal_id),
                        )
        elif event_type == "invoice.paid":
            provider_id = entity.get("subscription")
            if isinstance(provider_id, dict):
                provider_id = provider_id.get("id")
            parent = entity.get("parent")
            details = parent.get("subscription_details") if isinstance(parent, dict) else None
            if not isinstance(details, dict):
                details = entity.get("subscription_details")
            subscription_metadata = details.get("metadata") if isinstance(details, dict) else None
            internal_id = (
                subscription_metadata.get("subscription_id")
                if isinstance(subscription_metadata, dict)
                else None
            )
            if not isinstance(provider_id, str):
                provider_id = details.get("subscription") if isinstance(details, dict) else None
                if isinstance(provider_id, dict):
                    provider_id = provider_id.get("id")
            subscription = None
            if isinstance(provider_id, str):
                subscription = connection.execute(
                    "SELECT * FROM business_subscriptions WHERE provider_subscription_id=? AND provider='stripe'",
                    (provider_id,),
                ).fetchone()
            if subscription is None and isinstance(internal_id, str):
                subscription = connection.execute(
                    "SELECT * FROM business_subscriptions WHERE id=? AND provider='stripe'",
                    (internal_id,),
                ).fetchone()
                if subscription and isinstance(provider_id, str) and not subscription["provider_subscription_id"]:
                    connection.execute(
                        "UPDATE business_subscriptions SET provider_subscription_id=? WHERE id=?",
                        (provider_id, subscription["id"]),
                    )
            if subscription:
                _record_stripe_subscription_payment(connection, subscription, entity)
                connection.execute(
                    "UPDATE business_subscriptions SET status='active', updated_at=? "
                    "WHERE id=? AND status NOT IN ('cancelled', 'expired')",
                    (utc_now(), subscription["id"]),
                )
        elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
            metadata = entity.get("metadata") if isinstance(entity.get("metadata"), dict) else {}
            internal_id = metadata.get("subscription_id")
            provider_id = entity.get("id")
            if isinstance(internal_id, str) and isinstance(provider_id, str):
                provider_status = entity.get("status")
                status_map = {
                    "active": "active",
                    "trialing": "active",
                    "past_due": "past_due",
                    "unpaid": "past_due",
                    "incomplete": "pending",
                    "incomplete_expired": "expired",
                    "canceled": "cancelled",
                }
                new_status = status_map.get(provider_status, "cancelled" if event_type.endswith(".deleted") else None)
                if new_status:
                    connection.execute(
                        "UPDATE business_subscriptions SET status=?, provider_subscription_id=?, "
                        "current_period_start=COALESCE(?, current_period_start), "
                        "current_period_end=COALESCE(?, current_period_end), cancel_at_period_end=?, updated_at=? "
                        "WHERE id=? AND provider='stripe' "
                        "AND status NOT IN ('cancelled', 'expired')",
                        (
                            new_status,
                            provider_id,
                            _stripe_period(entity.get("current_period_start")),
                            _stripe_period(entity.get("current_period_end")),
                            int(bool(entity.get("cancel_at_period_end"))),
                            utc_now(),
                            internal_id,
                        ),
                    )
        elif event_type == "invoice.payment_failed":
            provider_id = entity.get("subscription")
            if isinstance(provider_id, dict):
                provider_id = provider_id.get("id")
            if isinstance(provider_id, str):
                connection.execute(
                    "UPDATE business_subscriptions SET status='past_due', updated_at=? "
                    "WHERE provider_subscription_id=? AND provider='stripe' "
                    "AND status NOT IN ('cancelled', 'expired')",
                    (utc_now(), provider_id),
                )
        elif event_type in {"refund.updated", "refund.failed"}:
            payment_intent = entity.get("payment_intent")
            if isinstance(payment_intent, dict):
                payment_intent = payment_intent.get("id")
            if isinstance(payment_intent, str):
                transaction = connection.execute(
                    "SELECT * FROM business_transactions WHERE provider_payment_id=? AND provider='stripe'",
                    (payment_intent,),
                ).fetchone()
                if transaction and transaction["status"] in {"captured", "refund_pending"}:
                    refund_status = entity.get("status")
                    next_status = (
                        "refunded"
                        if refund_status == "succeeded"
                        and entity.get("amount") == int(transaction["amount_minor"])
                        else "refund_pending" if refund_status == "succeeded"
                        else "captured" if refund_status == "failed"
                        else "refund_pending"
                    )
                    connection.execute(
                        "UPDATE business_transactions SET provider_refund_id=?, status=?, updated_at=? WHERE id=?",
                        (entity.get("id"), next_status, utc_now(), transaction["id"]),
                    )
                    if next_status == "refunded" and transaction["marketplace_order_id"]:
                        connection.execute(
                            "UPDATE business_marketplace_orders SET status='refunded', updated_at=? WHERE id=?",
                            (utc_now(), transaction["marketplace_order_id"]),
                        )
        elif event_type == "charge.refunded":
            payment_intent = entity.get("payment_intent")
            if isinstance(payment_intent, dict):
                payment_intent = payment_intent.get("id")
            refunds = entity.get("refunds")
            refund_rows = refunds.get("data") if isinstance(refunds, dict) else None
            refund = refund_rows[-1] if isinstance(refund_rows, list) and refund_rows else {}
            if isinstance(payment_intent, str):
                transaction = connection.execute(
                    "SELECT * FROM business_transactions WHERE provider_payment_id=? AND provider='stripe'",
                    (payment_intent,),
                ).fetchone()
                if transaction and transaction["status"] in {"captured", "refund_pending"}:
                    fully_refunded = (
                        isinstance(entity.get("amount"), int)
                        and entity.get("amount_refunded") == entity.get("amount")
                    )
                    connection.execute(
                        "UPDATE business_transactions SET provider_refund_id=?, status=?, updated_at=? WHERE id=?",
                        (
                            refund.get("id"),
                            "refunded" if fully_refunded else "refund_pending",
                            utc_now(),
                            transaction["id"],
                        ),
                    )
                    if fully_refunded and transaction["marketplace_order_id"]:
                        connection.execute(
                            "UPDATE business_marketplace_orders SET status='refunded', updated_at=? WHERE id=?",
                            (utc_now(), transaction["marketplace_order_id"]),
                        )
        elif event_type in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
            metadata = entity.get("metadata") if isinstance(entity.get("metadata"), dict) else {}
            transaction_id = metadata.get("transaction_id")
            subscription_id = metadata.get("subscription_id")
            if isinstance(transaction_id, str):
                transaction = connection.execute(
                    "SELECT id FROM business_transactions WHERE id=? AND provider_order_id=? AND provider='stripe'",
                    (transaction_id, entity.get("id")),
                ).fetchone()
                if transaction:
                    connection.execute(
                        "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                        (utc_now(), transaction_id),
                    )
                    connection.execute(
                        "UPDATE business_coupon_redemptions SET status='released' "
                        "WHERE transaction_id=? AND status='pending'",
                        (transaction_id,),
                    )
            if isinstance(subscription_id, str):
                connection.execute(
                    "UPDATE business_subscriptions SET status='expired', updated_at=? "
                    "WHERE id=? AND provider='stripe' AND status='pending'",
                    (utc_now(), subscription_id),
                )
    return {"received": True}


@router.post("/business/referrals/claim", status_code=201, tags=["Business and Revenue"])
def claim_referral(
    payload: ReferralInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, str]:
    with database(immediate=True) as connection:
        referral = connection.execute(
            """
            SELECT user_id FROM business_referral_codes WHERE code=? COLLATE NOCASE
            UNION ALL
            SELECT user_id FROM business_affiliates
            WHERE code=? COLLATE NOCASE AND status='approved'
            LIMIT 1
            """,
            (payload.code.strip(), payload.code.strip()),
        ).fetchone()
        if referral is None:
            raise HTTPException(status_code=404, detail="Referral code was not found.")
        if referral["user_id"] == user["id"]:
            raise HTTPException(status_code=422, detail="You cannot use your own referral code.")
        existing = connection.execute(
            "SELECT id FROM business_referrals WHERE referred_user_id=?",
            (user["id"],),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="A referral has already been assigned to this account.")
        referral_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO business_referrals"
            "(id, referrer_user_id, referred_user_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (referral_id, referral["user_id"], user["id"], now, now),
        )
    return {"status": "pending", "message": "Referral reward eligibility starts after a confirmed paid transaction."}


@router.get("/business/referrals", tags=["Business and Revenue"])
def referral_dashboard(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO business_referral_codes(user_id, code, created_at) VALUES (?, ?, ?)",
            (user["id"], _new_referral_code(), utc_now()),
        )
        code = connection.execute(
            "SELECT code FROM business_referral_codes WHERE user_id=?", (user["id"],)
        ).fetchone()["code"]
        referrals = connection.execute(
            "SELECT status, reward_credits, created_at, updated_at "
            "FROM business_referrals WHERE referrer_user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
        balance = ensure_monthly_credits(connection, user["id"])
        reward = _business_setting(connection, "referral_reward_credits", 50)
    return {
        "code": code,
        "referral_url": f"/?ref={code}",
        "reward_rule": f"{reward} credits after a referred account completes its first verified paid purchase; each account and payment qualifies once.",
        "referral_reward_credits": reward,
        "reward_credits": balance,
        "referrals": [dict(row) for row in referrals],
    }


@router.post("/business/affiliates", status_code=201, tags=["Business and Revenue"])
def apply_as_affiliate(
    payload: AffiliateInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    del payload
    code = _new_referral_code()
    now = utc_now()
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO business_affiliates(user_id, code, status, commission_basis_points, created_at, updated_at) "
            "VALUES (?, ?, 'pending', 0, ?, ?) ON CONFLICT(user_id) DO NOTHING",
            (user["id"], code, now, now),
        )
        row = connection.execute(
            "SELECT code, status, commission_basis_points FROM business_affiliates WHERE user_id=?",
            (user["id"],),
        ).fetchone()
    return dict(row)


@router.get("/business/affiliates", tags=["Business and Revenue"])
def affiliate_dashboard(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        profile = connection.execute(
            "SELECT code, status, commission_basis_points FROM business_affiliates WHERE user_id=?",
            (user["id"],),
        ).fetchone()
        conversions = connection.execute(
            "SELECT commission_minor, status, created_at FROM business_affiliate_conversions "
            "WHERE affiliate_user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    return {
        "affiliate": dict(profile) if profile else None,
        "conversions": [dict(row) for row in conversions],
        "note": "Affiliate commissions are tracked for administrator review and are not represented as paid until explicitly reconciled.",
    }


@router.post("/business/leads", status_code=201, tags=["Business and Revenue"])
def submit_business_lead(
    payload: LeadInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, str]:
    lead_id = str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO business_leads(id, user_id, lead_type, organization, details, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'submitted', ?, ?)",
            (
                lead_id, user["id"], payload.lead_type, payload.organization.strip(),
                protect_text(payload.details.strip()), now, now,
            ),
        )
    return {"id": lead_id, "status": "submitted"}


@router.get("/business/leads", tags=["Business and Revenue"])
def list_business_leads(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT id, lead_type, organization, details, status, created_at, updated_at "
            "FROM business_leads WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    return [{**dict(row), "details": reveal_text(row["details"])} for row in rows]


@router.get("/business/marketplace", tags=["Business and Revenue"])
def marketplace_listings(
    listing_type: Optional[str] = None,
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    if listing_type is not None and listing_type not in _MARKETPLACE_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported marketplace category.")
    query = (
        "SELECT id, provider_user_id, listing_type, title, description, price_minor, currency, created_at "
        "FROM business_marketplace_listings WHERE active=1"
    )
    params: list[Any] = []
    if listing_type:
        query += " AND listing_type=?"
        params.append(listing_type)
    query += " ORDER BY created_at DESC LIMIT 100"
    with database() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@router.post("/business/marketplace/listings", status_code=201, tags=["Business and Revenue"])
def create_marketplace_listing(
    payload: MarketplaceListingInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    listing_id = str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO business_marketplace_listings"
            "(id, provider_user_id, listing_type, title, description, price_minor, currency, active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (
                listing_id, user["id"], payload.listing_type, payload.title.strip(),
                payload.description.strip(), payload.price_minor, payload.currency, now, now,
            ),
        )
    return {"id": listing_id, "status": "pending_review", "note": "Listings are not purchasable until approved by an administrator."}


@router.post("/business/marketplace/{listing_id}/orders", status_code=201, tags=["Business and Revenue"])
def create_marketplace_order(
    listing_id: str,
    payload: MarketplaceOrderInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        listing = connection.execute(
            "SELECT * FROM business_marketplace_listings WHERE id=? AND active=1",
            (listing_id,),
        ).fetchone()
    if listing is None:
        raise HTTPException(status_code=404, detail="Marketplace listing is unavailable.")
    if listing["provider_user_id"] == user["id"]:
        raise HTTPException(status_code=422, detail="You cannot purchase your own listing.")
    provider = _select_payment_provider(listing["currency"])
    now = utc_now()
    order_id = str(uuid.uuid4())
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO business_marketplace_orders"
            "(id, customer_user_id, listing_id, status, amount_minor, currency, requirements, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending_payment', ?, ?, ?, ?, ?)",
            (
                order_id, user["id"], listing_id, listing["price_minor"],
                listing["currency"], protect_text(payload.requirements.strip()), now, now,
            ),
        )
        transaction_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO business_transactions"
            "(id, user_id, marketplace_order_id, provider, amount_minor, currency, status, purpose, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'created', 'marketplace', ?, ?)",
            (
                transaction_id, user["id"], order_id, provider, listing["price_minor"],
                listing["currency"], now, now,
            ),
        )
    if provider == "stripe":
        try:
            session = _stripe_checkout_session(
                user=user,
                name=listing["title"],
                amount_minor=int(listing["price_minor"]),
                currency=listing["currency"],
                transaction_id=transaction_id,
            )
        except HTTPException:
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                    (utc_now(), transaction_id),
                )
                connection.execute(
                    "UPDATE business_marketplace_orders SET status='cancelled', updated_at=? WHERE id=? AND status='pending_payment'",
                    (utc_now(), order_id),
                )
            raise
        if not isinstance(session.get("id"), str) or not _is_stripe_checkout_url(session.get("url")):
            with database(immediate=True) as connection:
                connection.execute(
                    "UPDATE business_transactions SET status='failed', updated_at=? WHERE id=? AND status='created'",
                    (utc_now(), transaction_id),
                )
                connection.execute(
                    "UPDATE business_marketplace_orders SET status='cancelled', updated_at=? WHERE id=? AND status='pending_payment'",
                    (utc_now(), order_id),
                )
            raise HTTPException(status_code=502, detail="Stripe did not return a valid Checkout Session.")
        with database(immediate=True) as connection:
            connection.execute(
                "UPDATE business_transactions SET provider_order_id=?, updated_at=? WHERE id=?",
                (session["id"], utc_now(), transaction_id),
            )
        return {
            "order_id": order_id,
            "provider": "stripe",
            "checkout_url": session["url"],
            "session_id": session["id"],
            "amount": int(listing["price_minor"]),
            "currency": listing["currency"],
            "name": listing["title"],
            "description": "Professional career service",
        }

    _require_gateway()
    provider_order = _razorpay_request(
        "/orders",
        method="POST",
        payload={
            "amount": int(listing["price_minor"]),
            "currency": listing["currency"],
            "receipt": transaction_id[:40],
            "notes": {"transaction_id": transaction_id, "marketplace_order_id": order_id},
        },
    )
    if not isinstance(provider_order.get("id"), str):
        raise HTTPException(status_code=502, detail="Payment provider did not return an order reference.")
    with database(immediate=True) as connection:
        connection.execute(
            "UPDATE business_transactions SET provider_order_id=?, updated_at=? WHERE id=?",
            (provider_order["id"], utc_now(), transaction_id),
        )
    return {
        "order_id": order_id,
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": provider_order["id"],
        "amount": int(listing["price_minor"]),
        "currency": listing["currency"],
        "name": listing["title"],
        "description": "Professional career service",
    }


@router.get("/business/marketplace/orders", tags=["Business and Revenue"])
def marketplace_orders(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT o.*, l.title, l.listing_type, l.provider_user_id "
            "FROM business_marketplace_orders o JOIN business_marketplace_listings l ON l.id=o.listing_id "
            "WHERE o.customer_user_id=? OR l.provider_user_id=? ORDER BY o.created_at DESC LIMIT 100",
            (user["id"], user["id"]),
        ).fetchall()
    return [
        {
            **dict(row),
            "requirements": reveal_text(row["requirements"]),
            "is_customer": row["customer_user_id"] == user["id"],
            "is_provider": row["provider_user_id"] == user["id"],
        }
        for row in rows
    ]


@router.patch("/business/marketplace/orders/{order_id}", tags=["Business and Revenue"])
def update_marketplace_order(
    order_id: str,
    payload: MarketplaceOrderUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, str]:
    with database(immediate=True) as connection:
        order = connection.execute(
            "SELECT o.*, l.provider_user_id FROM business_marketplace_orders o "
            "JOIN business_marketplace_listings l ON l.id=o.listing_id WHERE o.id=?",
            (order_id,),
        ).fetchone()
        if order is None or user["id"] not in {order["customer_user_id"], order["provider_user_id"]}:
            raise HTTPException(status_code=404, detail="Marketplace order was not found.")
        if order["status"] not in {"paid", "in_progress", "disputed", "completed"}:
            raise HTTPException(status_code=409, detail="This order cannot be updated in its current state.")
        if payload.status in {"in_progress", "completed"} and user["id"] != order["provider_user_id"]:
            raise HTTPException(status_code=403, detail="Only the service provider can update fulfillment.")
        if payload.status == "disputed" and user["id"] != order["customer_user_id"]:
            raise HTTPException(status_code=403, detail="Only the customer can open a dispute.")
        if payload.status == "cancelled" and (
            user["id"] != order["customer_user_id"] or order["status"] != "paid"
        ):
            raise HTTPException(status_code=409, detail="Only the customer can cancel an order before fulfillment starts.")
        if order["status"] in {"disputed", "completed"} and payload.status != "disputed":
            raise HTTPException(status_code=409, detail="Only a dispute update is available for this order.")
        connection.execute(
            "UPDATE business_marketplace_orders SET status=?, updated_at=? WHERE id=?",
            (payload.status, utc_now(), order_id),
        )
        connection.execute(
            "INSERT INTO business_marketplace_events(id, order_id, actor_user_id, event_type, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), order_id, user["id"], payload.status, protect_text(payload.note.strip()), utc_now()),
        )
    return {"id": order_id, "status": payload.status}


@router.get("/business/admin/overview", tags=["Business Administration"])
def admin_overview(user: dict[str, str] = Depends(_admin_user)) -> dict[str, Any]:
    with database() as connection:
        metrics = {
            "active_subscriptions": connection.execute(
                "SELECT COUNT(*) AS count FROM business_subscriptions WHERE status='active'"
            ).fetchone()["count"],
            "pending_subscriptions": connection.execute(
                "SELECT COUNT(*) AS count FROM business_subscriptions WHERE status='pending'"
            ).fetchone()["count"],
            "captured_transactions": connection.execute(
                "SELECT COUNT(*) AS count FROM business_transactions WHERE status='captured'"
            ).fetchone()["count"],
            "failed_payment_attempts": connection.execute(
                "SELECT COUNT(*) AS count FROM business_payment_attempts WHERE status='failed'"
            ).fetchone()["count"],
            "refunds_pending": connection.execute(
                "SELECT COUNT(*) AS count FROM business_transactions WHERE status='refund_pending'"
            ).fetchone()["count"],
            "gross_revenue_minor": connection.execute(
                "SELECT currency, SUM(amount_minor) AS amount_minor, COUNT(*) AS count "
                "FROM business_transactions WHERE captured_at IS NOT NULL GROUP BY currency"
            ).fetchall(),
            "net_captured_revenue_minor": connection.execute(
                "SELECT currency, SUM(amount_minor) AS amount_minor, COUNT(*) AS count "
                "FROM business_transactions WHERE status='captured' GROUP BY currency"
            ).fetchall(),
            "refunds_pending_by_currency": connection.execute(
                "SELECT currency, SUM(amount_minor) AS amount_minor, COUNT(*) AS count "
                "FROM business_transactions WHERE status='refund_pending' GROUP BY currency"
            ).fetchall(),
            "refunded_amount_minor": connection.execute(
                "SELECT currency, SUM(amount_minor) AS amount_minor, COUNT(*) AS count "
                "FROM business_transactions WHERE status='refunded' GROUP BY currency"
            ).fetchall(),
            "credits_outstanding": connection.execute(
                "SELECT COALESCE(SUM(delta), 0) AS credits FROM business_credit_ledger"
            ).fetchone()["credits"],
            "pending_affiliate_commissions": connection.execute(
                "SELECT t.currency, SUM(c.commission_minor) AS amount_minor, COUNT(*) AS count "
                "FROM business_affiliate_conversions c JOIN business_transactions t ON t.id=c.transaction_id "
                "WHERE c.status='pending' GROUP BY t.currency"
            ).fetchall(),
            "pending_marketplace_orders": connection.execute(
                "SELECT COUNT(*) AS count FROM business_marketplace_orders WHERE status='pending_payment'"
            ).fetchone()["count"],
        }
        plans = connection.execute("SELECT * FROM business_plans ORDER BY tier, billing_interval").fetchall()
        leads = connection.execute(
            "SELECT lead_type, COUNT(*) AS count FROM business_leads WHERE status IN ('submitted','reviewing') "
            "GROUP BY lead_type"
        ).fetchall()
    return {
        "metrics": {
            key: [dict(row) for row in value]
            if key in {
                "gross_revenue_minor", "net_captured_revenue_minor",
                "refunds_pending_by_currency", "refunded_amount_minor",
                "pending_affiliate_commissions",
            }
            else value
            for key, value in metrics.items()
        },
        "plans": [_row_dict(row) for row in plans],
        "pending_leads": [dict(row) for row in leads],
        "gateway_configured": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
    }


@router.get("/business/admin/transactions", tags=["Business Administration"])
def admin_list_transactions(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT t.id, t.plan_id, t.marketplace_order_id, t.amount_minor, t.discount_minor,
                t.currency, t.status, t.purpose, t.captured_at, t.created_at,
                COALESCE(p.credits_grant, 0) AS credits_grant, u.email AS user_email,
                (SELECT COUNT(*) FROM business_payment_attempts a
                 WHERE a.transaction_id=t.id AND a.status='failed') AS failed_attempts
            FROM business_transactions t
            JOIN users u ON u.id=t.user_id
            LEFT JOIN business_plans p ON p.id=t.plan_id
            ORDER BY t.created_at DESC LIMIT 500
            """
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("/business/admin/transactions/{transaction_id}/refund", tags=["Business Administration"])
def admin_refund_transaction(
    transaction_id: str,
    payload: RefundInput,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, Any]:
    with database() as connection:
        transaction = connection.execute(
            "SELECT * FROM business_transactions WHERE id=?",
            (transaction_id,),
        ).fetchone()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Payment transaction was not found.")
    if transaction["status"] != "captured" or not transaction["provider_payment_id"]:
        raise HTTPException(status_code=409, detail="Only captured, not-yet-refunded payments can be refunded.")
    if transaction["provider"] == "stripe":
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(status_code=503, detail="Stripe refunds are not configured.")
    else:
        _require_gateway()
    plan = None
    if transaction["plan_id"]:
        with database() as connection:
            plan = connection.execute(
                "SELECT credits_grant FROM business_plans WHERE id=?",
                (transaction["plan_id"],),
            ).fetchone()
    if transaction["purpose"] == "credits" or (plan and int(plan["credits_grant"]) > 0):
        raise HTTPException(
            status_code=409,
            detail="Credit purchases require a separate credit-balance reconciliation before refund.",
        )
    if transaction["provider"] == "stripe":
        refund = _stripe_request(
            "/refunds",
            method="POST",
            payload={
                "payment_intent": transaction["provider_payment_id"],
                "metadata[reason]": payload.reason.strip()[:500],
                "metadata[transaction_id]": transaction_id,
            },
            idempotency_key=f"business-refund:{transaction_id}",
        )
    else:
        refund = _razorpay_request(
            f"/payments/{transaction['provider_payment_id']}/refund",
            method="POST",
            payload={
                "amount": int(transaction["amount_minor"]),
                "notes": {"reason": payload.reason.strip(), "transaction_id": transaction_id},
            },
        )
    refund_id = refund.get("id")
    refund_status = refund.get("status")
    accepted_statuses = {"pending", "processed"} if transaction["provider"] != "stripe" else {"pending", "succeeded"}
    if not isinstance(refund_id, str) or refund_status not in accepted_statuses:
        raise HTTPException(status_code=502, detail="The payment provider did not confirm the refund request.")
    transaction_status = (
        "refunded"
        if refund_status in {"processed", "succeeded"}
        else "refund_pending"
    )
    with database(immediate=True) as connection:
        connection.execute(
            "UPDATE business_transactions SET provider_refund_id=?, status=?, updated_at=? "
            "WHERE id=? AND status='captured'",
            (refund_id, transaction_status, utc_now(), transaction_id),
        )
        if transaction["marketplace_order_id"] and transaction_status == "refunded":
            connection.execute(
                "UPDATE business_marketplace_orders SET status='refunded', updated_at=? WHERE id=?",
                (utc_now(), transaction["marketplace_order_id"]),
            )
    return {"transaction_id": transaction_id, "refund_id": refund_id, "status": transaction_status}


@router.post("/business/admin/plans", status_code=201, tags=["Business Administration"])
def admin_create_plan(
    payload: PlanInput,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, Any]:
    gateway_plan_id = None
    if payload.billing_interval in {"monthly", "yearly"} and payload.price_minor > 0:
        provider = _select_payment_provider(payload.currency, recurring=True)
        if provider == "razorpay":
            provider_plan = _razorpay_request(
                "/plans",
                method="POST",
                payload={
                    "period": payload.billing_interval,
                    "interval": 1,
                    "item": {
                        "name": payload.name,
                        "amount": payload.price_minor,
                        "currency": payload.currency,
                        "description": f"{payload.tier.title()} career platform subscription",
                    },
                },
            )
            gateway_plan_id = provider_plan.get("id")
            if not isinstance(gateway_plan_id, str):
                raise HTTPException(status_code=502, detail="Payment provider did not return a plan reference.")
    now = utc_now()
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO business_plans"
            "(id, name, tier, billing_interval, price_minor, currency, credits_grant, entitlement_json, "
            "gateway_plan_id, active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payload.id, payload.name.strip(), payload.tier, payload.billing_interval,
                payload.price_minor, payload.currency, payload.credits_grant,
                json.dumps(payload.entitlements), gateway_plan_id, int(payload.active), now, now,
            ),
        )
        row = connection.execute("SELECT * FROM business_plans WHERE id=?", (payload.id,)).fetchone()
    return _row_dict(row)


@router.patch("/business/admin/plans/{plan_id}/active", tags=["Business Administration"])
def admin_set_plan_active(
    plan_id: str,
    active: bool,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, bool]:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_plans SET active=?, updated_at=? WHERE id=?",
            (int(active), utc_now(), plan_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Plan was not found.")
    return {"active": active}


@router.put("/business/admin/ai-pricing/{operation}", tags=["Business Administration"])
def admin_set_ai_pricing(
    operation: str,
    payload: OperationPricingInput,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, Any]:
    if not operation or len(operation) > 80:
        raise HTTPException(status_code=422, detail="Invalid AI operation name.")
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO business_operation_pricing"
            "(operation, credit_cost, required_entitlement, enabled, updated_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(operation) DO UPDATE SET "
            "credit_cost=excluded.credit_cost, required_entitlement=excluded.required_entitlement, "
            "enabled=excluded.enabled, updated_at=excluded.updated_at",
            (
                operation, payload.credit_cost, payload.required_entitlement,
                int(payload.enabled), utc_now(),
            ),
        )
    return {
        "operation": operation,
        "credit_cost": payload.credit_cost,
        "required_entitlement": payload.required_entitlement,
        "enabled": payload.enabled,
    }


@router.get("/business/admin/ai-pricing", tags=["Business Administration"])
def admin_get_ai_pricing(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT operation, credit_cost, required_entitlement, enabled, updated_at "
            "FROM business_operation_pricing ORDER BY operation"
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/business/admin/settings", tags=["Business Administration"])
def admin_get_business_settings(user: dict[str, str] = Depends(_admin_user)) -> dict[str, int]:
    with database() as connection:
        return {
            "free_monthly_credits": _business_setting(connection, "free_monthly_credits", 20),
            "referral_reward_credits": _business_setting(connection, "referral_reward_credits", 50),
        }


@router.put("/business/admin/settings", tags=["Business Administration"])
def admin_set_business_settings(
    payload: BusinessSettingsInput,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, int]:
    now = utc_now()
    with database(immediate=True) as connection:
        for key, value in payload.model_dump().items():
            connection.execute(
                "INSERT INTO business_settings(setting_key, setting_value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value, "
                "updated_at=excluded.updated_at",
                (key, str(value), now),
            )
    return payload.model_dump()


@router.post("/business/admin/coupons", status_code=201, tags=["Business Administration"])
def admin_create_coupon(
    payload: CouponInput,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, Any]:
    coupon_id = str(uuid.uuid4())
    expires = payload.expires_at.astimezone(timezone.utc).isoformat() if payload.expires_at else None
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO business_coupons"
            "(id, code, discount_type, discount_value, currency, max_redemptions, expires_at, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                coupon_id, payload.code.upper(), payload.discount_type,
                payload.discount_value, payload.currency, payload.max_redemptions,
                expires, utc_now(),
            ),
        )
    return {"id": coupon_id, "code": payload.code.upper(), "status": "active"}


@router.get("/business/admin/coupons", tags=["Business Administration"])
def admin_list_coupons(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT id, code, discount_type, discount_value, currency, max_redemptions, "
            "redemption_count, expires_at, active, created_at "
            "FROM business_coupons ORDER BY created_at DESC LIMIT 500"
        ).fetchall()
    return [dict(row) for row in rows]


@router.patch("/business/admin/coupons/{coupon_id}/active", tags=["Business Administration"])
def admin_set_coupon_active(
    coupon_id: str,
    active: bool,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, bool]:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_coupons SET active=? WHERE id=?",
            (int(active), coupon_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Coupon was not found.")
    return {"active": active}


@router.post("/business/admin/marketplace/{listing_id}/approve", tags=["Business Administration"])
def admin_approve_marketplace_listing(
    listing_id: str,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, bool]:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_marketplace_listings SET active=1, updated_at=? WHERE id=?",
            (utc_now(), listing_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Marketplace listing was not found.")
    return {"active": True}


@router.patch("/business/admin/leads/{lead_id}", tags=["Business Administration"])
def admin_update_lead(
    lead_id: str,
    payload: AdminStatusUpdate,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, str]:
    if payload.status not in {"reviewing", "approved", "declined", "closed"}:
        raise HTTPException(status_code=422, detail="Unsupported business lead status.")
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_leads SET status=?, updated_at=? WHERE id=?",
            (payload.status, utc_now(), lead_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Business partnership request was not found.")
    return {"status": payload.status}


@router.patch("/business/admin/affiliates/{affiliate_user_id}", tags=["Business Administration"])
def admin_update_affiliate(
    affiliate_user_id: str,
    payload: AdminStatusUpdate,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, Any]:
    if payload.status not in {"approved", "rejected", "suspended"}:
        raise HTTPException(status_code=422, detail="Unsupported affiliate status.")
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_affiliates SET status=?, commission_basis_points=COALESCE(?, commission_basis_points), "
            "updated_at=? WHERE user_id=?",
            (payload.status, payload.commission_basis_points, utc_now(), affiliate_user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Affiliate application was not found.")
    return {"status": payload.status, "commission_basis_points": payload.commission_basis_points}


@router.post("/business/admin/affiliate-conversions/{conversion_id}/paid", tags=["Business Administration"])
def admin_mark_affiliate_paid(
    conversion_id: str,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, str]:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_affiliate_conversions SET status='paid' WHERE id=? AND status='approved'",
            (conversion_id,),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=409, detail="Only an approved affiliate commission can be marked paid.")
    return {"status": "paid"}


@router.get("/business/admin/leads", tags=["Business Administration"])
def admin_list_leads(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT l.*, u.email FROM business_leads l JOIN users u ON u.id=l.user_id "
            "ORDER BY l.created_at DESC LIMIT 500"
        ).fetchall()
    return [{**dict(row), "details": reveal_text(row["details"])} for row in rows]


@router.get("/business/admin/affiliates", tags=["Business Administration"])
def admin_list_affiliates(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT a.user_id, a.code, a.status, a.commission_basis_points, a.created_at, u.email "
            "FROM business_affiliates a JOIN users u ON u.id=a.user_id "
            "ORDER BY a.created_at DESC LIMIT 500"
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/business/admin/affiliate-conversions", tags=["Business Administration"])
def admin_list_affiliate_conversions(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT c.*, a.code FROM business_affiliate_conversions c "
            "JOIN business_affiliates a ON a.user_id=c.affiliate_user_id "
            "ORDER BY c.created_at DESC LIMIT 500"
        ).fetchall()
    return [dict(row) for row in rows]


@router.patch(
    "/business/admin/affiliate-conversions/{conversion_id}",
    tags=["Business Administration"],
)
def admin_update_affiliate_conversion(
    conversion_id: str,
    payload: AffiliateConversionUpdate,
    user: dict[str, str] = Depends(_admin_user),
) -> dict[str, str]:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE business_affiliate_conversions SET status=? WHERE id=? AND status='pending'",
            (payload.status, conversion_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=409, detail="Only a pending affiliate conversion can be reconciled.")
    return {"status": payload.status}


@router.get("/business/admin/marketplace/listings", tags=["Business Administration"])
def admin_list_marketplace_listings(user: dict[str, str] = Depends(_admin_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT l.id, l.provider_user_id, l.listing_type, l.title, l.description, "
            "l.price_minor, l.currency, l.active, l.created_at, u.email AS provider_email "
            "FROM business_marketplace_listings l JOIN users u ON u.id=l.provider_user_id "
            "ORDER BY l.created_at DESC LIMIT 500"
        ).fetchall()
    return [dict(row) for row in rows]
