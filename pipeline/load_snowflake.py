"""
Load the corpus into Snowflake and run the analysis there.

Loads via internal stage + COPY INTO rather than row-by-row inserts: 100k rows
of INSERT would take minutes and is the wrong shape for a warehouse.

Then it runs every view in queries.sql and writes the results back to
data/snowflake_results.json, which is what the writeup quotes. The point is that
the numbers on the site are Snowflake's answers, not Python's, and the two are
cross-checked against each other by verify.py.

Usage:  python pipeline/load_snowflake.py
Needs:  .env with SNOWFLAKE_ACCOUNT / USER / PASSWORD (and optionally ROLE,
        WAREHOUSE). Nothing is printed that would leak the password.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

DB = "STILL_HERE"
SCHEMA = "SHELTER"
WH = "STILL_HERE_WH"


def load_env():
    env = {}
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k, v in env.items():
        os.environ.setdefault(k, v)
    return env


def connect():
    import snowflake.connector

    acct = os.environ.get("SNOWFLAKE_ACCOUNT", "").strip()
    user = os.environ.get("SNOWFLAKE_USER", "").strip()
    pwd = os.environ.get("SNOWFLAKE_PASSWORD", "").strip()
    if not (acct and user and pwd):
        sys.exit("Missing SNOWFLAKE_ACCOUNT / USER / PASSWORD in .env")

    kw = dict(account=acct, user=user, password=pwd, client_session_keep_alive=True)
    role = os.environ.get("SNOWFLAKE_ROLE", "").strip()
    if role:
        kw["role"] = role
    print(f"connecting to {acct} as {user}…")
    return snowflake.connector.connect(**kw)


def put_path(p):
    """PUT needs a forward-slash file: URI even on Windows."""
    return "file://" + os.path.abspath(p).replace("\\", "/")


def main():
    load_env()
    cx = connect()
    cs = cx.cursor()

    def run(sql, quiet=False):
        if not quiet:
            first = " ".join(sql.split())[:78]
            print(f"  {first}")
        return cs.execute(sql)

    wh = os.environ.get("SNOWFLAKE_WAREHOUSE", "").strip() or WH
    print("\n-- warehouse / database --")
    # XSMALL, auto-suspend fast: this is 100k rows, not a production workload.
    run(f"CREATE WAREHOUSE IF NOT EXISTS {wh} WITH WAREHOUSE_SIZE='XSMALL' "
        f"AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=FALSE")
    run(f"USE WAREHOUSE {wh}")
    run(f"CREATE DATABASE IF NOT EXISTS {DB}")
    run(f"USE DATABASE {DB}")
    run(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    run(f"USE SCHEMA {SCHEMA}")

    print("\n-- tables --")
    run("""CREATE OR REPLACE TABLE DOG_STAYS (
      ERA STRING, ANIMAL_ID STRING, NAME STRING, BREED STRING, COLOR STRING,
      INTAKE_DATE DATE, OUTCOME_DATE DATE, DAYS_IN_SHELTER NUMBER,
      OUTCOME_STATUS STRING, ADOPTED NUMBER, INTAKE_TYPE STRING,
      INTAKE_CONDITION STRING)""")
    run("""CREATE OR REPLACE TABLE DOGS_WAITING (
      ANIMAL_ID STRING, NAME STRING, BREED STRING, RAW_BREED STRING,
      COLOR STRING, SECONDARY_COLOR STRING, SEX STRING, IS_PUPPY NUMBER,
      INTAKE_DATE DATE, DAYS_WAITING NUMBER, INTAKE_REASON STRING,
      HEALTH STRING, DATE_OF_BIRTH STRING)""")

    print("\n-- stage + load --")
    run("CREATE OR REPLACE STAGE STILL_HERE_STAGE "
        "FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='\"' "
        "EMPTY_FIELD_AS_NULL=TRUE NULL_IF=('','NULL'))")
    for csv_name, table in [("outcomes.csv", "DOG_STAYS"), ("waiting.csv", "DOGS_WAITING")]:
        src = os.path.join(DATA, csv_name)
        run(f"PUT {put_path(src)} @STILL_HERE_STAGE OVERWRITE=TRUE AUTO_COMPRESS=TRUE")
        run(f"COPY INTO {table} FROM @STILL_HERE_STAGE/{csv_name}.gz "
            f"ON_ERROR='ABORT_STATEMENT'")
        n = cs.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"    {table}: {n:,} rows")

    print("\n-- views --")
    sql_path = os.path.join(ROOT, "pipeline", "queries.sql")
    body = open(sql_path, encoding="utf-8").read()
    # Everything from the IS_BULLY definition onward; the DDL above already ran.
    body = body[body.index("CREATE OR REPLACE FUNCTION IS_BULLY"):]

    # Split on semicolons that are outside a $$ ... $$ function body, then strip
    # the leading comment block and blank lines off each statement. Without that
    # strip a statement begins with "-- 2. The headline..." and any test for
    # CREATE silently skips it, which is how six of eight views went missing.
    stmts, buf, in_dollar = [], [], False
    for line in body.splitlines():
        if line.count("$$") % 2 == 1:
            in_dollar = not in_dollar
        buf.append(line)
        if line.rstrip().endswith(";") and not in_dollar:
            stmts.append("\n".join(buf))
            buf = []
    if buf:
        stmts.append("\n".join(buf))

    def strip_lead(s):
        lines = s.splitlines()
        while lines and (not lines[0].strip() or lines[0].lstrip().startswith("--")):
            lines.pop(0)
        return "\n".join(lines).strip()

    wanted = [strip_lead(s) for s in stmts]
    wanted = [s for s in wanted if s.upper().startswith("CREATE")]

    # ADOPTIONS changed from a view to a table between runs, and Snowflake
    # refuses to CREATE OR REPLACE across object kinds. Drop both spellings of
    # anything we are about to recreate so a re-run is always clean.
    for s in wanted:
        parts = s.split()
        kind = parts[3].upper() if parts[1].upper() == "OR" else parts[1].upper()
        name = parts[4] if parts[1].upper() == "OR" else parts[2]
        name = name.split("(")[0]
        if kind in ("TABLE", "VIEW"):
            for other in ("VIEW", "TABLE"):
                try:
                    run(f"DROP {other} IF EXISTS {name}", quiet=True)
                except Exception:
                    pass

    created = 0
    for s in wanted:
        run(s.rstrip(";"), quiet=True)
        print(f"    {' '.join(s.split()[:5])}")
        created += 1
    if created != len(wanted) or created < 8:
        sys.exit(f"only {created} of {len(wanted)} objects created. Aborting before results.")
    print(f"    {created} functions/views created")

    print("\n-- results --")
    out = {}
    def grab(name, sql):
        cur = cs.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        out[name] = rows
        return rows

    for r in grab("headline", "SELECT * FROM HEADLINE"):
        print(f"    {r['GROUP_NAME']:<15} n={r['N']:>6,}  median {r['MEDIAN_DAYS']}d  mean {r['MEAN_DAYS']}d")
    grab("by_color", "SELECT * FROM BY_COLOR")
    grab("by_color_controlled", "SELECT * FROM BY_COLOR_CONTROLLED")
    for r in grab("spread", "SELECT * FROM SPREAD"):
        print(f"    color within bully {r['COLOR_SPREAD_WITHIN_BULLY']}d, "
              f"within other {r['COLOR_SPREAD_WITHIN_OTHER']}d, "
              f"gap between groups {r['WORST_CASE_GAP_BETWEEN_GROUPS']}d")
    grab("by_breed", "SELECT * FROM BY_BREED")
    # A view's ORDER BY is not guaranteed to survive into an outer query in
    # Snowflake, so the ordering has to be restated here or this returns an
    # arbitrary 25 dogs rather than the longest-waiting ones.
    top = grab("waiting_ranked",
               "SELECT * FROM WAITING_RANKED ORDER BY DAYS_WAITING DESC LIMIT 25")
    if top:
        t = top[0]
        print(f"    longest waiting: {t['NAME']} {t['DAYS_WAITING']}d, "
              f"{t['PCT_OF_COHORT_HOME_BY_NOW']}% of cohort home by now")
    grab("waiting_groups", """
      SELECT IFF(BULLY,'Bully-type','Everyone else') AS GROUP_NAME,
             COUNT(*) AS DOGS_WAITING, MEDIAN(DAYS_WAITING) AS MEDIAN_DAYS_SO_FAR,
             COUNT_IF(DAYS_WAITING>=365) AS OVER_A_YEAR
      FROM WAITING_RANKED GROUP BY BULLY""")

    dest = os.path.join(DATA, "snowflake_results.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nwrote {dest}")
    cs.close(); cx.close()


if __name__ == "__main__":
    main()
