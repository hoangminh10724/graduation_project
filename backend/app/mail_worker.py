"""Run with python -m app.mail_worker; SMTP delivery is at-least-once."""
import argparse
import hashlib
import hmac
import logging
import smtplib
import time
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.exc import SQLAlchemyError

from .auth import jwt_secret
from .db import session_factory
from .mailer import MailSettings, send_account_email
from .models import AccountAction, User
from .recovery import action_token, now

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


def deliver_one(create_session, settings: MailSettings) -> bool:
    current = now()
    lease_token = str(uuid4())
    with create_session() as db:
        # Expired, consumed and invalidated tokens must not remain queued indefinitely.
        current_version = select(User.token_version).where(User.id == AccountAction.user_id).scalar_subquery()
        db.execute(update(AccountAction).where(
            AccountAction.delivery_status.in_(["pending", "sending"]),
            or_(AccountAction.expires_at <= current, AccountAction.consumed.is_(True), AccountAction.token_version != current_version),
        ).values(delivery_status="failed", lease_token=None, lease_until=None))
        available = or_(
            (AccountAction.delivery_status == "pending") & (AccountAction.available_at <= current),
            (AccountAction.delivery_status == "sending") & (AccountAction.lease_until <= current),
        )
        db.execute(update(AccountAction).where(available, AccountAction.delivery_attempts >= MAX_ATTEMPTS).values(
            delivery_status="failed", lease_token=None, lease_until=None,
        ))
        candidate = select(AccountAction.id).where(
            available, AccountAction.delivery_attempts < MAX_ATTEMPTS,
        ).order_by(AccountAction.available_at, AccountAction.id).limit(1).scalar_subquery()
        action = db.scalar(update(AccountAction).where(
            AccountAction.id == candidate, available, AccountAction.delivery_attempts < MAX_ATTEMPTS,
        ).values(
            delivery_status="sending", lease_token=lease_token, lease_until=current + timedelta(minutes=2),
            delivery_attempts=AccountAction.delivery_attempts + 1,
        ).returning(AccountAction))
        if action is None:
            db.commit()
            return False
        user = db.get(User, action.user_id)
        token = action_token(action)
        valid = user is not None and hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), action.token_digest)
        action_id, purpose, attempt = action.id, action.purpose, action.delivery_attempts
        recipient = user.email if user else ""
        db.commit()
    # Never hold a database transaction or user lock during network delivery.
    delivered = False
    if valid:
        try:
            send_account_email(settings, recipient, purpose, token, action_id)
            delivered = True
        except (smtplib.SMTPException, OSError, ValueError) as error:
            logger.warning("Account email delivery failed (%s)", type(error).__name__)
    with create_session() as db:
        db.execute(update(AccountAction).where(
            AccountAction.id == action_id, AccountAction.lease_token == lease_token,
            AccountAction.delivery_status == "sending",
        ).values(
            delivery_status="sent" if delivered else ("pending" if valid and attempt < MAX_ATTEMPTS else "failed"),
            available_at=now() + timedelta(seconds=30 * 2 ** (attempt - 1)),
            lease_token=None, lease_until=None,
        ))
        db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Deliver queued WordSpeak account emails")
    parser.add_argument("--once", action="store_true", help="Drain currently available messages, then exit")
    parser.add_argument("--limit", type=int, default=100, help="Maximum messages per --once invocation")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    logging.basicConfig(level=logging.INFO)
    settings = MailSettings.load()
    jwt_secret()
    create_session = session_factory()
    processed = 0
    try:
        while True:
            try:
                worked = deliver_one(create_session, settings)
            except SQLAlchemyError:
                logger.error("Mail worker database unavailable")
                if args.once:
                    raise SystemExit(1) from None
                time.sleep(5)
                continue
            processed += int(worked)
            if args.once and (not worked or processed >= args.limit):
                break
            if not worked:
                time.sleep(2)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
