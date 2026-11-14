"""Backup or restore a PostgreSQL custom-format archive using installed client tools."""
import argparse
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['backup', 'restore'])
parser.add_argument('archive', type=Path)
parser.add_argument('--database', required=True, help='Database name or libpq connection string; prefer PG* environment variables for credentials')
args = parser.parse_args()
if args.action == 'backup':
    if args.archive.exists(): parser.error('Refusing to overwrite an existing backup')
    subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--file', str(args.archive), '--dbname', args.database], check=True)
else:
    # Intentionally no --clean: restore only into a newly created empty database.
    subprocess.run(['pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--dbname', args.database, str(args.archive)], check=True)
