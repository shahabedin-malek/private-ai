"""Detect control-plane drift between documented parser totals and the live corpus database.

Two independent checks, both reported as issues (exit status 1 when any issue is found):

1. **Internal sum** — a line that presents a cumulative `stdlib-text-v3` breakdown (at least five
   of the six core statuses with counts, plus a total keyword such as `rows`/`total`/`counts`)
   must have counts that sum to a total stated on the same line.
2. **Live database** — the corpus only grows, so the largest documented parser total is treated as
   the live claim. It must equal the live `parsed_content` row count for the parser version, and
   the per-status counts of every line carrying that total must equal the live database counts.
   Historical snapshots (smaller totals) are ignored, matching the project's provenance convention.

Run standalone:  python3 scripts/progress_consistency.py --project .
Exit status is 1 on any issue, so this can gate a test run or a commit. The database is opened
read-only; `--no-database` skips check 2, and a missing database is skipped with a note.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

PARSER_VERSION = "stdlib-text-v3"
DEFAULT_DB = Path("data/database/private_ai_corpus.sqlite")
# The documented cumulative breakdown uses exactly these six statuses. `FAILED` and
# `SOURCE_MISMATCH` are deliberately excluded: `FAILED` also appears in nearby extraction-job
# parentheticals, which would otherwise be mis-grouped into the parser breakdown.
PARSER_STATUSES = (
    "PARSED",
    "SENSITIVE",
    "UNSUPPORTED_TYPE",
    "BINARY",
    "UNSUPPORTED_ENCODING",
    "TOO_LARGE",
)
STATUS_ALT = "|".join(PARSER_STATUSES)
STATUS_PAIR = re.compile(rf"(?P<value>\d[\d,]*)\s+(?P<status>{STATUS_ALT})\b")
NUMBER = re.compile(r"\d[\d,]*")
TOTAL_KEYWORD = re.compile(r"\b(rows?|total|counts?|records?)\b", re.IGNORECASE)
# A line needs this many distinct statuses to be treated as a cumulative breakdown.
MIN_DISTINCT_STATUSES = 5
# Adjacent status pairs further apart than this belong to separate breakdown groups.
GROUP_GAP = 60


def _clean(line: str) -> str:
    """Strip Markdown emphasis/backticks so number/status pairing survives formatting."""
    return line.replace("**", "").replace("`", "")


def _to_int(token: str) -> int:
    return int(token.replace(",", ""))


def iter_breakdowns(text: str, *, source: str = "<text>") -> list[dict[str, object]]:
    """Return every cumulative parser breakdown record found in the text."""
    records: list[dict[str, object]] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = _clean(raw_line)
        pairs = list(STATUS_PAIR.finditer(line))
        if len(pairs) < MIN_DISTINCT_STATUSES or not TOTAL_KEYWORD.search(line):
            continue
        groups: list[list[re.Match[str]]] = []
        current: list[re.Match[str]] = []
        for match in pairs:
            if current and match.start() - current[-1].end() > GROUP_GAP:
                groups.append(current)
                current = []
            current.append(match)
        if current:
            groups.append(current)
        for group in groups:
            if len({match.group("status") for match in group}) < MIN_DISTINCT_STATUSES:
                continue
            counts = {match.group("status"): _to_int(match.group("value")) for match in group}
            records.append({
                "source": source,
                "line": lineno,
                "computed_total": sum(counts.values()),
                "status_counts": counts,
                "numbers_on_line": sorted({_to_int(token) for token in NUMBER.findall(line)}),
                "line_text": raw_line.strip(),
            })
    return records


def find_breakdown_issues(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Check 1: breakdown counts must sum to a total stated on the same line."""
    issues: list[dict[str, object]] = []
    for record in records:
        computed = int(record["computed_total"])
        if computed in set(record["numbers_on_line"]):
            continue
        issues.append({
            **record,
            "kind": "breakdown-sum",
            "detail": (f"status breakdown sums to {computed:,} but that total does not appear "
                       f"on the line"),
        })
    return issues


def load_database_counts(db_path: Path, parser_version: str) -> dict[str, object] | None:
    """Read the live per-status parser counts read-only, or None when the database is absent."""
    if not db_path.is_file():
        return None
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT status, count(*) FROM parsed_content WHERE parser_version=? GROUP BY status",
            (parser_version,)).fetchall()
    finally:
        con.close()
    statuses = {str(status): int(count) for status, count in rows}
    return {"total": sum(statuses.values()), "statuses": statuses, "path": str(db_path)}


def find_database_issues(records: list[dict[str, object]], database: dict[str, object] | None,
                         parser_version: str) -> list[dict[str, object]]:
    """Check 2: the freshest documented total and its per-status counts must match the live DB."""
    if database is None or not records:
        return []
    live_total = max(int(record["computed_total"]) for record in records)
    database_total = int(database["total"])
    if live_total != database_total:
        return [{
            "kind": "database-total",
            "documented_total": live_total,
            "database_total": database_total,
            "parser_version": parser_version,
            "detail": (f"freshest documented parser total {live_total:,} does not match the live "
                       f"database total {database_total:,} for {parser_version}"),
        }]
    database_statuses = database["statuses"]
    issues: list[dict[str, object]] = []
    for record in records:
        if int(record["computed_total"]) != live_total:
            continue
        documented = record["status_counts"]
        for status in PARSER_STATUSES:
            if status not in documented:
                continue
            expected = int(database_statuses.get(status, 0))
            if int(documented[status]) != expected:
                issues.append({
                    "kind": "database-status",
                    "source": record["source"],
                    "line": record["line"],
                    "parser_version": parser_version,
                    "status": status,
                    "documented": int(documented[status]),
                    "database": expected,
                    "detail": (f"{status} documented as {int(documented[status]):,} but the live "
                               f"database has {expected:,}"),
                })
    return issues


def scan(paths: list[Path], *, database: dict[str, object] | None = None,
         parser_version: str = PARSER_VERSION) -> dict[str, object]:
    """Run both checks over the given Markdown files and aggregate the issues."""
    checked: list[str] = []
    records: list[dict[str, object]] = []
    for path in paths:
        if not path.is_file():
            continue
        checked.append(str(path))
        records.extend(iter_breakdowns(
            path.read_text(encoding="utf-8", errors="replace"), source=str(path)))
    issues = find_breakdown_issues(records)
    issues.extend(find_database_issues(records, database, parser_version))
    report: dict[str, object] = {
        "checked": checked,
        "file_count": len(checked),
        "breakdown_count": len(records),
        "issues": issues,
        "issue_count": len(issues),
    }
    if database is not None:
        report["database"] = database
    return report


def default_paths(project: Path) -> list[Path]:
    """Control-plane Markdown files, which hold the documented parser totals."""
    progress = project / ".progress"
    return sorted(progress.glob("*.md")) if progress.is_dir() else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path,
                        help="Markdown files to check (default: <project>/.progress/*.md)")
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--db", type=Path, default=None,
                        help=f"corpus database for the live comparison (default: {DEFAULT_DB})")
    parser.add_argument("--parser-version", default=PARSER_VERSION)
    parser.add_argument("--no-database", action="store_true",
                        help="skip the live database comparison")
    args = parser.parse_args()
    paths = args.paths or default_paths(args.project)
    database = None
    if not args.no_database:
        db_path = args.db if args.db is not None else args.project / DEFAULT_DB
        database = load_database_counts(db_path, args.parser_version)
    report = scan(paths, database=database, parser_version=args.parser_version)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
