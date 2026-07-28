import uuid
import os
from decimal import Decimal
from datetime import datetime
from typing import Optional
import stripe
from sqlalchemy.orm import Session
from jinja2 import Template
from src.models.billing import Invoice, BillingCycle, StripeCustomer


INVOICE_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; }
        .invoice-details { margin: 20px 0; }
        .line-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .total-section { margin-top: 30px; font-size: 18px; font-weight: bold; }
        .footer { margin-top: 40px; text-align: center; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Invoice #{{ invoice_id }}</h1>
            <p>aimodels.cloud</p>
        </div>

        <div class="invoice-details">
            <p><strong>Bill To:</strong> {{ customer_email }}</p>
            <p><strong>Invoice Date:</strong> {{ issued_date }}</p>
            <p><strong>Due Date:</strong> {{ due_date }}</p>
        </div>

        <div class="invoice-details">
            <div class="line-item">
                <span><strong>Description</strong></span>
                <span><strong>Amount</strong></span>
            </div>
            {% for item in items %}
            <div class="line-item">
                <span>{{ item.description }} ({{ item.quantity }})</span>
                <span>${{ item.amount }}</span>
            </div>
            {% endfor %}
            <div class="line-item" style="border-top: 2px solid #333; margin-top: 20px;">
                <span><strong>Subtotal</strong></span>
                <span><strong>${{ subtotal }}</strong></span>
            </div>
            {% if tax_amount %}
            <div class="line-item">
                <span>Tax</span>
                <span>${{ tax_amount }}</span>
            </div>
            {% endif %}
            {% if discount_amount %}
            <div class="line-item">
                <span>Discount</span>
                <span>-${{ discount_amount }}</span>
            </div>
            {% endif %}
            <div class="line-item total-section">
                <span>Total Due</span>
                <span>${{ total_amount }}</span>
            </div>
        </div>

        <div class="footer">
            <p>Thank you for using aimodels.cloud</p>
            <p>Questions? Contact support@aimodels.cloud</p>
        </div>
    </div>
</body>
</html>
"""


class InvoiceService:
    @staticmethod
    def create_invoice(
        db: Session,
        customer_id: str,
        billing_cycle_id: str
    ) -> Invoice:
        customer = db.query(StripeCustomer).filter_by(id=customer_id).first()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        cycle = db.query(BillingCycle).filter_by(id=billing_cycle_id).first()
        if not cycle:
            raise ValueError(f"Billing cycle {billing_cycle_id} not found")

        existing = db.query(Invoice).filter_by(
            customer_id=customer_id,
            billing_cycle_id=billing_cycle_id
        ).first()
        if existing:
            return existing

        stripe_invoice = stripe.Invoice.create(
            customer=customer.stripe_customer_id,
            collection_method="send_invoice",
            days_until_due=30,
            auto_advance=False,
            metadata={
                "customer_id": customer_id,
                "billing_cycle_id": billing_cycle_id
            }
        )

        stripe.InvoiceLineItem.create(
            invoice=stripe_invoice.id,
            customer=customer.stripe_customer_id,
            amount=int(cycle.subtotal_usd * 100),
            currency="usd",
            description=f"API Usage - {cycle.period_start.strftime('%Y-%m-%d')} to {cycle.period_end.strftime('%Y-%m-%d')}"
        )

        if cycle.tax_usd > 0:
            stripe.InvoiceLineItem.create(
                invoice=stripe_invoice.id,
                customer=customer.stripe_customer_id,
                amount=int(cycle.tax_usd * 100),
                currency="usd",
                description="Tax"
            )

        stripe_invoice = stripe.Invoice.finalize_invoice(stripe_invoice.id)

        invoice = Invoice(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            stripe_invoice_id=stripe_invoice.id,
            billing_cycle_id=billing_cycle_id,
            amount_usd=cycle.total_usd,
            tax_usd=cycle.tax_usd,
            status="sent" if stripe_invoice.paid else "draft",
            issued_at=datetime.utcnow(),
            due_at=datetime.utcnow() + timedelta(days=30),
            pdf_url=stripe_invoice.hosted_invoice_url
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        return invoice

    @staticmethod
    def send_invoice_email(
        db: Session,
        invoice_id: str,
        recipient_email: Optional[str] = None
    ) -> dict:
        invoice = db.query(Invoice).filter_by(id=invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        customer = db.query(StripeCustomer).filter_by(id=invoice.customer_id).first()
        if not customer:
            raise ValueError(f"Customer not found")

        cycle = db.query(BillingCycle).filter_by(id=invoice.billing_cycle_id).first()
        if not cycle:
            raise ValueError(f"Billing cycle not found")

        email = recipient_email or customer.email

        items = [
            {
                "description": f"API Usage ({cycle.total_requests} requests)",
                "quantity": f"{cycle.total_tokens_input + cycle.total_tokens_output:,} tokens",
                "amount": f"{cycle.subtotal_usd:.2f}"
            }
        ]

        template = Template(INVOICE_EMAIL_TEMPLATE)
        html_content = template.render(
            invoice_id=invoice.stripe_invoice_id,
            customer_email=email,
            issued_date=invoice.issued_at.strftime("%Y-%m-%d"),
            due_date=invoice.due_at.strftime("%Y-%m-%d"),
            items=items,
            subtotal=f"{cycle.subtotal_usd:.2f}",
            tax_amount=f"{cycle.tax_usd:.2f}" if cycle.tax_usd > 0 else None,
            discount_amount=f"{cycle.discount_usd:.2f}" if cycle.discount_usd > 0 else None,
            total_amount=f"{cycle.total_usd:.2f}"
        )

        InvoiceService._send_email(
            to_email=email,
            subject=f"Invoice #{invoice.stripe_invoice_id} from aimodels.cloud",
            html_content=html_content
        )

        return {"status": "sent", "email": email}

    @staticmethod
    def get_invoice(db: Session, invoice_id: str) -> Optional[Invoice]:
        return db.query(Invoice).filter_by(id=invoice_id).first()

    @staticmethod
    def list_invoices(
        db: Session,
        customer_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        invoices = db.query(Invoice).filter_by(
            customer_id=customer_id
        ).order_by(Invoice.created_at.desc()).limit(limit).offset(offset).all()

        total = db.query(Invoice).filter_by(customer_id=customer_id).count()

        return {
            "total": total,
            "invoices": [
                {
                    "id": inv.id,
                    "stripe_id": inv.stripe_invoice_id,
                    "amount": float(inv.amount_usd),
                    "status": inv.status,
                    "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
                    "due_at": inv.due_at.isoformat() if inv.due_at else None,
                    "pdf_url": inv.pdf_url
                }
                for inv in invoices
            ]
        }

    @staticmethod
    def mark_as_paid(db: Session, invoice_id: str) -> Invoice:
        invoice = db.query(Invoice).filter_by(id=invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        stripe.Invoice.pay(invoice.stripe_invoice_id)

        invoice.status = "paid"
        invoice.paid_at = datetime.utcnow()
        db.commit()
        db.refresh(invoice)

        return invoice

    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str) -> bool:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            smtp_host = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            from_email = os.getenv("FROM_EMAIL", "noreply@aimodels.cloud")

            if not smtp_user or not smtp_password:
                print(f"WARNING: Email not sent. SMTP credentials not configured.")
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, [to_email], msg.as_string())

            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False


from datetime import timedelta
