#!/usr/bin/env python3
"""
Copy data between two Postgres databases using services defined in .pg_service.conf.

- Copies all tables (default) or a single table
- Resets database with --reset (drops and creates public schema)
- Excludes table data to be copied (useful to avoid copying large tables)

Usage:
    ./scripts/db-copy.py bca local
    ./scripts/db-copy.py bca local --tables app_species,app_dataset,app_publication

    # Reset database and copy all tables and schema
    ./scripts/db-copy.py bca local --reset

    # Reset database and copy all tables and schema (except data from some large tables)
    ./scripts/db-copy.py bca local --reset --exclude app_metacellgeneexpression,app_genecorrelation
"""

import argparse
import sys
import psycopg2
import subprocess
import time

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def get_connection(service_name):
    return psycopg2.connect(f"service={service_name}")


def get_tables(db):
    """Get tables ordered by less dependencies."""
    conn = get_connection(db)
    tables = None

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
        tables = [row[0] for row in cur.fetchall()]

    conn.close()
    return tables


def reset_database(db, dry_run=False):
    """Reset database by dropping and creating public schema."""
    drop_schema_sql = "DROP SCHEMA public CASCADE;"
    create_schema_sql = "CREATE SCHEMA public;"

    print(f"{YELLOW}DATABASE RESET (SQL): {CYAN}{drop_schema_sql} {create_schema_sql}{RESET}")
    if not dry_run:
        conn = get_connection(db)
        conn.autocommit = True  # required for DROP SCHEMA

        with conn.cursor() as cur:
            cur.execute(drop_schema_sql)
            cur.execute(create_schema_sql)

        conn.close()


def dump_data(db_src, db_dst, tables=[], exclude_table_data=[], args=None):
    """Dump data using pg_dump for selected (or all) tables."""

    # Run pg_dump and pipe output to psql
    pg = ["pg_dump", f"service={db_src}", "--no-owner", "--no-privileges", "--verbose"]
    ps = ["psql", f"service={db_dst}"]

    if args.data_only:
        pg.extend(["--data-only"])
    else:
        pg.extend(["--clean", "--if-exists"])

    if tables or exclude_table_data:
        for table in tables or []:
            pg.extend(["-t", table])
        for table in exclude_table_data or []:
            pg.extend(["--exclude-table-data", table])

    print(f"{YELLOW}DUMP DATA (SHELL):{CYAN} {' '.join(pg)} | {' '.join(ps)}{RESET}\n")
    if not args.dry_run:
        start = time.time()

        pg_proc = subprocess.Popen(pg, stdout=subprocess.PIPE)
        ps_proc = subprocess.Popen(ps, stdin=pg_proc.stdout)
        pg_proc.stdout.close()
        ps_proc.communicate()

        # Parse elapsed time
        minutes, seconds = divmod(time.time() - start, 60)
        elapsed = f"{int(minutes)}m {int(seconds)}s"

        print(f"{GREEN}✔ Database copied from {db_src} to {db_dst} in {elapsed}{RESET}")


def check_tables_exist(tables, src_tables, db_src, excluded=False):
    msg = "tables" if not excluded else "excluded tables"

    if tables:
        check_tables = set(tables) - set(src_tables)
        if check_tables:
            raise ValueError(f"User-provided {msg} not found in {db_src}: {', '.join(check_tables)}")


def copy_database(db_src, db_dst, tables=[], exclude_table_data=[], args=None):
    # Get tables in source database
    src_tables = get_tables(db_src)

    # Check if user gave non-existing tables in source database
    check_tables_exist(tables, src_tables, db_src)
    check_tables_exist(exclude_table_data, src_tables, db_src, excluded=True)

    if tables:
        # Reorder so tables with less dependencies come first
        list_tables = [t for t in src_tables if t in tables and t not in exclude_table_data]
        dump_tables = list_tables
    else:
        list_tables = [t for t in src_tables if t not in exclude_table_data]
        dump_tables = []  # dump all tables

    print(f"{CYAN}Tables to copy from {db_src} to {db_dst} (ordered by fewer dependencies):{RESET}")
    for i in list_tables:
        print(f"    - {i}")
    print()

    if args.reset_db:
        reset_database(db_dst, args.dry_run)
    dump_data(db_src, db_dst, dump_tables, exclude_table_data, args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy PostgreSQL database data.")
    parser.add_argument("source", help="Source database service name")
    parser.add_argument("target", help="Target database service name")
    parser.add_argument("--tables", "-t", help="Comma-separated list of tables to copy")
    parser.add_argument("--data-only", action="store_true", help="Dump only the data, not the schema or statistics")
    parser.add_argument(
        "--exclude-table-data", help="Comma-separated list of tables to skip data dump (schema is still copied)"
    )
    parser.add_argument("--reset-db", "-r", action="store_true", help="Reset database")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Print copy commands without executing them")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)
    args = parser.parse_args()

    if args.source == args.target:
        print(f"{RED}✖ Error: source and target database cannot be the same{RESET}")
        sys.exit(1)

    if args.dry_run:
        print(f"{YELLOW}=== DRY RUN MODE ==={RESET}\n")

    tables = args.tables.split(",") if args.tables else []
    exclude_table_data = args.exclude_table_data.split(",") if args.exclude_table_data else []

    try:
        copy_database(args.source, args.target, tables, exclude_table_data, args)
    except Exception as e:
        print(f"{RED}✖ Error: {e}{RESET}")
        sys.exit(1)
