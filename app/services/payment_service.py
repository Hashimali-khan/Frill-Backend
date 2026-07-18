from app.config import settings
from app.core.exceptions import ValidationAppError


async def process_payment(payment_method: str, total: float, wallet_number: str | None) -> dict:
    """Process payment based on method. Returns payment metadata."""

    if payment_method == "cod":
        return {"payment_status": "pending_delivery", "provider": "cod"}

    if payment_method == "stripe":
        if not settings.stripe_enabled:
            raise ValidationAppError("Online payments are not yet available")

        import stripe
        stripe.api_key = settings.stripe_secret_key

        # Create a PaymentIntent — the frontend will confirm it with Stripe.js
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),   # Stripe expects amount in smallest currency unit
            currency="pkr",
            metadata={"source": "frill_backend"},
        )
        return {
            "payment_status": "requires_confirmation",
            "provider": "stripe",
            "client_secret": intent.client_secret,
        }

    if payment_method in ("jazzcash", "easypaisa"):
        # Wallet payments — for now, record the wallet number and process manually
        if not wallet_number:
            raise ValidationAppError(f"{payment_method} requires a wallet number")
        return {"payment_status": "pending_verification", "provider": payment_method}

    raise ValidationAppError(f"Unsupported payment method: {payment_method}")