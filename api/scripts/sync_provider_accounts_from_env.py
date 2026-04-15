from __future__ import annotations

import argparse
import json

from fastapi import HTTPException

from app.db.session import SessionLocal
from app.domains.platform.services.provider_accounts import ProviderAccountService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync platform provider accounts from current environment credentials."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write synced provider accounts into the database.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run live verification for synced platform accounts after apply.",
    )
    parser.add_argument(
        "--sync-balance",
        action="store_true",
        help="Sync provider balance for synced accounts when supported.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        service = ProviderAccountService(session)
        provider_codes = [item.provider_code for item in service._list_env_backed_provider_configs()]
        print(
            json.dumps(
                {
                    "env_backed_provider_codes": provider_codes,
                    "count": len(provider_codes),
                    "mode": "apply" if args.apply else "dry_run",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not args.apply:
            return 0

        synced_accounts = service.sync_platform_accounts_from_env()
        session.commit()
        print(
            json.dumps(
                {
                    "synced_count": len(synced_accounts),
                    "accounts": [
                        {
                            "id": item["id"],
                            "provider_code": item["provider_code"],
                            "short_id": item["short_id"],
                            "display_name": item["display_name"],
                        }
                        for item in synced_accounts
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        if not args.verify and not args.sync_balance:
            return 0

        results: list[dict[str, str | int]] = []
        for item in synced_accounts:
            row: dict[str, str | int] = {
                "id": int(item["id"]),
                "provider_code": str(item["provider_code"]),
                "short_id": str(item["short_id"]),
            }
            if args.verify:
                try:
                    verified = service.verify_platform_account(account_id=int(item["id"]))
                    row["verify"] = str(verified["verification_status"])
                except HTTPException as exc:
                    row["verify"] = f"failed:{exc.detail}"
            if args.sync_balance:
                try:
                    balanced = service.sync_balance_platform_account(account_id=int(item["id"]))
                    row["balance"] = str(balanced["balance_status"])
                except HTTPException as exc:
                    row["balance"] = f"failed:{exc.detail}"
            results.append(row)
            session.commit()

        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
