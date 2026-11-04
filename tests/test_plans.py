"""Analysis plans are preregistered; unmatched comparisons read as exploratory."""

from __future__ import annotations

import unittest

from engine.analysis import claim_statistics
from engine.claims import add_claim
from engine.errors import EngineError
from engine.observations import add_observation
from engine.plans import add_plan, list_plans
from tests.support import DatabaseCase


class PlanTests(DatabaseCase):
    def _planned_claim(self) -> str:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Treatment raises the value.", "assumption", basis="p"
        ).id
        for value in (1.2, 1.4, 1.1, 1.3, 1.25, 1.35):
            add_observation(self.conn, claim, "baseline", value)
        for value in (1.9, 2.1, 2.0, 2.2, 1.95, 2.05):
            add_observation(self.conn, claim, "treatment", value)
        return claim

    def test_plan_registers_before_data_is_seen(self) -> None:
        research = self.add_research()
        claim = add_claim(
            self.conn, research, "Treatment raises the value.", "assumption", basis="p"
        ).id
        plan = add_plan(
            self.conn, claim, "baseline", "treatment", "treatment mean exceeds baseline"
        )
        self.assertEqual(plan.status, "PREREGISTERED")
        self.assertEqual(plan.claim_id, claim)
        self.assertEqual([item.id for item in list_plans(self.conn, claim)], [plan.id])

    def test_plan_needs_a_prediction_and_two_groups(self) -> None:
        claim = self._planned_claim()
        with self.assertRaises(EngineError):
            add_plan(self.conn, claim, "baseline", "treatment", "   ")
        with self.assertRaises(EngineError):
            add_plan(self.conn, claim, "baseline", "baseline", "no difference")

    def test_cited_plan_is_recorded_on_the_comparison(self) -> None:
        claim = self._planned_claim()
        plan = add_plan(
            self.conn, claim, "baseline", "treatment", "treatment mean exceeds baseline"
        )
        result = claim_statistics(
            self.conn, claim, "baseline", "treatment", resamples=50, plan_ref=plan.id
        )
        self.assertEqual(result["plan"], plan.id)
        self.assertFalse(
            any("exploratory" in warning for warning in result["warnings"])
        )

    def test_uncited_comparison_with_plans_is_exploratory(self) -> None:
        claim = self._planned_claim()
        add_plan(
            self.conn, claim, "baseline", "treatment", "treatment mean exceeds baseline"
        )
        result = claim_statistics(
            self.conn, claim, "baseline", "treatment", resamples=50
        )
        self.assertTrue(
            any("exploratory" in warning for warning in result["warnings"])
        )

    def test_plan_must_match_the_compared_pair(self) -> None:
        claim = self._planned_claim()
        plan = add_plan(
            self.conn, claim, "baseline", "treatment", "treatment mean exceeds baseline"
        )
        with self.assertRaises(EngineError):
            claim_statistics(
                self.conn, claim, "treatment", "baseline", resamples=50,
                plan_ref=plan.id,
            )

    def test_plan_belongs_to_one_claim(self) -> None:
        claim = self._planned_claim()
        plan = add_plan(
            self.conn, claim, "baseline", "treatment", "treatment mean exceeds baseline"
        )
        sibling = add_claim(
            self.conn, plan.research_id, "Sibling.", "assumption", basis="q"
        ).id
        for value in (1.0, 1.1, 1.2):
            add_observation(self.conn, sibling, "baseline", value)
            add_observation(self.conn, sibling, "treatment", value + 1.0)
        with self.assertRaises(EngineError):
            claim_statistics(
                self.conn, sibling, "baseline", "treatment", resamples=50,
                plan_ref=plan.id,
            )


if __name__ == "__main__":
    unittest.main()
