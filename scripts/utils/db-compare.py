#!/usr/bin/env python3
"""
Compare two Postgres databases using services defined in .pg_service.conf.

- List tables unique to each database (if any).
- Compare size of common tables across datasets.
- If row counts differ, stop and report; otherwise, continue.
- List columns unique to each table (if any).
- If columns match, print differing rows from the last 10 000 rows (by default).

Usage:
    ./scripts/db-compare.py local bca
    ./scripts/db-compare.py local bca --rows 1_000_000
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
    """
    Get table size based on relation_size.

    Indexes are ignored: their size may differ because of internal overhead.
    """

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


def check_row_diff(rows1, rows2, max_rows=10):
    """Get difference between 10 (by default) rows."""

    diffs = []
    for r1, r2 in zip(rows1, rows2):
        if any(r1[k] != r2[k] for k in r1):
            diffs.append((r1, r2))
            if len(diffs) >= max_rows:
                break

    return diffs


def print_exclusive_db_items(db, items, label, indent=1, symbol="✖ "):
    """Print items exclusive to a single database."""

    indent_str = ' ' * 4 * indent
    indent_str_2 = ' ' * 4 * (indent + 1)

    any_diff = False
    if len(items) > 0:
        label += "s" if len(items) != 1 else ""
        print(f"{indent_str}{YELLOW}{symbol}{len(items)} {label} only in {db}:{RESET}")
        for each in items:
            print(f"{indent_str_2}{each}")
        any_diff = True
    return any_diff


def print_table_list_diff(db1, db2, tables1, tables2):
    """Print list of common and different tables between two databases."""

    common_tables = tables1 & tables2
    table1_tables = tables1 - tables2
    table2_tables = tables2 - tables1

    print(f"    {GREEN}✔ {len(common_tables)} common tables{RESET}")

    print_exclusive_db_items(db1, table1_tables, "table")
    print_exclusive_db_items(db2, table2_tables, "table")
    return common_tables


def print_column_diff(db1, db2, rows1, rows2):
    """Print list of different columns between two tables."""

    columns1 = set(rows1[0].keys())
    columns2 = set(rows2[0].keys())

    table1_cols = columns1 - columns2
    table2_cols = columns2 - columns1

    are_cols_diff = (
        print_exclusive_db_items(db1, table1_cols, "column", indent=2, symbol="") or
        print_exclusive_db_items(db2, table2_cols, "column", indent=2, symbol="")
    )

    return are_cols_diff


def print_table_size_diff(db1, db2, conn1, conn2, table, check_nrows=10_000):
    """
    Print size difference (and example of differing rows across the last 10k rows, by
    default) between a table compared across two databases.
    """

    size1 = get_table_size(conn1, table)
    size2 = get_table_size(conn2, table)

    if size1 != size2:
        print(f"    {RED}✖ {table} size mismatch:{RESET} {size1} vs {size2} bytes")
    else:
        print(f"    {GREEN}✔ {table} size: {size1} bytes{RESET}")

    rows1 = get_last_rows(conn1, table, check_nrows)
    rows2 = get_last_rows(conn2, table, check_nrows)

    if len(rows1) != len(rows2):
        # Print if different row count in tables
        if len(rows2) == check_nrows:
            msg = f"{len(rows2)}+"
        else:
            msg = len(rows2)
        print(f"        {YELLOW}Different row count: {len(rows1)} vs {msg} rows{RESET}")
        return
    elif len(rows1) == 0:
        # Skip if both datasets are empty
        return

    # Print column differences
    any_diff_col = print_column_diff(db1, db2, rows1, rows2)

    # Print row differences
    if not any_diff_col:
        diffs = check_row_diff(rows1, rows2, max_rows=1)

        row_number = f"The last {len(rows1)}" if len(rows1) == check_nrows else f"All {len(rows1)}"

        if diffs:
            print(f"        {CYAN}Differences in {row_number.lower()} rows -- example:{RESET}")
            for r1, r2 in diffs:
                print(f"        {YELLOW}{db1}:{RESET} {r1}\n        {YELLOW}{db2}:{RESET} {r2}\n")
        elif size1 != size2:
            print(f"        {CYAN}{row_number} rows are identical{RESET}")


def compare_databases(db1, db2, nrows=10_000):
    """Compare two databases."""

    conn1 = get_connection(db1)
    conn2 = get_connection(db2)

    tables1 = get_tables(conn1)
    tables2 = get_tables(conn2)

    print(f"{CYAN}🔍 Comparing list of tables...{RESET}\n")
    common_tables = print_table_list_diff(db1, db2, tables1, tables2)

    print(f"\n{CYAN}📦 Comparing relation size of {len(common_tables)} common tables (ignoring indexes)...{RESET}\n")
    for table in common_tables:
        print_table_size_diff(db1, db2, conn1, conn2, table, check_nrows=nrows)

    conn1.close()
    conn2.close()


def parse_args():
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=f"{CYAN}Compare two PostgreSQL databases.{RESET}",
        epilog=f"{YELLOW}Example usage:{RESET}\n  {sys.argv[0]} local ssh-bca-staging --rows 100",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", help="Source database service name")
    parser.add_argument("target", help="Target database service name")
    parser.add_argument(
        "--rows",
        type=int,
        default=10_000,
        help="Number of last rows to compare upon table size mismatch (default: 10000)",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = parse_args()
        compare_databases(args.source, args.target, nrows=args.rows)
    except Exception as e:
        print(f"{RED}✖ Error: {e}{RESET}")
        sys.exit(1)
