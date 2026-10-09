"""Contract controls for declarative valid time; no store or network access."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from project_valid_time import instant, project, stamp

S = "https://schema.org/"
I = "http://www.w3.org/2002/12/cal/ical#"
O = "http://www.w3.org/ns/sosa/"
P = json.loads((ROOT / "profiles/valid-time.json").read_text())
T = "2026-10-07T02:55:21.233261492Z"


def record(kind=S + "Action", start=S + "dateCreated", value=T, end=None):
    props = {start: [value]}
    if end is not None:
        props[S + "endTime"] = [end]
    return {"types": [kind], "properties": props}


class ValidTime(unittest.TestCase):
    def test_cli_invalid_containers_exit_two_without_output(self):
        cases = [
            [],
            None,
            {"types": [S + "Action"], "properties": []},
            {"types": [S + "Action"], "properties": None},
            {"types": "Action", "properties": {}},
            {"types": [S + "Action"], "properties": {S + "dateCreated": [{}]}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            for value in cases:
                path.write_text(json.dumps(value))
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts/project_valid_time.py"),
                        "--profile",
                        "tracker",
                        str(path),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                with self.subTest(value=value):
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("projection refused:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_invalid_declaration_containers_refuse(self):
        for value in (
            [],
            None,
            {"version": 1, "interval": "closed-open", "profiles": []},
            {"version": 1, "interval": "closed-open", "profiles": {"tracker": []}},
            {
                "version": 1,
                "interval": "closed-open",
                "profiles": {"tracker": {S + "Action": None}},
            },
        ):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                project(value, "tracker", record())

    def test_open_tracker_preserves_nanos(self):
        self.assertEqual(
            project(P, "tracker", record()), {"valid_from": T, "valid_to": None}
        )

    def test_closed_tracker(self):
        r = record(value="2026-10-09T20:30:51Z", end="2026-10-09T20:30:57Z")
        self.assertEqual(project(P, "tracker", r)["valid_to"], "2026-10-09T20:30:57Z")

    def test_activity_uses_start_not_creation(self):
        r = record(start=S + "startTime")
        self.assertEqual(project(P, "activity", r)["valid_from"], T)
        with self.assertRaises(ValueError):
            project(P, "tracker", r)

    def test_modified_is_not_valid_start(self):
        with self.assertRaises(ValueError):
            project(P, "tracker", record(start=S + "dateModified"))

    def test_offset_same_instant(self):
        self.assertEqual(instant(T), instant("2026-10-06T22:55:21.233261492-04:00"))

    def test_point_crosses_second_with_exact_epsilon(self):
        r = record(
            O + "Observation", O + "resultTime", "2026-10-09T23:59:59.999999999Z"
        )
        self.assertEqual(project(P, "point", r)["valid_to"], "2026-10-10T00:00:00Z")

    def test_calendar_date_requires_zone(self):
        r = record(I + "Vevent", I + "dtstart", "2026-03-08")
        r["properties"][I + "dtend"] = ["2026-03-09"]
        with self.assertRaises(ValueError):
            project(P, "calendar", r)
        result = project(P, "calendar", r, "America/New_York")
        self.assertEqual(
            result,
            {"valid_from": "2026-03-08T05:00:00Z", "valid_to": "2026-03-09T04:00:00Z"},
        )

    def test_skipped_date_refuses(self):
        with self.assertRaises(ValueError):
            instant("2011-12-30", "Pacific/Apia")

    def test_due_is_not_completion(self):
        r = record(I + "Vtodo", I + "dtstart")
        r["properties"][I + "due"] = ["2026-10-10T00:00:00Z"]
        self.assertIsNone(project(P, "calendar", r)["valid_to"])
        r["properties"][I + "completed"] = ["2026-10-09T00:00:00Z"]
        self.assertEqual(project(P, "calendar", r)["valid_to"], "2026-10-09T00:00:00Z")

    def test_missing_and_multivalued_start_refuse(self):
        for values in ([], [T, T], T):
            r = record()
            r["properties"][S + "dateCreated"] = values
            with self.subTest(values=values), self.assertRaises(ValueError):
                project(P, "tracker", r)

    def test_invalid_timestamps_refuse(self):
        for value in (
            "2026-10-07T02:55:21",
            "2026-02-30T00:00:00Z",
            "2026-10-07T00:00:00-00:00",
            "2026-10-07T00:00:00+00:99",
            "2026-10-07T00:00:00.1234567890Z",
            "",
            None,
        ):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                instant(value)

    def test_equal_and_backwards_end_refuse(self):
        for end in (T, "2020-01-01T00:00:00Z"):
            with self.subTest(end=end), self.assertRaises(ValueError):
                project(P, "tracker", record(end=end))

    def test_conflicting_classes_refuse(self):
        r = record(I + "Vevent", I + "dtstart")
        r["types"].append(I + "Vtodo")
        with self.assertRaises(ValueError):
            project(P, "calendar", r)

    def test_unknown_class_refuses_no_default(self):
        with self.assertRaises(ValueError):
            project(P, "tracker", record(S + "Event"))

    def test_point_epsilon_positive_integer(self):
        for epsilon in (0, -1, True, "1"):
            bad = copy.deepcopy(P)
            bad["profiles"]["point"][O + "Observation"]["epsilon_ns"] = epsilon
            with self.subTest(epsilon=epsilon), self.assertRaises(ValueError):
                project(bad, "point", record(O + "Observation", O + "resultTime"))

    def test_profile_terms_are_pinned_public_terms(self):
        terms = set()
        for path in (ROOT / "vocab").glob("*.terms"):
            terms.update(path.read_text().splitlines())
        for profile in P["profiles"].values():
            for kind, rule in profile.items():
                self.assertIn(kind, terms)
                for key in ("start", "end"):
                    if key in rule:
                        self.assertIn(rule[key], terms)

    def test_negative_epoch_exact_roundtrip(self):
        value = "1969-12-31T23:59:59.999999999Z"
        self.assertEqual(instant(value), -1)
        self.assertEqual(stamp(-1), value)


if __name__ == "__main__":
    unittest.main()
