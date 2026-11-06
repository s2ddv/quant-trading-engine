"""Synthetic-only contracts for point-in-time ML rows and chronological splits.

This module validates research inputs; it does not train or trade.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from calendar import monthrange


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


def _number(value: Decimal, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")
    return value


def _add_months(value: datetime, count: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 + count
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return value.replace(year=year, month=month,
                         day=min(value.day, monthrange(year, month)[1]))


@dataclass(frozen=True)
class Factor:
    instrument_id: str
    name: str
    value: Decimal
    source_id: str
    source_version: str
    observed_at: datetime
    available_at: datetime

    def validate(self, decision_at: datetime, instrument_id: str) -> None:
        if self.instrument_id != instrument_id:
            raise ValueError("factor instrument differs from example")
        if not self.name or not self.source_id or not self.source_version:
            raise ValueError("factor name and source identity are required")
        _number(self.value, "factor value")
        _utc(self.observed_at, "factor observed_at")
        _utc(self.available_at, "factor available_at")
        if self.observed_at > self.available_at or self.available_at > decision_at:
            raise ValueError("factor is unavailable at decision")


def factor_as_of(candidates: tuple[Factor, ...], decision_at: datetime) -> Factor:
    """Choose the latest published revision of one factor at a decision."""
    _utc(decision_at, "decision_at")
    if len({(factor.instrument_id, factor.name) for factor in candidates}) != 1:
        raise ValueError("candidates must describe one instrument and factor")
    eligible = [factor for factor in candidates if factor.available_at <= decision_at]
    if not eligible:
        raise ValueError("no factor available at decision")
    chosen = max(eligible, key=lambda factor: (factor.observed_at, factor.available_at))
    chosen.validate(decision_at, chosen.instrument_id)
    return chosen


@dataclass(frozen=True)
class Label:
    value: Decimal  # proposed simple total return, dimensionless
    horizon_start: datetime
    horizon_end: datetime
    available_at: datetime
    source_id: str
    source_version: str

    def validate(self, decision_at: datetime) -> None:
        _number(self.value, "label value")
        _utc(self.horizon_start, "label horizon_start")
        _utc(self.horizon_end, "label horizon_end")
        _utc(self.available_at, "label available_at")
        if not self.source_id or not self.source_version:
            raise ValueError("label source identity is required")
        if (self.horizon_start <= decision_at or
                self.horizon_end <= self.horizon_start or
                self.available_at < self.horizon_end):
            raise ValueError("label horizon or availability is invalid")


@dataclass(frozen=True)
class Example:
    instrument_id: str
    decision_at: datetime
    factors: tuple[Factor, ...]
    label: Label

    def validate(self) -> None:
        _utc(self.decision_at, "decision_at")
        if not self.instrument_id or not self.factors:
            raise ValueError("instrument and factors are required")
        if len({factor.name for factor in self.factors}) != len(self.factors):
            raise ValueError("duplicate factor name")
        for factor in self.factors:
            factor.validate(self.decision_at, self.instrument_id)
        self.label.validate(self.decision_at)


@dataclass(frozen=True)
class TemporalSplit:
    train_start: datetime
    validation_start: datetime
    validation_end: datetime
    final_start: datetime
    final_end: datetime
    fit_at: datetime

    def validate(self) -> None:
        for name in ("train_start", "validation_start", "validation_end",
                     "final_start", "final_end", "fit_at"):
            _utc(getattr(self, name), name)
        if not (self.train_start < self.fit_at <= self.validation_start <
                self.validation_end <= self.final_start < self.final_end):
            raise ValueError("invalid chronological split boundaries")
        if self.final_start < _add_months(self.validation_end, 13):
            raise ValueError("final test requires 13 calendar months of embargo")


@dataclass(frozen=True)
class SplitManifest:
    train: tuple[tuple[str, datetime], ...]
    validation: tuple[tuple[str, datetime], ...]
    final_reserved: tuple[tuple[str, datetime], ...]
    excluded: tuple[tuple[str, datetime, str], ...]


def split_examples(examples: tuple[Example, ...], split: TemporalSplit) -> SplitManifest:
    """Purge labels crossing fold starts; keep final rows reserved, not fitted."""
    split.validate()
    train, validation, final, excluded = [], [], [], []
    seen = set()
    for row in examples:
        row.validate()
        key = (row.instrument_id, row.decision_at)
        if key in seen:
            raise ValueError("duplicate instrument and decision")
        seen.add(key)
        when = row.decision_at
        if split.train_start <= when < split.validation_start:
            if row.label.horizon_end >= split.validation_start:
                excluded.append((*key, "label_overlaps_validation"))
            elif row.label.available_at > split.fit_at:
                excluded.append((*key, "label_unavailable_at_fit"))
            else:
                train.append(key)
        elif split.validation_start <= when < split.validation_end:
            if row.label.horizon_end >= split.validation_end:
                excluded.append((*key, "label_overlaps_selection"))
            elif row.label.available_at > split.validation_end:
                excluded.append((*key, "label_unavailable_at_selection"))
            else:
                validation.append(key)
        elif split.final_start <= when < split.final_end:
            final.append(key)
        else:
            excluded.append((*key, "outside_folds"))
    return SplitManifest(tuple(train), tuple(validation), tuple(final), tuple(excluded))
