#!/usr/bin/env python3
"""Check whether today is an A-share trading day.

The date is evaluated in Asia/Shanghai and Baostock supplies the exchange
calendar.  When running in GitHub Actions, the result is exposed as the
``is_trading_day`` step output.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        dest="calendar_date",
        help="Date to check in YYYY-MM-DD format (defaults to today in Shanghai)",
    )
    return parser.parse_args()


def _selected_date(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _write_github_output(is_trading_day: bool, calendar_date: date) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"is_trading_day={str(is_trading_day).lower()}\n")
        output.write(f"calendar_date={calendar_date.isoformat()}\n")


def _query_baostock(calendar_date: date) -> bool:
    import baostock as bs

    login_result = bs.login()
    if login_result.error_code != "0":
        raise RuntimeError(
            f"Baostock login failed: {login_result.error_code} "
            f"{login_result.error_msg}"
        )

    try:
        date_text = calendar_date.isoformat()
        result = bs.query_trade_dates(start_date=date_text, end_date=date_text)
        if result.error_code != "0":
            raise RuntimeError(
                f"Baostock calendar query failed: {result.error_code} "
                f"{result.error_msg}"
            )
        if not result.next():
            raise RuntimeError(f"Baostock returned no calendar row for {date_text}")

        row = result.get_row_data()
        if len(row) < 2:
            raise RuntimeError(f"Unexpected Baostock calendar response: {row!r}")
        return row[1] == "1"
    finally:
        bs.logout()


def main() -> int:
    args = _parse_args()
    try:
        calendar_date = _selected_date(args.calendar_date)
        is_trading_day = _query_baostock(calendar_date)
    except (ImportError, RuntimeError, ValueError) as exc:
        print(f"Trading-day check failed: {exc}", file=sys.stderr)
        return 1

    _write_github_output(is_trading_day, calendar_date)
    status = "trading day" if is_trading_day else "market closed"
    print(f"A-share calendar: {calendar_date.isoformat()} is {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
