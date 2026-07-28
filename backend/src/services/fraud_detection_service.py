from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from src.models.billing import UsageRecord, FraudAlert, StripeCustomer


class FraudDetectionService:
    @staticmethod
    def detect_usage_spike(
        db: Session,
        customer_id: str,
        current_usage: Decimal,
        threshold_multiplier: float = 3.0
    ) -> tuple[bool, str]:
        now = datetime.utcnow()
        last_7_days = now - timedelta(days=7)

        avg_last_7_days = db.query(
            func.avg(UsageRecord.cost_usd)
        ).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.timestamp >= last_7_days
            )
        ).scalar() or Decimal("0")

        if current_usage > (avg_last_7_days * Decimal(str(threshold_multiplier))):
            return True, f"Usage spike detected: {current_usage} vs avg {avg_last_7_days}"

        return False, ""

    @staticmethod
    def detect_rapid_requests(
        db: Session,
        customer_id: str,
        time_window_minutes: int = 5,
        threshold: int = 100
    ) -> tuple[bool, str]:
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        count = db.query(func.count(UsageRecord.id)).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.timestamp >= cutoff_time
            )
        ).scalar()

        if count > threshold:
            return True, f"Rapid requests detected: {count} in {time_window_minutes} minutes"

        return False, ""

    @staticmethod
    def detect_unusual_pattern(
        db: Session,
        customer_id: str,
        model_id: str
    ) -> tuple[bool, str]:
        customer = db.query(StripeCustomer).filter_by(id=customer_id).first()
        if not customer:
            return False, ""

        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_30_days = now - timedelta(days=30)

        avg_daily_requests = db.query(
            func.count(UsageRecord.id) / 30.0
        ).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.timestamp >= last_30_days
            )
        ).scalar() or 0

        today_requests = db.query(func.count(UsageRecord.id)).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.timestamp >= today
            )
        ).scalar() or 0

        if today_requests > (avg_daily_requests * 5):
            return True, f"Unusual pattern: Today {today_requests} vs avg daily {avg_daily_requests}"

        return False, ""

    @staticmethod
    def check_account_status(
        db: Session,
        customer_id: str
    ) -> dict:
        customer = db.query(StripeCustomer).filter_by(id=customer_id).first()
        if not customer:
            return {"status": "unknown", "alerts": []}

        alerts = []

        now = datetime.utcnow()
        current_month_cost = db.query(
            func.sum(UsageRecord.cost_usd)
        ).filter(
            and_(
                UsageRecord.customer_id == customer_id,
                UsageRecord.timestamp >= now.replace(day=1, hour=0, minute=0, second=0)
            )
        ).scalar() or Decimal("0")

        is_spike, msg = FraudDetectionService.detect_usage_spike(db, customer_id, current_month_cost)
        if is_spike:
            alerts.append({"type": "usage_spike", "severity": "high", "message": msg})

        is_rapid, msg = FraudDetectionService.detect_rapid_requests(db, customer_id)
        if is_rapid:
            alerts.append({"type": "rapid_requests", "severity": "high", "message": msg})

        is_unusual, msg = FraudDetectionService.detect_unusual_pattern(db, customer_id, "any")
        if is_unusual:
            alerts.append({"type": "unusual_pattern", "severity": "medium", "message": msg})

        for alert in alerts:
            existing = db.query(FraudAlert).filter(
                and_(
                    FraudAlert.customer_id == customer_id,
                    FraudAlert.alert_type == alert["type"],
                    FraudAlert.is_resolved == False
                )
            ).first()

            if not existing:
                fraud_alert = FraudAlert(
                    id=f"alert-{customer_id}-{alert['type']}-{now.timestamp()}",
                    customer_id=customer_id,
                    alert_type=alert["type"],
                    severity=alert["severity"],
                    message=alert["message"]
                )
                db.add(fraud_alert)

        db.commit()

        status = "normal"
        if any(a["severity"] == "high" for a in alerts):
            status = "risky"
        elif len(alerts) > 0:
            status = "caution"

        return {
            "status": status,
            "alerts": alerts,
            "current_month_cost": float(current_month_cost)
        }

    @staticmethod
    def resolve_fraud_alert(
        db: Session,
        alert_id: str,
        resolution_notes: str = ""
    ) -> bool:
        alert = db.query(FraudAlert).filter_by(id=alert_id).first()
        if not alert:
            return False

        alert.is_resolved = True
        db.commit()
        return True

    @staticmethod
    def get_fraud_alerts(
        db: Session,
        customer_id: str,
        unresolved_only: bool = True
    ) -> list[dict]:
        query = db.query(FraudAlert).filter_by(customer_id=customer_id)

        if unresolved_only:
            query = query.filter_by(is_resolved=False)

        alerts = query.order_by(FraudAlert.detected_at.desc()).all()

        return [
            {
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "detected_at": a.detected_at.isoformat(),
                "is_resolved": a.is_resolved
            }
            for a in alerts
        ]

    @staticmethod
    def should_block_request(
        db: Session,
        customer_id: str
    ) -> tuple[bool, str]:
        status = FraudDetectionService.check_account_status(db, customer_id)

        if status["status"] == "risky":
            high_severity_alerts = [a for a in status["alerts"] if a["severity"] == "high"]
            if len(high_severity_alerts) >= 2:
                return True, "Multiple high-severity fraud alerts detected. Account suspended."

        return False, ""
