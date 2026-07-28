import os
import hashlib
import hmac
import json
from typing import Optional
import stripe
from sqlalchemy.orm import Session
from src.models.billing import StripeCustomer, Invoice, BillingCycle
from src.services.invoice_service import InvoiceService


class WebhookService:
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    @staticmethod
    def verify_stripe_signature(
        body: bytes,
        signature: str
    ) -> bool:
        if not WebhookService.STRIPE_WEBHOOK_SECRET:
            return False

        try:
            timestamp, signed_content = signature.split(",")[0].split("=")[1], ",".join(signature.split(",")[1:])
            expected_sig = hmac.new(
                WebhookService.STRIPE_WEBHOOK_SECRET.encode(),
                f"{timestamp}.{body.decode()}".encode(),
                hashlib.sha256
            ).hexdigest()
            actual_sig = signed_content.split("=")[1]
            return hmac.compare_digest(expected_sig, actual_sig)
        except Exception:
            return False

    @staticmethod
    def handle_payment_intent_succeeded(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            payment_intent = event_data.get("object", {})
            customer_id = payment_intent.get("metadata", {}).get("customer_id")
            invoice_id = payment_intent.get("metadata", {}).get("invoice_id")

            if invoice_id:
                invoice = db.query(Invoice).filter_by(id=invoice_id).first()
                if invoice:
                    invoice.status = "paid"
                    from datetime import datetime
                    invoice.paid_at = datetime.utcnow()
                    db.commit()
                    return True

            return False
        except Exception as e:
            print(f"Error handling payment_intent.succeeded: {e}")
            return False

    @staticmethod
    def handle_payment_intent_payment_failed(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            payment_intent = event_data.get("object", {})
            customer_id = payment_intent.get("metadata", {}).get("customer_id")
            invoice_id = payment_intent.get("metadata", {}).get("invoice_id")

            if invoice_id:
                invoice = db.query(Invoice).filter_by(id=invoice_id).first()
                if invoice:
                    invoice.status = "failed"
                    db.commit()
                    return True

            return False
        except Exception as e:
            print(f"Error handling payment_intent.payment_failed: {e}")
            return False

    @staticmethod
    def handle_invoice_payment_succeeded(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            stripe_invoice = event_data.get("object", {})
            stripe_invoice_id = stripe_invoice.get("id")
            customer_id = stripe_invoice.get("customer")

            invoice = db.query(Invoice).filter_by(stripe_invoice_id=stripe_invoice_id).first()
            if invoice:
                invoice.status = "paid"
                from datetime import datetime
                invoice.paid_at = datetime.utcnow()
                db.commit()
                return True

            return False
        except Exception as e:
            print(f"Error handling invoice.payment_succeeded: {e}")
            return False

    @staticmethod
    def handle_invoice_payment_failed(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            stripe_invoice = event_data.get("object", {})
            stripe_invoice_id = stripe_invoice.get("id")

            invoice = db.query(Invoice).filter_by(stripe_invoice_id=stripe_invoice_id).first()
            if invoice:
                invoice.status = "failed"
                db.commit()

                customer = db.query(StripeCustomer).filter_by(id=invoice.customer_id).first()
                if customer:
                    retry_count = stripe_invoice.get("attempt_count", 0)
                    if retry_count >= 3:
                        customer.is_active = False
                        db.commit()

                return True

            return False
        except Exception as e:
            print(f"Error handling invoice.payment_failed: {e}")
            return False

    @staticmethod
    def handle_customer_subscription_updated(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            subscription = event_data.get("object", {})
            stripe_customer_id = subscription.get("customer")
            stripe_subscription_id = subscription.get("id")

            customer = db.query(StripeCustomer).filter_by(
                stripe_customer_id=stripe_customer_id
            ).first()

            if customer:
                customer.stripe_subscription_id = stripe_subscription_id
                db.commit()
                return True

            return False
        except Exception as e:
            print(f"Error handling customer.subscription.updated: {e}")
            return False

    @staticmethod
    def handle_customer_subscription_deleted(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            subscription = event_data.get("object", {})
            stripe_customer_id = subscription.get("customer")

            customer = db.query(StripeCustomer).filter_by(
                stripe_customer_id=stripe_customer_id
            ).first()

            if customer:
                customer.stripe_subscription_id = None
                from src.models.billing import BillingTier
                customer.current_tier = BillingTier.FREE
                db.commit()
                return True

            return False
        except Exception as e:
            print(f"Error handling customer.subscription.deleted: {e}")
            return False

    @staticmethod
    def handle_charge_refunded(
        db: Session,
        event_data: dict
    ) -> bool:
        try:
            charge = event_data.get("object", {})
            stripe_invoice_id = charge.get("invoice")

            if stripe_invoice_id:
                invoice = db.query(Invoice).filter_by(stripe_invoice_id=stripe_invoice_id).first()
                if invoice:
                    invoice.status = "refunded"
                    db.commit()
                    return True

            return False
        except Exception as e:
            print(f"Error handling charge.refunded: {e}")
            return False

    @staticmethod
    def process_webhook(
        db: Session,
        event_type: str,
        event_data: dict
    ) -> dict:
        handlers = {
            "payment_intent.succeeded": WebhookService.handle_payment_intent_succeeded,
            "payment_intent.payment_failed": WebhookService.handle_payment_intent_payment_failed,
            "invoice.payment_succeeded": WebhookService.handle_invoice_payment_succeeded,
            "invoice.payment_failed": WebhookService.handle_invoice_payment_failed,
            "customer.subscription.updated": WebhookService.handle_customer_subscription_updated,
            "customer.subscription.deleted": WebhookService.handle_customer_subscription_deleted,
            "charge.refunded": WebhookService.handle_charge_refunded,
        }

        handler = handlers.get(event_type)
        if not handler:
            return {"success": False, "error": f"Unknown event type: {event_type}"}

        try:
            result = handler(db, event_data)
            return {"success": result}
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def construct_event(
        payload: bytes,
        signature: str
    ) -> Optional[dict]:
        try:
            return stripe.Webhook.construct_event(
                payload,
                signature,
                WebhookService.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            return None
