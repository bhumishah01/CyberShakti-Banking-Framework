"""RuralShield CLI runtime prototype for end-to-end demo."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RuralShield CLI")
    parser.add_argument("--db", default="data/ruralshield.db", help="SQLite DB path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db_cmd = subparsers.add_parser("init-db", help="Initialize local database")
    init_db_cmd.set_defaults(func=cmd_init_db)

    add_user = subparsers.add_parser("add-user", help="Register a user with PIN")
    add_user.add_argument("--user-id", required=True)
    add_user.add_argument("--phone", required=True)
    add_user.add_argument("--pin", required=True)
    add_user.set_defaults(func=cmd_add_user)

    add_tx = subparsers.add_parser("add-tx", help="Create secure offline transaction")
    add_tx.add_argument("--user-id", required=True)
    add_tx.add_argument("--pin", required=True)
    add_tx.add_argument("--amount", type=float, required=True)
    add_tx.add_argument("--recipient", required=True)
    add_tx.set_defaults(func=cmd_add_tx)

    list_tx = subparsers.add_parser("list-tx", help="List user transactions")
    list_tx.add_argument("--user-id", required=True)
    list_tx.add_argument("--pin", required=True)
    list_tx.add_argument("--limit", type=int, default=10)
    list_tx.set_defaults(func=cmd_list_tx)

    sync_cmd = subparsers.add_parser("sync", help="Sync pending outbox records")
    sync_cmd.add_argument("--server-url", default="http://localhost:8000")
    sync_cmd.set_defaults(func=cmd_sync)

    audit_cmd = subparsers.add_parser("audit-check", help="Verify tamper-evident audit chain")
    audit_cmd.set_defaults(func=cmd_audit_check)

    return parser


def cmd_init_db(args: argparse.Namespace) -> None:
    from src.database.init_db import init_db

    db_path = Path(args.db)
    init_db(db_path)
    print(f"Database initialized: {db_path}")


def cmd_add_user(args: argparse.Namespace) -> None:
    from src.auth.service import create_user

    db_path = Path(args.db)
    create_user(
        user_id=args.user_id,
        phone_number=args.phone,
        pin=args.pin,
        db_path=db_path,
    )
    print(f"User created: {args.user_id}")


def cmd_add_tx(args: argparse.Namespace) -> None:
    from src.database.transaction_store import create_secure_transaction

    db_path = Path(args.db)
    stored = create_secure_transaction(
        user_id=args.user_id,
        pin=args.pin,
        amount=args.amount,
        recipient=args.recipient,
        db_path=db_path,
    )
    print(
        "Transaction created: "
        f"tx_id={stored.tx_id} risk_score={stored.risk_score} "
        f"risk_level={stored.risk_level} reasons={','.join(stored.reason_codes) if stored.reason_codes else 'NONE'}"
    )


def cmd_list_tx(args: argparse.Namespace) -> None:
    from src.database.transaction_store import list_secure_transactions

    db_path = Path(args.db)
    items = list_secure_transactions(
        user_id=args.user_id,
        pin=args.pin,
        db_path=db_path,
        limit=args.limit,
    )
    if not items:
        print("No transactions found")
        return

    for item in items:
        print(
            f"{item['timestamp']} | {item['tx_id']} | amount={item['amount']} "
            f"recipient={item['recipient']} risk={item['risk_score']}({item['risk_level']}) "
            f"status={item['status']}"
        )


def cmd_sync(args: argparse.Namespace) -> None:
    from src.sync.client import make_http_sender
    from src.sync.manager import sync_outbox

    db_path = Path(args.db)
    sender = make_http_sender(args.server_url)
    summary = sync_outbox(db_path=db_path, sender=sender)
    print(
        "Sync summary: "
        f"processed={summary.processed} synced={summary.synced} "
        f"duplicates={summary.duplicates} retried={summary.retried}"
    )


def cmd_audit_check(args: argparse.Namespace) -> None:
    from src.audit.chain import verify_audit_chain

    db_path = Path(args.db)
    result = verify_audit_chain(db_path=db_path)
    status = "VALID" if result.is_valid else "INVALID"
    print(f"Audit chain: {status} (entries={result.checked_entries})")
    if result.error:
        print(f"Error: {result.error}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
