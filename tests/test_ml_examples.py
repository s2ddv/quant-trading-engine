"""Manual synthetic oracles and temporal leakage counterexamples."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from qtre.validation.ml_examples import (Example, Factor, Label, TemporalSplit,
                                         factor_as_of, split_examples)


def at(day):
    return datetime.fromisoformat(day + "T18:00:00+00:00")


def factor(value="0.10", available="2026-02-27"):
    return Factor("A", "momentum", Decimal(value), "synthetic-close", "v1",
                  at(available), at(available))


def row(decision, end, label_available, *, ident="A", chosen=None):
    # 110 / 100 - 1 = 0.10, a dimensionless simple return.
    return Example(ident, at(decision), (chosen or factor(),),
                   Label(Decimal("0.10"), at(decision) + timedelta(days=1),
                         at(end), at(label_available),
                         "synthetic-total-return", "v1"))


class MlExampleTests(unittest.TestCase):
    def setUp(self):
        self.split = TemporalSplit(at("2026-01-01"), at("2026-03-01"),
                                   at("2026-05-01"), at("2027-06-01"),
                                   at("2027-08-01"), at("2026-03-01"))

    def test_manual_return_and_chronological_assignment(self):
        validation = row("2026-03-15", "2026-04-15", "2026-04-16")
        final = row("2027-06-15", "2027-07-15", "2027-07-16")
        # Training labels must end after their decision, so use a February 20 decision.
        train = row("2026-02-20", "2026-02-28", "2026-02-28",
                    chosen=factor("0.10", "2026-02-19"))
        manifest = split_examples((train, validation, final), self.split)
        self.assertEqual(train.label.value, (Decimal(110) / Decimal(100) - 1))
        self.assertEqual(manifest.train, (("A", at("2026-02-20")),))
        self.assertEqual(manifest.validation, (("A", at("2026-03-15")),))
        self.assertEqual(manifest.final_reserved, (("A", at("2027-06-15")),))

    def test_future_factor_rejected(self):
        leaked = row("2026-02-28", "2026-03-15", "2026-03-16",
                     chosen=factor("0.90", "2026-03-02"))
        with self.assertRaisesRegex(ValueError, "factor is unavailable"):
            leaked.validate()

    def test_label_crossing_validation_start_is_purged(self):
        crossing = row("2026-02-28", "2026-03-15", "2026-03-16")
        manifest = split_examples((crossing,), self.split)
        self.assertEqual(manifest.train, ())
        self.assertEqual(manifest.excluded[0][2], "label_overlaps_validation")

    def test_label_unknown_at_fit_is_purged(self):
        late = row("2026-02-20", "2026-02-28", "2026-03-02",
                   chosen=factor(available="2026-02-19"))
        self.assertEqual(split_examples((late,), self.split).excluded[0][2],
                         "label_unavailable_at_fit")

    def test_validation_label_unknown_at_final_selection_is_purged(self):
        late = row("2026-03-15", "2026-04-15", "2027-05-01")
        self.assertEqual(split_examples((late,), self.split).excluded[0][2],
                         "label_unavailable_at_selection")

    def test_validation_label_crossing_selection_is_purged(self):
        crossing = row("2026-03-15", "2026-05-02", "2026-05-03")
        self.assertEqual(split_examples((crossing,), self.split).excluded[0][2],
                         "label_overlaps_selection")

    def test_short_final_embargo_rejected(self):
        short = TemporalSplit(at("2026-01-01"), at("2026-03-01"),
                              at("2026-05-01"), at("2027-05-31"),
                              at("2027-08-01"), at("2026-03-01"))
        with self.assertRaisesRegex(ValueError, "13 calendar months"):
            short.validate()

    def test_future_revision_cannot_change_past_factor(self):
        past = factor("0.10", "2026-02-27")
        future = factor("0.90", "2026-03-02")
        decision = at("2026-02-28")
        self.assertEqual(factor_as_of((past,), decision), past)
        self.assertEqual(factor_as_of((past, future), decision), past)
        self.assertEqual(factor_as_of((past, factor("-0.80", "2026-03-02")), decision), past)

    def test_latest_observation_precedes_revision_publication_order(self):
        from dataclasses import replace
        newer = factor("0.20", "2026-02-28")
        revised_old = replace(factor("0.90", "2026-03-01"),
                              observed_at=at("2026-01-31"))
        self.assertEqual(factor_as_of((revised_old, newer), at("2026-03-02")), newer)

    def test_factor_from_another_instrument_rejected(self):
        from dataclasses import replace
        wrong = replace(factor(), instrument_id="B")
        with self.assertRaisesRegex(ValueError, "factor instrument"):
            row("2026-02-28", "2026-03-15", "2026-03-16", chosen=wrong).validate()


if __name__ == "__main__":
    unittest.main()
