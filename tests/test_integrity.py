"""Every integrity rule must detect the corruption it names."""

from __future__ import annotations

import unittest

from engine.claims import add_claim, get_claim, link_claims, link_to_question, set_verdict
from engine.errors import EngineError
from engine.hypotheses import add_hypothesis
from engine.integrity import (
    check,
    findings_for_research,
    has_errors,
    render_json,
    render_markdown,
)
from engine.questions import add_question
from engine.researches import create_research
from tests.support import DatabaseCase, force_numeric


def codes(findings) -> set[str]:
    return {finding.code for finding in findings}


class IntegrityTests(DatabaseCase):
    def _clean_program(self) -> str:
        research = self.add_research()
        question = add_question(self.conn, research, "Does the mechanism hold?")
        claim = add_claim(
            self.conn, research, "The mechanism holds by construction.", "assumption",
            kill_test="An observation that violates the construction.",
        )
        link_to_question(self.conn, claim.id, question.id, "supports")
        set_verdict(self.conn, claim.id, "PROVEN", "definitional argument")
        add_hypothesis(self.conn, research, "A prediction follows.", "The prediction fails.")
        return research

    def test_clean_program_has_no_errors(self) -> None:
        self._clean_program()
        findings = check(self.conn)
        self.assertFalse(has_errors(findings), findings)

    def test_missing_provenance_is_detected(self) -> None:
        research = self.add_research()
        claim = self.add_empirical(research)
        self.conn.execute("UPDATE claim SET quote = '' WHERE id = ?", (claim,))
        self.assertIn("PROV-001", codes(check(self.conn)))

    def test_source_without_identifier_is_detected(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        self.conn.execute("UPDATE source SET year = NULL WHERE id = ?", (source,))
        self.assertIn("PROV-002", codes(check(self.conn)))

    def test_promoted_claim_needs_kill_test(self) -> None:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Promoted.", "assumption", kill_test="A counterexample."
        )
        set_verdict(self.conn, claim.id, "PROVEN", "proof")
        self.conn.execute("UPDATE claim SET kill_test = '' WHERE id = ?", (claim.id,))
        self.assertIn("EVID-001", codes(check(self.conn)))

    def test_numeric_claim_needs_two_run_test(self) -> None:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Measured.", "assumption", kill_test="A different measurement."
        )
        with self.assertRaises(EngineError):
            set_verdict(self.conn, claim.id, "NUMERIC", "single manual run")
        force_numeric(self.conn, claim.id)
        self.assertIn("EVID-002", codes(check(self.conn)))

    def test_failed_status_needs_evidence(self) -> None:
        research = self.add_research()
        claim = self.add_empirical(research)
        self.conn.execute("UPDATE claim SET status = 'FALSIFIED' WHERE id = ?", (claim,))
        self.assertIn("EVID-003", codes(check(self.conn)))

    def test_hypothesis_outcome_needs_verdict(self) -> None:
        research = self.add_research()
        hypothesis = add_hypothesis(self.conn, research, "Prediction.", "Failure criterion.")
        self.conn.execute(
            "UPDATE hypothesis SET status = 'REFUTED' WHERE id = ?", (hypothesis.id,)
        )
        self.assertIn("EVID-004", codes(check(self.conn)))

    def test_dependency_cycle_is_detected(self) -> None:
        research = self.add_research()
        first = add_claim(self.conn, research, "First.", "assumption", basis="a")
        second = add_claim(self.conn, research, "Second.", "assumption", basis="b")
        link_claims(self.conn, first.id, second.id, "depends_on")
        link_claims(self.conn, second.id, first.id, "depends_on")
        self.assertIn("GRAPH-001", codes(check(self.conn)))

    def test_dangling_and_self_edges_are_detected(self) -> None:
        self.conn.execute(
            "INSERT INTO edge(id, src_kind, src_id, dst_kind, dst_id, rel, created_at)"
            " VALUES ('e_999999', 'claim', 'c_999999', 'claim', 'c_999998', 'related', 'now')"
        )
        self.conn.execute(
            "INSERT INTO edge(id, src_kind, src_id, dst_kind, dst_id, rel, created_at)"
            " VALUES ('e_999998', 'claim', 'c_999999', 'claim', 'c_999999', 'related', 'now')"
        )
        found = codes(check(self.conn))
        self.assertIn("GRAPH-002", found)
        self.assertIn("GRAPH-003", found)

    def test_cross_program_edge_is_detected(self) -> None:
        first = self.add_research("First")
        second = self.add_research("Second")
        left = add_claim(self.conn, first, "Left.", "assumption", basis="a")
        right = add_claim(self.conn, second, "Right.", "assumption", basis="b")
        self.conn.execute(
            "INSERT INTO edge(id, src_kind, src_id, dst_kind, dst_id, rel, created_at)"
            " VALUES ('e_999997', 'claim', ?, 'claim', ?, 'related', 'now')",
            (left.id, right.id),
        )
        self.assertIn("SCOPE-001", codes(check(self.conn)))

    def test_stale_dependent_is_detected(self) -> None:
        research = self.add_research()
        root = self.add_empirical(research)
        derived = add_claim(
            self.conn, research, "Depends on root.", "derived", basis="from root",
            prerequisites=[root],
        )
        self.conn.execute("UPDATE claim SET status = 'FALSIFIED' WHERE id = ?", (root,))
        self.assertIn("CASCADE-001", codes(check(self.conn)))

    def test_gaps_and_duplicates_are_warnings(self) -> None:
        research = self.add_research()
        add_question(self.conn, research, "Unanswered?")
        claim = add_claim(self.conn, research, "Repeated text.", "assumption", basis="a")
        add_claim(self.conn, research, "Repeated text.", "assumption", basis="b")
        found = codes(check(self.conn))
        self.assertIn("GAP-001", found)
        self.assertIn("GAP-002", found)
        self.assertIn("DUP-001", found)
        self.assertNotIn(claim, [])

    def test_empty_program_warns(self) -> None:
        create_research(self.conn, "Empty")
        self.assertIn("EMPTY-001", codes(check(self.conn)))

    def test_renderers_are_stable(self) -> None:
        findings = check(self.conn)
        self.assertIn("Integrity check", render_markdown(findings))
        self.assertTrue(render_json(findings).startswith("["))



    def test_stale_numeric_evidence_is_detected(self) -> None:
        import sys
        import tempfile
        from pathlib import Path

        from engine.claims import add_claim
        from engine.killtests import add_test, verify_test

        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Measured value.", "empirical",
            source_ref=self.add_source(research), quote="Measured value.", locator="p.1",
            kill_test="A different measurement.",
        )
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        script = Path(directory.name) / "measure.py"
        script.write_text("print('value=1')\n", encoding="utf-8")
        test = add_test(
            self.conn, research, "Measure", f'"{sys.executable}" "{script}"', claim_ref=claim.id
        )
        result = verify_test(self.conn, test.id)
        self.assertTrue(result["verification_complete"])
        set_verdict(self.conn, claim.id, "NUMERIC", f"{test.id} two-run verification")
        self.assertNotIn("EVID-005", codes(check(self.conn)))
        self.conn.execute("UPDATE test_run SET code_sha256 = ? WHERE test_id = ?", ("0" * 64, test.id))
        self.assertIn("EVID-005", codes(check(self.conn)))

    def test_retracted_source_blocks_a_live_claim(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        claim = add_claim(
            self.conn, research, "Cites retracted work.", "empirical",
            source_ref=source, quote="Cites retracted work.", locator="p.1",
            kill_test="A replicate.",
        )
        self.conn.execute("UPDATE source SET status = 'retracted' WHERE id = ?", (source,))
        findings = [item for item in check(self.conn) if item.code == "PROV-003"]
        self.assertEqual([item.subject for item in findings], [claim.id])

    def test_expression_of_concern_is_a_warning(self) -> None:
        research = self.add_research()
        source = self.add_source(research)
        add_claim(
            self.conn, research, "Concerned work.", "empirical",
            source_ref=source, quote="Concerned work.", locator="p.1", kill_test="A replicate.",
        )
        self.conn.execute(
            "UPDATE source SET status = 'expression_of_concern' WHERE id = ?", (source,)
        )
        findings = [item for item in check(self.conn) if item.code == "PROV-004"]
        self.assertEqual([item.severity for item in findings], ["warning"])




    def test_unknown_is_recorded_with_a_reason(self) -> None:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Missing data claim.", "assumption",
            kill_test="A measurement that exists.",
        )
        set_verdict(self.conn, claim.id, "UNKNOWN", "the cohort data was never released")
        self.assertEqual(get_claim(self.conn, claim.id).status, "UNKNOWN")
        self.assertNotIn("EVID-007", codes(check(self.conn)))

    def test_unknown_without_a_reason_warns(self) -> None:
        research = self.add_research()
        claim = add_claim(self.conn, research, "Silent unknown.", "assumption", basis="a")
        self.conn.execute("UPDATE claim SET status = 'UNKNOWN' WHERE id = ?", (claim.id,))
        findings = [item for item in check(self.conn) if item.code == "EVID-007"]
        self.assertEqual([item.severity for item in findings], ["warning"])

    def test_unknown_is_not_a_failure_state(self) -> None:
        from engine.models import FAILED_STATUSES

        self.assertNotIn("UNKNOWN", FAILED_STATUSES)

    def test_promotion_is_blocked_by_an_unknown_premise(self) -> None:
        research = self.add_research()
        root = add_claim(self.conn, research, "Root.", "assumption", basis="a")
        derived = add_claim(
            self.conn, research, "Depends on root.", "derived", basis="b",
            prerequisites=[root.id], kill_test="A counterexample.",
        )
        set_verdict(self.conn, root.id, "UNKNOWN", "data missing")
        with self.assertRaises(EngineError):
            set_verdict(self.conn, derived.id, "PROVEN", "an argument")


    def test_out_of_order_hypothesis_outcome_is_scoped_to_its_hypothesis(self) -> None:
        research = self.add_research()
        self.conn.execute(
            "INSERT INTO hypothesis(id, research_id, statement, criterion, confidence,"
            " registered_at, status, outcome_note, updated_at) VALUES ('h_1', ?, 's', 'c', 0.5,"
            " '2999-01-01T00:00:00+00:00', 'PREREGISTERED', '', 'now')",
            (research,),
        )
        self.conn.execute(
            "INSERT INTO verdict(id, subject_kind, subject_id, status, previous_status, evidence,"
            " note, actor, at, evidence_group) VALUES ('v_1', 'hypothesis', 'h_1', 'REFUTED',"
            " 'PREREGISTERED', 'e', '', 'a', '2000-01-01T00:00:00+00:00', '')"
        )
        findings = [item for item in check(self.conn) if item.code == "PRE-001"]
        self.assertEqual([item.subject for item in findings], ["h_1"])
        scoped = [item for item in findings_for_research(self.conn, research)
                  if item.code == "PRE-001"]
        self.assertEqual([item.subject for item in scoped], ["h_1"])


if __name__ == "__main__":
    unittest.main()
