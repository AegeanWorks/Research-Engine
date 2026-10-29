"""Measurement provenance and protocol comparability."""

from __future__ import annotations

import unittest

from engine.analysis import claim_statistics
from engine.claims import add_claim
from engine.errors import EngineError
from engine.integrity import check
from engine.observations import add_observation, get_observation
from engine.protocols import get_protocol, list_protocols, register_protocol
from engine.synthesis import report
from tests.support import DatabaseCase


class MeasurementTests(DatabaseCase):
    def setUp(self) -> None:
        super().setUp()
        self.research = self.add_research()
        self.claim = add_claim(
            self.conn, self.research, "Measured.", "assumption", basis="a"
        ).id
        register_protocol(self.conn, "accuracy_at_1", "top-1 accuracy on the held-out split")
        register_protocol(self.conn, "end_to_end_judge", "end-to-end judge score")

    def _kwargs(self, protocol: str = "accuracy_at_1", instrument: str = "rubric-a",
                digest: str = "a" * 64, unit: str = "score") -> dict:
        return {
            "instrument_kind": "rubric",
            "instrument_id": instrument,
            "instrument_digest": digest,
            "rater_kind": "human",
            "rater_id": "rater-1",
            "rater_version": "2026-01",
            "protocol_id": protocol,
            "sample_size": 1,
            "aggregation": "raw",
            "unit": unit,
            "provenance_class": "independent",
        }

    def _add(self, group: str, value: float, **overrides) -> None:
        values = self._kwargs()
        values.update(overrides)
        add_observation(self.conn, self.claim, group, value, **values)

    def test_protocol_registration_is_immutable(self) -> None:
        protocol = get_protocol(self.conn, "accuracy_at_1")
        self.assertEqual(protocol.measures, "top-1 accuracy on the held-out split")
        self.assertEqual([item.id for item in list_protocols(self.conn)],
                         ["accuracy_at_1", "end_to_end_judge"])
        with self.assertRaises(EngineError):
            register_protocol(self.conn, "accuracy_at_1", "different procedure")

    def test_observation_round_trips_provenance(self) -> None:
        self._add("baseline", 1.0)
        record = get_observation(self.conn, "ob_000001")
        self.assertEqual(record.instrument_kind, "rubric")
        self.assertEqual(record.instrument_id, "rubric-a")
        self.assertEqual(record.rater_version, "2026-01")
        self.assertEqual(record.protocol_id, "accuracy_at_1")
        self.assertEqual(record.unit, "score")

    def test_incomplete_provenance_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            add_observation(
                self.conn, self.claim, "baseline", 1.0, instrument_kind="rubric"
            )

    def test_unknown_protocol_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            self._add("baseline", 1.0, protocol_id="not_registered")

    def test_unknown_aggregation_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            self._add("baseline", 1.0, aggregation="mode")

    def test_legacy_observation_warns(self) -> None:
        add_observation(self.conn, self.claim, "baseline", 1.0)
        findings = [item for item in check(self.conn) if item.code == "OBS-002"]
        self.assertEqual(len(findings), 1)

    def test_same_protocol_is_comparable(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value)
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value)
        result = claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)
        self.assertTrue(result["comparability"]["comparable"])
        self.assertEqual(result["comparability"]["baseline_protocol"], "accuracy_at_1")

    def test_different_protocols_are_refused(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value)
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value, protocol_id="end_to_end_judge")
        with self.assertRaises(EngineError) as caught:
            claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)
        self.assertIn("not comparable", str(caught.exception))

    def test_incomparable_can_be_allowed_with_a_warning(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value)
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value, protocol_id="end_to_end_judge")
        result = claim_statistics(
            self.conn, self.claim, "baseline", "treatment", resamples=50,
            allow_incomparable=True,
        )
        self.assertFalse(result["comparability"]["comparable"])
        self.assertTrue(any("incomparable" in item for item in result["warnings"]))

    def test_different_instruments_are_refused(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value)
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value, instrument_id="rubric-b",
                      instrument_digest="b" * 64)
        with self.assertRaises(EngineError):
            claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)

    def test_different_units_are_refused(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value, unit="ms")
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value, unit="s")
        with self.assertRaises(EngineError):
            claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)

    def test_mixed_provenance_in_one_group_is_refused(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value)
        add_observation(self.conn, self.claim, "baseline", 1.3)
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value)
        with self.assertRaises(EngineError):
            claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)

    def test_self_reported_requires_a_producer_path(self) -> None:
        with self.assertRaises(EngineError):
            self._add("baseline", 1.0, provenance_class="self_reported")

    def test_unknown_provenance_class_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            self._add("baseline", 1.0, provenance_class="vendor")

    def test_self_reported_comparison_is_refused(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value, provenance_class="self_reported",
                      producer_path="engine/analysis.py")
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value, provenance_class="self_reported",
                      producer_path="engine/analysis.py")
        with self.assertRaises(EngineError) as caught:
            claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)
        self.assertIn("self-reported", str(caught.exception))
        result = claim_statistics(
            self.conn, self.claim, "baseline", "treatment", resamples=50,
            allow_self_reported=True,
        )
        self.assertFalse(result["comparability"]["comparable"])
        self.assertEqual(result["comparability"]["provenance_class"], "self_reported")

    def test_mixed_self_reported_group_is_refused(self) -> None:
        self._add("baseline", 1.0)
        self._add("baseline", 1.1, provenance_class="self_reported",
                  producer_path="engine/analysis.py")
        for value in (2.0, 2.1, 2.2):
            self._add("treatment", value)
        with self.assertRaises(EngineError):
            claim_statistics(self.conn, self.claim, "baseline", "treatment", resamples=50)

    def test_self_reported_measurements_are_separated_in_the_report(self) -> None:
        for value in (1.0, 1.1, 1.2):
            self._add("baseline", value)
        self._add("baseline", 9.0, provenance_class="self_reported",
                  producer_path="engine/analysis.py")
        text = report(self.conn, self.research)
        self.assertIn("### Self-reported measurements", text)

    def test_integrity_flags_unclassified_and_self_reported(self) -> None:
        add_observation(self.conn, self.claim, "baseline", 1.0)
        self._add("treatment", 2.0, provenance_class="self_reported",
                  producer_path="engine/analysis.py")
        found = {item.code for item in check(self.conn)}
        self.assertIn("OBS-003", found)
        self.assertIn("OBS-004", found)


if __name__ == "__main__":
    unittest.main()
