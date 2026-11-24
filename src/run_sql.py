"""Run sql/*.sql in order with DuckDB and export the results to data/processed/.

Views created first: every data/sim/<name>.parquet becomes a view <name> (SIMULATED), and
data/public/uci_invoices.parquet becomes uci_invoices (PUBLIC DATA). A statement preceded by a line
'-- output: <name>' is exported to data/processed/<name>.csv.

    python src/run_sql.py            (all files)
    python src/run_sql.py 05 07      (only files whose name starts with these prefixes)
"""
import re
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM, PUB, OUT, SQL = ROOT / "data" / "sim", ROOT / "data" / "public", ROOT / "data" / "processed", ROOT / "sql"
DB = ROOT / "data" / "sim" / "retention.duckdb"


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB))
    for f in sorted(SIM.glob("*.parquet")):
        con.execute(f"CREATE OR REPLACE VIEW {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    con.execute(f"CREATE OR REPLACE VIEW uci_invoices AS SELECT * FROM read_parquet('{(PUB / 'uci_invoices.parquet').as_posix()}')")
    return con


def run_file(con, sql_file: Path) -> None:
    t0 = time.time()
    for statement in re.split(r";\s*$", sql_file.read_text(encoding="utf-8"), flags=re.MULTILINE):
        if not re.search(r"^\s*[A-Za-z(]", statement, flags=re.MULTILINE):
            continue
        match = re.search(r"--\s*output:\s*(\w+)", statement)
        if match:
            df = con.execute(statement).df()
            for c in df.select_dtypes("float").columns:
                df[c] = df[c].map(lambda v: float(f"{v:.8g}") if pd.notna(v) else v)
            df.to_csv(OUT / f"{match.group(1)}.csv", index=False)
            print(f"  {sql_file.name:32s} -> {match.group(1)}.csv ({len(df):,} rows)")
        else:
            con.execute(statement)
    print(f"{sql_file.name} done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    con = connect()
    prefixes = tuple(sys.argv[1:])
    for f in sorted(SQL.glob("*.sql")):
        if prefixes and not f.name.startswith(prefixes):
            continue
        run_file(con, f)
