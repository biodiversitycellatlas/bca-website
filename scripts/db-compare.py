#!/usr/bin/env python3
"""
Compare two Postgres databases using services defined in .pg_service.conf.

1. Check list of table names and report differences.
2. Compare size of intersecting tables and report differing rows (if any) based on the
last 10 000 rows (by default).

Usage:
    ./scripts/db-compare.py local bca
"""

import argparse
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def get_connection(service_name):
    """Get Postgres database connection."""
    return psycopg2.connect(f"service={service_name}")


def get_tables(conn):
    """Get list of tables."""

    with conn.cursor() as cur:
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public';
        """)
        return {row[0] for row in cur.fetchall()}


def get_table_size(conn, table):
    """Get table size."""

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_total_relation_size(%s);
        """,
            (f"public.{table}",),
        )
        return cur.fetchone()[0]


def get_last_rows(conn, table, nrows=10_000):
    """Get values from last 10_000 (by default) rows."""

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT *
            FROM "{table}"
            ORDER BY 1 DESC
            LIMIT {nrows};
        """)
        return cur.fetchall()


def check_row_differences(rows1, rows2, max_rows=10):
    """Get difference between 10 (by default) rows."""

    diffs = []
    for r1, r2 in zip(rows1, rows2):
        if any(r1[k] != r2[k] for k in r1):
            diffs.append((r1, r2))
            if len(diffs) >= max_rows:
                break

    return diffs


def get_indexes(conn, table):
    """Get list of indexes for a table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = %s;
        """,
            (table,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def get_constraints(conn, table):
    """Get list of constraints for a table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT conname, contype, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = %s::regclass;
        """,
            (f"public.{table}",),
        )
        return {row[0]: row[2] for row in cur.fetchall()}


def print_table_list_diff(db1, db2, tables1, tables2):
    """Print list of common and different tables between two databases."""

    common_tables = tables1 & tables2
    table1_tables = tables1 - tables2
    table2_tables = tables2 - tables1

    print(f"    {GREEN}✔ {len(common_tables)} common tables{RESET}")

    if len(table1_tables) > 0:
        print(f"    {YELLOW}✖ {len(table1_tables)} tables only in {db1}:{RESET}")
        for table in table1_tables:
            print(f"        {table}")

    if len(table2_tables) > 0:
        print(f"    {YELLOW}✖ {len(table2_tables)} tables only in {db2}:{RESET}")
        for table in table2_tables:
            print(f"        {table}")
    return common_tables


def print_table_size_diff(db1, db2, conn1, conn2, table, check_nrows=10_000):
    """
    Print size difference (and example of differing rows across the last 10k rows, by
    default) between a table compared across two databases.
    """

    size1 = get_table_size(conn1, table)
    size2 = get_table_size(conn2, table)

    if size1 != size2:
        print(f"    {RED}✖ Size mismatch in '{table}':{RESET} {size1} vs {size2} bytes")
    else:
        print(f"    {GREEN}✔ '{table}' OK (size: {size1} bytes){RESET}")

    rows1 = get_last_rows(conn1, table, check_nrows)
    rows2 = get_last_rows(conn2, table, check_nrows)

    diffs = check_row_differences(rows1, rows2, max_rows=1)
    if diffs:
        print(f"        {CYAN}Differences in the last {check_nrows} rows -- example:{RESET}")
        for r1, r2 in diffs:
            print(f"        {YELLOW}{db1}:{RESET} {r1}\n        {YELLOW}{db2}:{RESET} {r2}\n")
    elif size1 != size2:
        print(f"        {CYAN}Last {check_nrows} rows are identical{RESET}")


def compare_databases(db1, db2, nrows=10_000):
    """Compare two databases."""

    conn1 = get_connection(db1)
    conn2 = get_connection(db2)

    tables1 = get_tables(conn1)
    tables2 = get_tables(conn2)

    print(f"{CYAN}🔍 Comparing list of tables...{RESET}\n")
    common_tables = print_table_list_diff(db1, db2, tables1, tables2)

    print(f"\n{CYAN}📦 Comparing size of {len(common_tables)} common tables...{RESET}\n")
    for table in common_tables:
        print_table_size_diff(db1, db2, conn1, conn2, table, check_nrows=nrows)

    conn1.close()
    conn2.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"{CYAN}Compare two PostgreSQL databases.{RESET}",
        epilog=f"{YELLOW}Example usage:{RESET}\n  {sys.argv[0]} local ssh-bca-staging --rows 100",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("db1", help="First database service name")
    parser.add_argument("db2", help="Second database service name")
    parser.add_argument(
        "--rows",
        type=int,
        default=10_000,
        help="Number of last rows to compare upon table size mismatch (default: 10000)",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    args = parser.parse_args()

    compare_databases(args.db1, args.db2, nrows=args.rows)
