"""N1 suitable ports: provenance-gated correlation, batch stats-all, CSV import."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from engine.analysis import batch_statistics, group_correlations
from engine.claims import add_claim
from engine.errors import EngineError
from engine.observations import (
    CSV_TEMPLATE_HEADER,
    add_observation,
    group_values,
    import_observations_csv,
)
from engine.protocols import register_protocol
from engine.stats import pearson
from tests.support import DatabaseCase


class PearsonTests(unittest.TestCase):
    def test_perfect_correlation(self) -> None:
        result = pearson([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0])
        self.assertAlmostEqual(result["r"], 1.0, places=6)
        self.assertEqual(result["n"], 4)

    def test_anticorrelation(self) -> None:
        result = pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
        self.assertAlmostEqual(result["r"], -1.0, places=6)

    def test_degenerate_variance_yields_zero(self) -> None:
        result = pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
        self.assertEqual(result["r"], 0.0)

    def test_fewer_than_three_pairs_yields_zero(self) -> None:
        result = pearson([1.0, 2.0], [1.0, 2.0])
        self.assertEqual(result["r"], 0.0)
        self.assertEqual(result["n"], 2)


class CorrelationTests(DatabaseCase):
    def _claim_with_groups(self) -> str:
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        for value in (1.0, 2.0, 3.0, 4.0):
            add_observation(self.conn, claim, "baseline", value)
        for value in (2.0, 4.0, 6.0, 8.0):
            add_observation(self.conn, claim, "treatment", value)
        return claim

    def test_correlated_groups_rank_first(self) -> None:
        claim = self._claim_with_groups()
        pairs = group_correlations(self.conn, claim)
        self.assertEqual(len(pairs), 1)
        self.assertAlmostEqual(pairs[0]["r"], 1.0, places=6)
        self.assertTrue(pairs[0]["comparable"])
        self.assertTrue(
            any("no measurement provenance" in warning for warning in pairs[0]["warnings"])
        )

    def test_truncation_is_reported(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        for value in (1.0, 2.0, 3.0, 4.0, 5.0):
            add_observation(self.conn, claim, "baseline", value)
        for value in (2.0, 4.0, 6.0):
            add_observation(self.conn, claim, "treatment", value)
        pairs = group_correlations(self.conn, claim)
        self.assertEqual(pairs[0]["n"], 3)
        self.assertTrue(any("truncated" in warning for warning in pairs[0]["warnings"]))

    def test_incomparable_protocols_are_recorded_not_raised(self) -> None:
        register_protocol(self.conn, "p-one", "measures one")
        register_protocol(self.conn, "p-two", "measures two")
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        for value in (1.0, 2.0, 3.0):
            add_observation(
                self.conn, claim, "baseline", value,
                instrument_kind="sensor", instrument_id="m", instrument_digest="d",
                rater_kind="automated", rater_id="r", rater_version="1",
                protocol_id="p-one", unit="u",
            )
        for value in (1.0, 2.0, 3.0):
            add_observation(
                self.conn, claim, "treatment", value,
                instrument_kind="sensor", instrument_id="m", instrument_digest="d",
                rater_kind="automated", rater_id="r", rater_version="1",
                protocol_id="p-two", unit="u",
            )
        pairs = group_correlations(self.conn, claim)
        self.assertFalse(pairs[0]["comparable"])
        # Explicit allowance still reports the caveat instead of raising.
        allowed = group_correlations(
            self.conn, claim, allow_incomparable=True
        )
        self.assertFalse(allowed[0]["comparable"])
        self.assertTrue(any("incomparable" in w for w in allowed[0]["warnings"]))

    def test_fewer_than_two_groups_refused(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        add_observation(self.conn, claim, "only", 1.0)
        with self.assertRaises(EngineError):
            group_correlations(self.conn, claim)


class BatchStatisticsTests(DatabaseCase):
    def _claim(self, research: str, baseline, treatment) -> str:
        claim = add_claim(self.conn, research, "S rises here.", "assumption", basis="b").id
        for value in baseline:
            add_observation(self.conn, claim, "baseline", value)
        for value in treatment:
            add_observation(self.conn, claim, "treatment", value)
        return claim

    def test_errors_are_isolated_per_claim(self) -> None:
        research = self.add_research()
        good = self._claim(research, [1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        bad_claim = add_claim(self.conn, research, "Thin.", "assumption", basis="b").id
        add_observation(self.conn, bad_claim, "baseline", 1.0)
        result = batch_statistics(self.conn, research, "baseline", "treatment")
        self.assertIn(good, result["results"])
        self.assertIn(bad_claim, result["errors"])
        self.assertEqual(result["research"], research)

    def test_many_claims_warn(self) -> None:
        research = self.add_research()
        for index in range(4):
            self._claim(research, [1.0, 2.0, 3.0], [float(4 + index)] * 3)
        result = batch_statistics(self.conn, research, "baseline", "treatment")
        self.assertTrue(
            any("Multiple Comparison Risk" in w for w in result["global_warnings"])
        )


class CsvImportTests(DatabaseCase):
    def _write_csv(self, rows) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "obs.csv"
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["group_label", "value", "note"])
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(lambda: tmp.unlink(missing_ok=True))
        return tmp

    def test_valid_rows_import_and_bad_rows_skip(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        path = self._write_csv(
            [
                {"group_label": "baseline", "value": "1.0", "note": ""},
                {"group_label": "baseline", "value": "not-a-number", "note": ""},
                {"group_label": "", "value": "", "note": ""},
                {"group_label": "treatment", "value": "2.0", "note": ""},
            ]
        )
        result = import_observations_csv(self.conn, claim, path)
        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["skipped"], 1)
        values = group_values(self.conn, claim)
        self.assertEqual(values["baseline"], [1.0])
        self.assertEqual(values["treatment"], [2.0])

    def test_missing_header_refused(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        tmp = Path(tempfile.mkdtemp()) / "bad.csv"
        tmp.write_text("group_label\nbaseline\n", encoding="utf-8")
        self.addCleanup(lambda: tmp.unlink(missing_ok=True))
        with self.assertRaises(EngineError):
            import_observations_csv(self.conn, claim, tmp)

    def test_alternate_group_header_accepted(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "S rises.", "assumption", basis="b").id
        tmp = Path(tempfile.mkdtemp()) / "alt.csv"
        tmp.write_text("group,value\nbaseline,1.0\n", encoding="utf-8")
        self.addCleanup(lambda: tmp.unlink(missing_ok=True))
        result = import_observations_csv(self.conn, claim, tmp)
        self.assertEqual(result["imported"], 1)


class TemplateTests(unittest.TestCase):
    def test_header_names_required_columns_first(self) -> None:
        header = CSV_TEMPLATE_HEADER.split(",")
        self.assertEqual(header[:2], ["group_label", "value"])
        for column in ("protocol_id", "unit", "provenance_class"):
            self.assertIn(column, header)


if __name__ == "__main__":
    unittest.main()
