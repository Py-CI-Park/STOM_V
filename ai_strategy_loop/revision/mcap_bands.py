"""Frozen market-cap bands for existing-DB D3 research (unit: 억 KRW)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable


@dataclass(frozen=True, slots=True)
class McapBand:
    band_id: str
    lower: float | None
    upper: float | None
    lower_inclusive: bool = True
    upper_inclusive: bool = False

    def contains(self, value: float) -> bool:
        if not math.isfinite(value) or value < 0:
            return False
        lower_ok = self.lower is None or value > self.lower or (self.lower_inclusive and value == self.lower)
        upper_ok = self.upper is None or value < self.upper or (self.upper_inclusive and value == self.upper)
        return lower_ok and upper_ok

    def to_dict(self) -> dict:
        return asdict(self)


MCAP_BANDS = (
    McapBand("MCAP_A_LT3000", None, 3000, False, False),
    McapBand("MCAP_B_3000_5000", 3000, 5000),
    McapBand("MCAP_C_5000_10000", 5000, 10000),
    McapBand("MCAP_D_GE10000", 10000, None),
)


def band_for_value(value: object) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    matches = [band.band_id for band in MCAP_BANDS if band.contains(number)]
    if len(matches) > 1:
        raise RuntimeError(f"market-cap bands overlap for {number}")
    return matches[0] if matches else None


def mcap_band_case_sql(column: str = '"시가총액"') -> str:
    return (
        f"CASE WHEN {column} IS NULL OR {column} < 0 THEN 'INVALID' "
        f"WHEN {column} < 3000 THEN 'MCAP_A_LT3000' "
        f"WHEN {column} < 5000 THEN 'MCAP_B_3000_5000' "
        f"WHEN {column} < 10000 THEN 'MCAP_C_5000_10000' "
        "ELSE 'MCAP_D_GE10000' END"
    )


def validate_full_partition(values: Iterable[object]) -> dict[str, int]:
    counts = {band.band_id: 0 for band in MCAP_BANDS}
    invalid = 0
    for value in values:
        band_id = band_for_value(value)
        if band_id is None:
            invalid += 1
        else:
            counts[band_id] += 1
    return {**counts, "INVALID": invalid}
