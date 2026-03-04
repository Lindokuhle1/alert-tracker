"""
Small CLI tool to import semicolon-delimited CSV alert exports into the
existing SQLite database used by the project.

Usage:
    python import_csv.py alerts.csv [--dry-run]

Expected CSV header (semicolon-separated):
    Created time;Originator;Type;Severity;Status;Label

This script maps:
- `Originator` -> device serial number
- `Type` or `Label` -> fault name
- `Status` -> ACTIVE or CLEARED (heuristic: contains 'Cleared' -> CLEARED)

It uses `DatabaseManager` from `db.py` and calls `add_or_update_alert`.
"""

import csv
import argparse
import logging
from typing import Optional

from db import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def map_status(raw: Optional[str]) -> str:
    if not raw:
        return 'ACTIVE'
    if 'cleared' in raw.lower() or 'cleared' in raw:
        return 'CLEARED'
    return 'ACTIVE'


def import_csv(path: str, dry_run: bool = False):
    db = DatabaseManager()
    created = 0
    skipped = 0
    updated = 0

    with open(path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh, delimiter=';')
        for row in reader:
            serial = (row.get('Originator') or row.get('Originator ') or '').strip()
            # some CSVs might use 'Type' or 'Label' for the fault text
            fault = (row.get('Type') or row.get('Label') or '').strip()
            status_raw = (row.get('Status') or '').strip()
            status = map_status(status_raw)
            # priority column if present
            priority = (row.get('Priority') or '').strip().capitalize()
            if priority not in ('High','Mid','Low'):
                priority = 'Mid'
            if not serial:
                skipped += 1
                logger.debug('Skipping row with empty Originator: %r', row)
                continue
            notes = []
            if row.get('Created time'):
                notes.append(f"Created:{row.get('Created time')}")
            if row.get('Severity'):
                notes.append(f"Severity:{row.get('Severity')}")
            if row.get('Label'):
                notes.append(f"Label:{row.get('Label')}")
            notes_text = '; '.join(notes) if notes else None

            if dry_run:
                logger.info('DRY RUN - would import: %s | %s | %s', serial, fault, status)
                created += 1
                continue

            alert_id, was_updated = db.add_or_update_alert(
                serial_number=serial,
                fault_name=fault or 'Unknown Fault',
                status=status,
                notes=notes_text,
                priority=priority
            )
            if was_updated:
                updated += 1
            else:
                created += 1

    logger.info('Import finished: created=%d updated=%d skipped=%d', created, updated, skipped)


def main():
    parser = argparse.ArgumentParser(description='Import semicolon CSV alerts into DB')
    parser.add_argument('csv_path', help='Path to semicolon-delimited CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Do not modify DB; just report')
    args = parser.parse_args()

    import_csv(args.csv_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
