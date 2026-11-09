"""The comparative reader validates persisted sources without changing them."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import unittest

from qtre.validation.comparative_report import (
    InvalidSource, _validate_identities, read_comparative_report, report_json, report_table,
)


SOURCE = Path(__file__).resolve().parents[1] / "examples" / "f2_cost_sensitivity_v1"


def file_hashes(root):
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class ComparativeReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read_comparative_report(SOURCE)

    def test_fixture_values_states_and_deterministic_bytes(self):
        report = self.report
        self.assertEqual(report["report_schema_version"], 1)
        self.assertEqual(sum(map(len, report["runs"].values())), 9)
        self.assertEqual(sum(map(len, report["comparisons"].values())), 6)
        base = report["runs"]["momentum"]["base"]
        self.assertEqual(base["costs_brl"]["total"], Decimal("90.78"))
        self.assertEqual(str(base["costs_bps"]["total"]), "15.00347073017551978316200046")
        self.assertIsNone(base["cumulative_return"])
        self.assertEqual(base["return_status"], "UNAVAILABLE_INCOMPLETE_NAV")
        self.assertEqual(base["incomplete_sessions"], ["2025-02-04"])
        cash = report["runs"]["cash"]["base"]
        self.assertEqual(str(cash["cumulative_return"]), "0")
        self.assertEqual(cash["costs_bps"], {"total": None, "status": "UNAVAILABLE_NO_NOTIONAL"})
        self.assertEqual(report["comparisons"]["momentum"]["zero_to_base"]["monotonicity"],
                         "NOT_COMPARABLE_EXECUTION_CHANGED")
        self.assertEqual(report["comparisons"]["cash"]["zero_to_base"]["nav_points_compared"], 66)
        self.assertEqual(report_json(report), report_json(read_comparative_report(SOURCE)))
        self.assertEqual(json.loads(report_json(report))["runs"]["momentum"]["base"]["costs_brl"]["total"], "90.78")
        self.assertIn("NOT_COMPARABLE_EXECUTION_CHANGED", report_table(report))

    def test_reader_does_not_modify_artifacts(self):
        before = file_hashes(SOURCE)
        read_comparative_report(SOURCE)
        self.assertEqual(file_hashes(SOURCE), before)

    def test_changed_artifact_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            copytree(SOURCE, root)
            path = root / "momentum-base" / "fills.jsonl"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(InvalidSource, "momentum-base.*fills.jsonl"):
                read_comparative_report(root)

    def test_missing_audit_is_rejected_without_creating_it(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            copytree(SOURCE, root)
            path = root / "cash-base" / "audit.json"
            path.unlink()
            with self.assertRaisesRegex(InvalidSource, "cash-base.*audit.json"):
                read_comparative_report(root)
            self.assertFalse(path.exists())

    def test_linked_artifact_is_rejected_without_changing_source(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            copytree(SOURCE, root)
            path = root / "cash-base" / "nav.jsonl"
            path.unlink()
            path.symlink_to(SOURCE / "cash-base" / "nav.jsonl")
            before = file_hashes(SOURCE)
            with self.assertRaisesRegex(InvalidSource, "cash-base/nav.jsonl.*linked artifact"):
                read_comparative_report(root)
            self.assertEqual(file_hashes(SOURCE), before)

    def test_cross_strategy_execution_assumptions_are_required(self):
        manifests = {strategy: {
            scenario: json.loads((SOURCE / f"{strategy}-{scenario}" / "manifest.json").read_text())["run"]
            for scenario in ("zero", "base", "high")}
            for strategy in ("momentum", "equal_weight", "cash")}
        for key, changed in (("settlement", "other"),
                             ("monetary_rounding", "other"),
                             ("decimal_precision", 30)):
            with self.subTest(key=key):
                altered = deepcopy(manifests)
                for run in altered["cash"].values():
                    run[key] = changed
                with self.assertRaisesRegex(InvalidSource, "common execution assumptions mismatch"):
                    _validate_identities(SOURCE, altered)

    def test_malformed_cost_is_reported_as_invalid_source(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            copytree(SOURCE, root)
            run = root / "cash-base"
            manifest_path = run / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["run"]["config"]["fees_bps"] = "invalid"
            manifest_path.write_text(json.dumps(manifest))
            audit_path = run / "audit.json"
            audit = json.loads(audit_path.read_text())
            audit["manifest_sha256"] = sha256(manifest_path.read_bytes()).hexdigest()
            audit_path.write_text(json.dumps(audit))
            with self.assertRaisesRegex(InvalidSource, "cash-base.*invalid scenario cost"):
                read_comparative_report(root)

    def test_changed_sensitivity_and_missing_run_are_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            copytree(SOURCE, root)
            path = root / "sensitivity.json"
            data = json.loads(path.read_text())
            data["runs"]["cash"]["base"]["fills"] = 1
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(InvalidSource, "cash-base.*sensitivity run mismatch"):
                read_comparative_report(root)
            path.write_bytes((SOURCE / "sensitivity.json").read_bytes())
            (root / "cash-high").rename(root / "cash-other")
            with self.assertRaisesRegex(InvalidSource, "run directory set mismatch"):
                read_comparative_report(root)


if __name__ == "__main__":
    unittest.main()
