# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rdflib==7.1.4",
# ]
# ///
"""Pin the public vocabularies the trim maps onto, as offline term lists.

The trim (trim/*.tsv) replaces or aligns Quechua terms with terms from W3C
Recommendations, schema.org and a few other public vocabularies. A replacement
that names a term the target vocabulary does not define is a broken promise, so
the validator checks every target offline against `vocab/<name>.terms`.

Those lists are derived, not copied: this script downloads each source, checks
its sha256 against `vocab/SOURCES.tsv`, and writes the sorted IRIs it defines
under its namespace. Nothing third-party is redistributed.

    uv run --script scripts/pin_vocab.py --check     # sources still match the pins
    uv run --script scripts/pin_vocab.py --update    # re-pin after a deliberate upgrade
"""

import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parent.parent
VOCAB = ROOT / "vocab"
FIELDS = ("name", "prefix", "namespace", "url", "accept", "format", "sha256")


def sources() -> list[dict]:
    with (VOCAB / "SOURCES.tsv").open() as handle:
        rows = csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t")
        return [dict(row) for row in rows]


def fetch(row: dict) -> bytes:
    # curl, not urllib: on the host this was pinned from, urllib stalled on
    # chunked reads from w3.org that curl completed in under a second.
    result = subprocess.run(
        ["curl", "-sfL", "--retry", "2", "-m", "180", "-H", f"Accept: {row['accept']}", row["url"]],
        check=True, capture_output=True,
    )
    return result.stdout


def terms(data: bytes, row: dict) -> list[str]:
    graph = Graph().parse(data=data, format=row["format"])
    namespace = row["namespace"]
    return sorted(
        {str(s) for s in graph.subjects() if isinstance(s, URIRef) and str(s).startswith(namespace)}
        - {namespace}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="refuse if any source no longer matches its pin")
    mode.add_argument("--update", action="store_true", help="re-pin every source and rewrite the term lists")
    args = parser.parse_args()
    rows = sources()
    drift = []
    for row in rows:
        data = fetch(row)
        digest = hashlib.sha256(data).hexdigest()
        if args.check:
            if digest != row["sha256"]:
                drift.append(f"{row['name']}: pinned {row['sha256'][:12]}, served {digest[:12]}")
            continue
        row["sha256"] = digest
        found = terms(data, row)
        (VOCAB / f"{row['name']}.terms").write_text("\n".join(found) + "\n")
        print(f"{row['name']}: {len(found)} terms, sha256 {digest[:12]}")
    if args.update:
        with (VOCAB / "SOURCES.tsv").open("w", newline="") as handle:
            handle.write("# Pinned sources for vocab/*.terms. Regenerate with scripts/pin_vocab.py --update.\n")
            writer = csv.DictWriter(handle, FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    if drift:
        print("Sources moved since they were pinned (re-pin deliberately with --update):", *drift, sep="\n  ")
        return 1
    if args.check:
        print(f"{len(rows)} pinned sources match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
