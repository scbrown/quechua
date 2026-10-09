# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Offline, opt-in class-indexed valid-time projection; never writes a store."""

import argparse
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NANO = 1_000_000_000
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
STAMP = re.compile(
    r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$"
)


def instant(value: str, date_zone: str | None = None) -> int:
    """Exact nanoseconds since epoch. Floating times and excess precision refuse."""
    if not isinstance(value, str):
        raise TypeError("timestamp must be a string")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        if date_zone is None:
            raise ValueError("date-only timestamp requires explicit date_zone")
        day = date.fromisoformat(value)
        dt = datetime.combine(day, datetime.min.time(), ZoneInfo(date_zone))
        if dt.utcoffset() != dt.replace(fold=1).utcoffset():
            raise ValueError("date midnight is ambiguous in date_zone")
        if dt.astimezone(UTC).astimezone(dt.tzinfo) != dt:
            raise ValueError("date midnight does not exist in date_zone")
        fraction = 0
    else:
        match = STAMP.fullmatch(value)
        if not match:
            raise ValueError(
                "expected RFC3339 timestamp with zone and at most 9 fractional digits"
            )
        day, clock, digits, offset = match.groups()
        if offset != "Z" and (int(offset[1:3]) > 23 or int(offset[4:6]) > 59):
            raise ValueError("invalid timestamp offset")
        if offset == "-00:00":
            raise ValueError("unknown offset -00:00 is not a known instant")
        dt = datetime.fromisoformat(f"{day}T{clock}{offset.replace('Z', '+00:00')}")
        fraction = int((digits or "").ljust(9, "0"))
    delta = dt.astimezone(UTC) - EPOCH
    return (delta.days * 86400 + delta.seconds) * NANO + fraction


def stamp(ns: int) -> str:
    seconds, fraction = divmod(ns, NANO)
    dt = EPOCH + timedelta(seconds=seconds)
    text = dt.isoformat(timespec="seconds").removesuffix("+00:00")
    suffix = f".{fraction:09d}".rstrip("0") if fraction else ""
    return f"{text}{suffix}Z"


def project(
    declaration: dict, profile: str, record: dict, date_zone: str | None = None
) -> dict:
    """Record: asserted full-IRI types + full-IRI properties, each a list of strings."""
    if not isinstance(declaration, dict) or not isinstance(record, dict):
        raise TypeError("declaration and record must be objects")
    if declaration.get("version") != 1 or declaration.get("interval") != "closed-open":
        raise ValueError("unsupported valid-time declaration")
    profiles = declaration.get("profiles")
    if not isinstance(profiles, dict) or not isinstance(profiles.get(profile), dict):
        raise TypeError("selected profile must be an object")
    rules = profiles[profile]
    if not all(
        isinstance(kind, str) and isinstance(rule, dict) for kind, rule in rules.items()
    ):
        raise ValueError("class mappings must be objects keyed by class IRI")
    types = record.get("types")
    properties = record.get("properties")
    if not isinstance(properties, dict):
        raise TypeError("properties must be an object")
    if not all(
        isinstance(key, str)
        and isinstance(values, list)
        and all(isinstance(value, str) for value in values)
        for key, values in properties.items()
    ):
        raise ValueError(
            "properties must map predicate IRIs to lists of timestamp strings"
        )
    if not isinstance(types, list) or not all(isinstance(t, str) for t in types):
        raise ValueError("types must be a list of asserted full IRIs")
    matches = [rules[t] for t in set(types) if t in rules]
    if not matches:
        raise ValueError("no declared class in this profile")
    if any(rule != matches[0] for rule in matches[1:]):
        raise ValueError("conflicting class mappings; choose an unambiguous profile")
    rule = matches[0]
    if not isinstance(rule.get("start"), str) or (
        "end" in rule and not isinstance(rule["end"], str)
    ):
        raise ValueError("boundary predicates must be strings")
    point = "epsilon_ns" in rule
    if set(rule) != ({"start", "epsilon_ns"} if point else {"start", "end"}):
        raise ValueError("invalid rule fields")

    def read(predicate: str, required: bool) -> int | None:
        values = properties.get(predicate, [])
        if not isinstance(values, list) or len(values) > 1 or (required and not values):
            raise ValueError(
                f"expected {'one' if required else 'zero or one'} value for {predicate}"
            )
        return instant(values[0], date_zone) if values else None

    start = read(rule["start"], True)
    assert start is not None
    if point:
        epsilon = rule["epsilon_ns"]
        if type(epsilon) is not int or epsilon <= 0:
            raise ValueError("epsilon_ns must be a positive integer")
        end = start + epsilon
    else:
        end = read(rule["end"], False)
    if end is not None and end <= start:
        raise ValueError(
            "end must be strictly after start for a nonempty half-open interval"
        )
    return {
        "valid_from": stamp(start),
        "valid_to": stamp(end) if end is not None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument(
        "--profile", required=True, choices=("tracker", "activity", "calendar", "point")
    )
    parser.add_argument(
        "--declaration",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "profiles/valid-time.json",
    )
    parser.add_argument(
        "--date-zone", help="explicit IANA zone for date-only boundaries"
    )
    args = parser.parse_args()
    try:
        output = project(
            json.loads(args.declaration.read_text()),
            args.profile,
            json.loads(args.record.read_text()),
            args.date_zone,
        )
    except (
        ValueError,
        KeyError,
        TypeError,
        OverflowError,
        OSError,
        UnicodeError,
    ) as exc:
        parser.exit(2, f"valid-time projection refused: {exc}\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
