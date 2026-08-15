"""Census-derived, lane-specific research time-window contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

AUTHORITY = "existing_db_development_no_oos_no_adoption"


def _hhmmss_to_minute(value: str | int) -> int:
    text = str(value).zfill(6)
    if len(text) != 6 or not text.isdigit():
        raise ValueError("window value must be HHMMSS")
    hour, minute, second = int(text[:2]), int(text[2:4]), int(text[4:])
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError("invalid HHMMSS window value")
    return hour * 60 + minute


@dataclass(frozen=True, slots=True)
class ResearchWindowContract:
    lane: str
    start: int
    end_exclusive: int
    bucket_minutes: tuple[int, ...]
    source_fingerprint: str
    authority: str = AUTHORITY
    schema: str = "stom.research_window.v1"

    def __post_init__(self) -> None:
        start_minute = _hhmmss_to_minute(self.start)
        end_minute = _hhmmss_to_minute(self.end_exclusive)
        if self.lane not in {"stock_tick", "stock_min"}:
            raise ValueError("unsupported research lane")
        if end_minute <= start_minute:
            raise ValueError("window end must be after start")
        expected = tuple(range(start_minute, end_minute, 5))
        if self.bucket_minutes != expected:
            raise ValueError("window buckets must be contiguous five-minute coverage")
        if self.authority != AUTHORITY:
            raise ValueError("window authority mismatch")

    @property
    def contract_sha256(self) -> str:
        canonical = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "contract_sha256": self.contract_sha256}


def window_contract_from_census(payload: Mapping[str, Any]) -> ResearchWindowContract:
    if payload.get("status") != "CENSUS_COMPLETED":
        raise ValueError("census is not completed")
    raw = payload.get("window_contract")
    if not isinstance(raw, Mapping) or raw.get("status") != "AVAILABLE":
        raise ValueError("census common window is unavailable")
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("census source is missing")
    fingerprint = source.get("fingerprint")
    if not isinstance(fingerprint, Mapping) or not fingerprint.get("sha256"):
        raise ValueError("census source fingerprint is missing")
    return ResearchWindowContract(
        lane=str(source.get("lane")),
        start=int(str(raw.get("start"))),
        end_exclusive=int(str(raw.get("end_exclusive"))),
        bucket_minutes=tuple(int(value) for value in raw.get("bucket_minutes") or ()),
        source_fingerprint=str(fingerprint["sha256"]),
    )


def window_contract_from_mapping(payload: Mapping[str, Any]) -> ResearchWindowContract:
    return ResearchWindowContract(
        lane=str(payload.get("lane")), start=int(payload.get("start")),
        end_exclusive=int(payload.get("end_exclusive")),
        bucket_minutes=tuple(int(value) for value in payload.get("bucket_minutes") or ()),
        source_fingerprint=str(payload.get("source_fingerprint")),
        authority=str(payload.get("authority", AUTHORITY)),
    )
