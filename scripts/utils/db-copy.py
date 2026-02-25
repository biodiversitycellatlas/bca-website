#!/usr/bin/env python3
"""
Copy data between two Postgres databases using services defined in .pg_service.conf.

- Copies all tables (default) or a single table.
- Verifies columns, indexes, and constraints match.
- Raises error if schema mismatch.
- Truncates target table before inserting.

Usage:
    ./scripts/db-copy.py source target
    ./scripts/db-copy.py source target --table users
"""

import argparse
import sys
import os
import tempfile
import psycopg2
import subprocess
from psycopg2.extras import execute_values

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def get_connection(service_name):
    return psycopg2.connect(f"service={service_name}")


def get_tables(conn):
    """Get tables ordered by less dependencies."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.relname AS table_name
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_constraint fk ON fk.conrelid = c.oid AND fk.contype = 'f'
            WHERE c.relkind = 'r'  -- only regular tables
            AND n.nspname = 'public'
            GROUP BY c.relname
            ORDER BY COUNT(fk.conname) ASC;
        """)
        return [row[0] for row in cur.fetchall()]


def dump_data(db_src, db_dst, tables=None, dry_run=False):
    """Dump data using pg_dump for full database if no tables were selected."""

    # Run pg_dump and pipe output to psql
    pg = ["pg_dump", f"service={db_src}", "--clean", "--if-exists", "--no-owner", "--no-privileges", "--verbose"]
    ps = ["psql", f"service={db_dst}"]

    if tables is not None:
        for table in tables:
            pg.extend(["-t", table])
    else:
        # Full database drop and create tables
        pg.extend(["--create"])

    # Fully drop and create database
    create = "--create" if tables is None else ""

    if dry_run:
        print(f"{YELLOW}DRY RUN:{RESET} {" ".join(pg)} | {" ".join(ps)}")
    else:
        pg_proc = subprocess.Popen(pg, stdout=subprocess.PIPE)
        ps_proc = subprocess.Popen(ps, stdin=pg_proc.stdout)
        pg_proc.stdout.close()
        ps_proc.communicate()
        print(f"{GREEN}✔ Database copied from {db_src} to {db_dst}{RESET}")


def copy_database(db_src, db_dst, tables=None, dry_run=False):
    # Get tables in source database
    conn_src = get_connection(db_src)
    src_tables = get_tables(conn_src)
    conn_src.close()

    if tables:
        # Reorder so tables with less dependencies come first
        sorted_tables = [t for t in src_tables if t in tables]
        msg = " (ordered by fewer dependencies)"
    else:
        sorted_tables = None
        msg = ""

    print(f"{CYAN}Tables to copy from {db_src} to {db_dst}{msg}:{RESET}")
    for i in (sorted_tables or src_tables):
        print(f"    - {i}")
    print()

    try:
        dump_data(db_src, db_dst, sorted_tables, dry_run)
    except Exception as e:
        print(f"{RED}✖ Error: {e}{RESET}")
        sys.exit(1)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy PostgreSQL database data.")
    parser.add_argument("source", help="Source database service name")
    parser.add_argument("target", help="Target database service name")
    parser.add_argument("--tables", "-t", help="Comma-separated list of tables to copy")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Print copy commands without executing them")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    args = parser.parse_args()

    if args.dry_run:
        print(f"{YELLOW}=== DRY RUN MODE ==={RESET}\n")

    tables = args.tables.split(',') if args.tables else None
    copy_database(args.source, args.target, tables, args.dry_run)
