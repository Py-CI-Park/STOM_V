"""Immutable typed evidence contracts (CL-R02).

정본 설계 문서: docs/research/condition_research/generated_conditions/
lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md §7 (schemas),
§8 (immutable ID/hash rules), §9 (append-only 저장 규칙 — 이 모듈은 저장
계층을 포함하지 않는다. append-only EvidenceStore 배선은 CL-R03).

이 모듈은 5개 불변(frozen) typed 계약만 정의한다:
``CandidatePassport`` / ``FeedbackEnvelope`` / ``FeedbackConsumption`` /
``EvaluationManifest`` / ``RunReceipt``. 전부 ``@dataclass(frozen=True,
slots=True)`` 이며, 구성 시점에 경계 검증을 통과해야 한다(실패 시
``ValueError``). 가변 컬렉션(dict/list)은 구성 시 복사되어 불변 매핑
(``types.MappingProxyType``)/튜플로 동결되므로, 호출자가 원본을 나중에
바꿔도 저장된 값은 영향받지 않는다.

DB/파일/네트워크 부작용 없음(순수 stdlib: dataclasses, hashlib, json, enum,
datetime, unicodedata). import 시점 부작용 없음.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Mapping as MappingABC
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

__all__ = [
    "CandidateMode",
    "FeedbackSide",
    "CandidatePassport",
    "FeedbackEnvelope",
    "FeedbackConsumption",
    "EvaluationManifest",
    "RunReceipt",
    "CANDIDATE_PASSPORT_SCHEMA",
    "FEEDBACK_ENVELOPE_SCHEMA",
    "FEEDBACK_CONSUMPTION_SCHEMA",
    "EVALUATION_MANIFEST_SCHEMA",
    "RUN_RECEIPT_SCHEMA",
    "ID_PREFIX_CANDIDATE",
    "ID_PREFIX_CANDIDATE_PASSPORT",
    "ID_PREFIX_FEEDBACK_ENVELOPE",
    "ID_PREFIX_FEEDBACK_CONSUMPTION",
    "ID_PREFIX_EVALUATION_MANIFEST",
    "ID_PREFIX_RUN_RECEIPT",
    "canonical_json",
    "sha256_hex",
    "text_sha256",
    "content_sha256",
    "compute_candidate_id",
    "compute_passport_id",
    "compute_feedback_id",
    "compute_consumption_id",
    "compute_manifest_id",
    "compute_receipt_id",
]


# ---------------------------------------------------------------------
# canonical JSON / hashing (design spec §8)
# ---------------------------------------------------------------------

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalize_newlines(text: str) -> str:
    """CRLF/lone-CR -> LF. hash/직렬화 이전 항상 적용(플랫폼 독립성)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _canonicalize(obj: Any, _path: str = "$") -> Any:
    """재귀적으로 JSON-safe canonical 구조로 정규화한다.

    문자열: NFC 정규화 + 개행 정규화. float: NaN/Infinity 거부. Mapping/tuple/
    list: 재귀 처리. 지원하지 않는 타입은 명시적으로 거부한다(무음 유실 방지).
    """
    if isinstance(obj, str):
        return _nfc(_normalize_newlines(obj))
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"non_finite_float_forbidden:{_path}")
        return obj
    if obj is None:
        return None
    if isinstance(obj, MappingProxyType) or isinstance(obj, MappingABC):
        return {
            str(key): _canonicalize(value, f"{_path}.{key}")
            for key, value in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(value, f"{_path}[]") for value in obj]
    if isinstance(obj, enum.Enum):
        return _canonicalize(obj.value, _path)
    raise ValueError(f"non_canonical_type:{_path}:{type(obj)!r}")


def canonical_json(obj: Any) -> str:
    """정렬된 키 + compact separators + NFC + LF 정규화 canonical JSON 문자열."""
    canonical = _canonicalize(obj)
    return json.dumps(
        canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def sha256_hex(text: str) -> str:
    """UTF-8 bytes sha256 hex (64자, 소문자). 입력은 그대로 인코딩된다."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_sha256(text: str) -> str:
    """자유 텍스트(비-JSON) sha256 — NFC + 개행 정규화 후 해시."""
    return sha256_hex(_nfc(_normalize_newlines(str(text))))


def content_sha256(instance: Any) -> str:
    """typed 계약 인스턴스의 canonical JSON(to_dict 기준) sha256 hex."""
    return sha256_hex(canonical_json(instance.to_dict()))


# ---------------------------------------------------------------------
# ID prefixes + factories (design spec §8)
# ---------------------------------------------------------------------

ID_PREFIX_CANDIDATE = "cand_"
ID_PREFIX_CANDIDATE_PASSPORT = "cp_"
ID_PREFIX_FEEDBACK_ENVELOPE = "fe_"
ID_PREFIX_FEEDBACK_CONSUMPTION = "fc_"
ID_PREFIX_EVALUATION_MANIFEST = "em_"
ID_PREFIX_RUN_RECEIPT = "rr_"


def _prefixed_id(prefix: str, payload: Mapping[str, Any]) -> str:
    return f"{prefix}{sha256_hex(canonical_json(payload))}"


def compute_candidate_id(
    buy_sha256: str, sell_sha256: str, methodology: str, timeframe: str
) -> str:
    """content identity: 동일 buy/sell 본문 + methodology/timeframe -> 동일 id.

    런(run)이 달라도 동일 body+methodology면 동일 candidate_id를 낸다(§8).
    """
    _require_sha256(buy_sha256, "buy_sha256")
    _require_sha256(sell_sha256, "sell_sha256")
    _require_nonempty_str(methodology, "methodology")
    _require_nonempty_str(timeframe, "timeframe")
    return _prefixed_id(
        ID_PREFIX_CANDIDATE,
        {
            "buy_sha256": buy_sha256,
            "sell_sha256": sell_sha256,
            "methodology": methodology,
            "timeframe": timeframe,
        },
    )


def compute_passport_id(run_id: str, round_no: int, gen_no: int, slot_no: int) -> str:
    """run/round/gen/slot 범위 identity — 동일 candidate_id라도 제안마다 구별."""
    _require_nonempty_str(run_id, "run_id")
    _require_non_negative_int(round_no, "round_no")
    _require_non_negative_int(gen_no, "gen_no")
    _require_non_negative_int(slot_no, "slot_no")
    return _prefixed_id(
        ID_PREFIX_CANDIDATE_PASSPORT,
        {"run_id": run_id, "round_no": round_no, "gen_no": gen_no, "slot_no": slot_no},
    )


def compute_feedback_id(
    source_passport_id: str,
    autopsy_kind: str,
    side: str,
    source_result_sha256: str,
    rendered_sha256: str,
) -> str:
    return _prefixed_id(
        ID_PREFIX_FEEDBACK_ENVELOPE,
        {
            "source_passport_id": source_passport_id,
            "autopsy_kind": autopsy_kind,
            "side": side,
            "source_result_sha256": source_result_sha256,
            "rendered_sha256": rendered_sha256,
        },
    )


def compute_consumption_id(
    feedback_id: str, prompt_id: str, target_passport_id: str
) -> str:
    return _prefixed_id(
        ID_PREFIX_FEEDBACK_CONSUMPTION,
        {
            "feedback_id": feedback_id,
            "prompt_id": prompt_id,
            "target_passport_id": target_passport_id,
        },
    )


def compute_manifest_id(
    run_id: str,
    profile: str,
    methodology: str,
    timeframe: str,
    scope: str,
    role: str,
    code_hash: str,
    config_hash: str,
) -> str:
    return _prefixed_id(
        ID_PREFIX_EVALUATION_MANIFEST,
        {
            "run_id": run_id,
            "profile": profile,
            "methodology": methodology,
            "timeframe": timeframe,
            "scope": scope,
            "role": role,
            "code_hash": code_hash,
            "config_hash": config_hash,
        },
    )


def compute_receipt_id(
    run_id: str, phase_id: str, outcome: str, stop_reason: Optional[str]
) -> str:
    return _prefixed_id(
        ID_PREFIX_RUN_RECEIPT,
        {
            "run_id": run_id,
            "phase_id": phase_id,
            "outcome": outcome,
            "stop_reason": stop_reason,
        },
    )


# ---------------------------------------------------------------------
# boundary validators (reject at construction with clear ValueError)
# ---------------------------------------------------------------------

def _require_nonempty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def _require_optional_str(value: Any, name: str) -> Optional[str]:
    if value is None:
        return None
    return _require_nonempty_str(value, name)


def _require_sha256(value: Any, name: str) -> str:
    _require_nonempty_str(value, name)
    if not _SHA256_HEX_RE.match(value):
        raise ValueError(f"{name}_must_be_64_lowercase_hex")
    return value


def _require_id(value: Any, name: str, prefix: str) -> str:
    _require_nonempty_str(value, name)
    if not value.startswith(prefix):
        raise ValueError(f"{name}_wrong_prefix_expected:{prefix}")
    suffix = value[len(prefix):]
    if not _SHA256_HEX_RE.match(suffix):
        raise ValueError(f"{name}_must_be_prefix_plus_64_hex")
    return value


def _require_optional_id(value: Any, name: str, prefix: str) -> Optional[str]:
    if value is None:
        return None
    return _require_id(value, name, prefix)


def _require_non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name}_must_be_int")
    if value < 0:
        raise ValueError(f"{name}_must_be_non_negative")
    return value


def _require_enum_value(value: Any, enum_cls: type, name: str) -> str:
    if isinstance(value, enum_cls):
        return value.value
    if isinstance(value, str):
        try:
            return enum_cls(value).value
        except ValueError:
            raise ValueError(f"{name}_unknown_enum_value:{value!r}")
    raise ValueError(f"{name}_must_be_enum_or_str")


def _require_utc_timestamp(value: Any, name: str) -> str:
    """tz-aware UTC ISO8601 문자열만 허용(naive/local 거부)."""
    _require_nonempty_str(value, name)
    text = value
    parseable = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(parseable)
    except ValueError as exc:
        raise ValueError(f"{name}_invalid_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name}_naive_timestamp_forbidden")
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{name}_must_be_utc_offset_zero")
    return text


def _deep_freeze(value: Any, name: str) -> Any:
    """가변 dict/list -> 불변 MappingProxyType/tuple 재귀 동결. NaN/Inf 거부.

    입력 컨테이너는 항상 새로 복사되므로, 호출자가 구성 이후 원본을 변경해도
    저장된 값에는 영향이 없다.
    """
    if isinstance(value, MappingProxyType) or isinstance(value, MappingABC):
        frozen: dict = {}
        for key, sub_value in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{name}_keys_must_be_str")
            frozen[key] = _deep_freeze(sub_value, f"{name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (set, frozenset)):
        raise ValueError(f"{name}_must_be_ordered_sequence_not_set")
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item, f"{name}[]") for item in value)
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"{name}_must_be_finite")
        return value
    if isinstance(value, (int, str)) or value is None:
        return value
    raise ValueError(f"{name}_unsupported_type:{type(value)!r}")


def _require_mapping(value: Any, name: str) -> MappingProxyType:
    if not (isinstance(value, MappingProxyType) or isinstance(value, MappingABC)):
        raise ValueError(f"{name}_must_be_mapping")
    return _deep_freeze(value, name)


def _require_tuple_of_str(value: Any, name: str) -> Tuple[str, ...]:
    frozen = _deep_freeze(value, name)
    if not isinstance(frozen, tuple):
        raise ValueError(f"{name}_must_be_sequence")
    for item in frozen:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name}_elements_must_be_nonempty_str")
    return frozen


def _require_directive_tuple(value: Any, name: str) -> Tuple[Any, ...]:
    frozen = _deep_freeze(value, name)
    if not isinstance(frozen, tuple):
        raise ValueError(f"{name}_must_be_sequence")
    return frozen


def _thaw(value: Any) -> Any:
    """MappingProxyType/tuple -> plain dict/list (JSON round-trip 복원용)."""
    if isinstance(value, MappingProxyType):
        return {key: _thaw(sub_value) for key, sub_value in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _to_dict(instance: Any) -> dict:
    return {
        field.name: _thaw(getattr(instance, field.name))
        for field in dataclasses.fields(instance)
    }


def _from_dict(cls: type, data: Mapping[str, Any]) -> Any:
    known = {field.name for field in dataclasses.fields(cls)}
    missing = known - set(data)
    if missing:
        raise ValueError(f"{cls.__name__}_missing_fields:{sorted(missing)}")
    kwargs = {key: value for key, value in dict(data).items() if key in known}
    return cls(**kwargs)


# ---------------------------------------------------------------------
# enums (design spec §7)
# ---------------------------------------------------------------------

class CandidateMode(str, enum.Enum):
    SEED = "seed"
    FRESH = "fresh"
    REFINE = "refine"


class FeedbackSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    RISK = "risk"
    ERROR = "error"
    SEGMENT = "segment"
    FEATURE = "feature"
    HYPOTHESIS = "hypothesis"


# ---------------------------------------------------------------------
# schema versions — 필드 추가/의미 변경 시 올린다(hash에 포함되어 구분됨).
# ---------------------------------------------------------------------

CANDIDATE_PASSPORT_SCHEMA = 1
FEEDBACK_ENVELOPE_SCHEMA = 1
FEEDBACK_CONSUMPTION_SCHEMA = 1
EVALUATION_MANIFEST_SCHEMA = 1
RUN_RECEIPT_SCHEMA = 1


# ---------------------------------------------------------------------
# CandidatePassport
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class CandidatePassport:
    """제안된 매수/매도 조건 후보의 불변 신원 증거 (design spec §7).

    ``candidate_id`` 는 내용 정체성(buy/sell sha + methodology/timeframe),
    ``passport_id`` 는 run/round/gen/slot 범위 정체성이다. 두 값은 서로 다른
    identity 축이므로, 동일 candidate_id가 여러 passport_id 아래 제안될 수
    있다(예: 리런/재제안).
    """

    schema: int
    passport_id: str
    candidate_id: str
    run_id: str
    round_no: int
    gen_no: int
    slot_no: int
    parent_passport_id: Optional[str]
    mode: str
    lane: str
    family: str
    timeframe: str
    buy_strategy_name: str
    sell_strategy_name: str
    buy_sha256: str
    sell_sha256: str
    ast_fingerprint: str
    rowset_fingerprint: str
    evidence_ids: Tuple[str, ...]
    threshold_provenance: Mapping[str, Any]
    manifest_id: str
    created_at: str

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "schema", _require_non_negative_int(self.schema, "schema"))
        set_(self, "passport_id", _require_id(self.passport_id, "passport_id", ID_PREFIX_CANDIDATE_PASSPORT))
        set_(self, "candidate_id", _require_id(self.candidate_id, "candidate_id", ID_PREFIX_CANDIDATE))
        set_(self, "run_id", _require_nonempty_str(self.run_id, "run_id"))
        set_(self, "round_no", _require_non_negative_int(self.round_no, "round_no"))
        set_(self, "gen_no", _require_non_negative_int(self.gen_no, "gen_no"))
        set_(self, "slot_no", _require_non_negative_int(self.slot_no, "slot_no"))
        set_(self, "parent_passport_id", _require_optional_id(
            self.parent_passport_id, "parent_passport_id", ID_PREFIX_CANDIDATE_PASSPORT
        ))
        set_(self, "mode", _require_enum_value(self.mode, CandidateMode, "mode"))
        set_(self, "lane", _require_nonempty_str(self.lane, "lane"))
        set_(self, "family", _require_nonempty_str(self.family, "family"))
        set_(self, "timeframe", _require_nonempty_str(self.timeframe, "timeframe"))
        set_(self, "buy_strategy_name", _require_nonempty_str(self.buy_strategy_name, "buy_strategy_name"))
        set_(self, "sell_strategy_name", _require_nonempty_str(self.sell_strategy_name, "sell_strategy_name"))
        set_(self, "buy_sha256", _require_sha256(self.buy_sha256, "buy_sha256"))
        set_(self, "sell_sha256", _require_sha256(self.sell_sha256, "sell_sha256"))
        set_(self, "ast_fingerprint", _require_nonempty_str(self.ast_fingerprint, "ast_fingerprint"))
        set_(self, "rowset_fingerprint", _require_nonempty_str(self.rowset_fingerprint, "rowset_fingerprint"))
        set_(self, "evidence_ids", _require_tuple_of_str(self.evidence_ids, "evidence_ids"))
        set_(self, "threshold_provenance", _require_mapping(self.threshold_provenance, "threshold_provenance"))
        set_(self, "manifest_id", _require_id(self.manifest_id, "manifest_id", ID_PREFIX_EVALUATION_MANIFEST))
        set_(self, "created_at", _require_utc_timestamp(self.created_at, "created_at"))

    def to_dict(self) -> dict:
        return _to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidatePassport":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------
# FeedbackEnvelope
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class FeedbackEnvelope:
    """부검(autopsy) 근거로 생성된 불변 피드백 증거 (design spec §7)."""

    schema: int
    feedback_id: str
    source_passport_id: str
    autopsy_kind: str
    side: str
    source_result_sha256: str
    directives: Tuple[Any, ...]
    rendered_text: str
    rendered_sha256: str
    created_at: str

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "schema", _require_non_negative_int(self.schema, "schema"))
        set_(self, "feedback_id", _require_id(self.feedback_id, "feedback_id", ID_PREFIX_FEEDBACK_ENVELOPE))
        set_(self, "source_passport_id", _require_id(
            self.source_passport_id, "source_passport_id", ID_PREFIX_CANDIDATE_PASSPORT
        ))
        set_(self, "autopsy_kind", _require_nonempty_str(self.autopsy_kind, "autopsy_kind"))
        set_(self, "side", _require_enum_value(self.side, FeedbackSide, "side"))
        set_(self, "source_result_sha256", _require_sha256(self.source_result_sha256, "source_result_sha256"))
        set_(self, "directives", _require_directive_tuple(self.directives, "directives"))
        rendered_text = _require_nonempty_str(self.rendered_text, "rendered_text")
        rendered_sha256 = _require_sha256(self.rendered_sha256, "rendered_sha256")
        expected = text_sha256(rendered_text)
        if rendered_sha256 != expected:
            raise ValueError("rendered_sha256_does_not_match_rendered_text")
        set_(self, "rendered_text", rendered_text)
        set_(self, "rendered_sha256", rendered_sha256)
        set_(self, "created_at", _require_utc_timestamp(self.created_at, "created_at"))

    def to_dict(self) -> dict:
        return _to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FeedbackEnvelope":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------
# FeedbackConsumption
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class FeedbackConsumption:
    """피드백이 특정 prompt/후보에 실제로 소비되었음을 남기는 불변 증거."""

    schema: int
    consumption_id: str
    feedback_id: str
    prompt_id: str
    target_passport_id: str
    created_at: str

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "schema", _require_non_negative_int(self.schema, "schema"))
        set_(self, "consumption_id", _require_id(
            self.consumption_id, "consumption_id", ID_PREFIX_FEEDBACK_CONSUMPTION
        ))
        set_(self, "feedback_id", _require_id(self.feedback_id, "feedback_id", ID_PREFIX_FEEDBACK_ENVELOPE))
        set_(self, "prompt_id", _require_nonempty_str(self.prompt_id, "prompt_id"))
        set_(self, "target_passport_id", _require_id(
            self.target_passport_id, "target_passport_id", ID_PREFIX_CANDIDATE_PASSPORT
        ))
        set_(self, "created_at", _require_utc_timestamp(self.created_at, "created_at"))

    def to_dict(self) -> dict:
        return _to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FeedbackConsumption":
        return _from_dict(cls, data)


# ---------------------------------------------------------------------
# EvaluationManifest
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class EvaluationManifest:
    """공식 평가 실행 환경(profile/data/universe/methodology/...) 불변 동결."""

    schema: int
    manifest_id: str
    run_id: str
    profile: str
    data: str
    universe: str
    methodology: str
    timeframe: str
    scope: str
    session: Any
    period: Any
    capital: Any
    cost: Any
    fill: Any
    role: str
    code_hash: str
    config_hash: str
    created_at: str

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "schema", _require_non_negative_int(self.schema, "schema"))
        set_(self, "manifest_id", _require_id(self.manifest_id, "manifest_id", ID_PREFIX_EVALUATION_MANIFEST))
        set_(self, "run_id", _require_nonempty_str(self.run_id, "run_id"))
        set_(self, "profile", _require_nonempty_str(self.profile, "profile"))
        set_(self, "data", _require_nonempty_str(self.data, "data"))
        set_(self, "universe", _require_nonempty_str(self.universe, "universe"))
        set_(self, "methodology", _require_nonempty_str(self.methodology, "methodology"))
        set_(self, "timeframe", _require_nonempty_str(self.timeframe, "timeframe"))
        set_(self, "scope", _require_nonempty_str(self.scope, "scope"))
        set_(self, "session", _deep_freeze_required(self.session, "session"))
        set_(self, "period", _deep_freeze_required(self.period, "period"))
        set_(self, "capital", _deep_freeze_required(self.capital, "capital"))
        set_(self, "cost", _deep_freeze_required(self.cost, "cost"))
        set_(self, "fill", _deep_freeze_required(self.fill, "fill"))
        set_(self, "role", _require_nonempty_str(self.role, "role"))
        set_(self, "code_hash", _require_sha256(self.code_hash, "code_hash"))
        set_(self, "config_hash", _require_sha256(self.config_hash, "config_hash"))
        set_(self, "created_at", _require_utc_timestamp(self.created_at, "created_at"))

    def to_dict(self) -> dict:
        return _to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvaluationManifest":
        return _from_dict(cls, data)


def _deep_freeze_required(value: Any, name: str) -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{name}_required")
    return _deep_freeze(value, name)


# ---------------------------------------------------------------------
# RunReceipt
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class RunReceipt:
    """단계(phase) go/no-go 결과와 예산 소비의 불변 영수증 (design spec §7)."""

    schema: int
    receipt_id: str
    run_id: str
    phase_id: str
    outcome: str
    stop_reason: Optional[str]
    budget_counters: Mapping[str, Any]
    predecessor_ids: Tuple[str, ...]
    artifact_hashes: Mapping[str, str]
    created_at: str

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "schema", _require_non_negative_int(self.schema, "schema"))
        set_(self, "receipt_id", _require_id(self.receipt_id, "receipt_id", ID_PREFIX_RUN_RECEIPT))
        set_(self, "run_id", _require_nonempty_str(self.run_id, "run_id"))
        set_(self, "phase_id", _require_nonempty_str(self.phase_id, "phase_id"))
        set_(self, "outcome", _require_nonempty_str(self.outcome, "outcome"))
        set_(self, "stop_reason", _require_optional_str(self.stop_reason, "stop_reason"))
        set_(self, "budget_counters", _require_mapping(self.budget_counters, "budget_counters"))
        set_(self, "predecessor_ids", _require_tuple_of_str_allow_empty(
            self.predecessor_ids, "predecessor_ids"
        ))
        artifact_hashes = _require_mapping(self.artifact_hashes, "artifact_hashes")
        for key, value in artifact_hashes.items():
            _require_sha256(value, f"artifact_hashes.{key}")
        set_(self, "artifact_hashes", artifact_hashes)
        set_(self, "created_at", _require_utc_timestamp(self.created_at, "created_at"))

    def to_dict(self) -> dict:
        return _to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RunReceipt":
        return _from_dict(cls, data)


def _require_tuple_of_str_allow_empty(value: Any, name: str) -> Tuple[str, ...]:
    frozen = _deep_freeze(value, name)
    if not isinstance(frozen, tuple):
        raise ValueError(f"{name}_must_be_sequence")
    for item in frozen:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name}_elements_must_be_nonempty_str")
    return frozen
