"""알파 랩 CLI 공통 유틸 — 봉인 검증·날짜 해석·JSON 영수증·로깅 (research-only).

모든 alpha_* CLI는 실행 시작 시 run dir의 preregistration_v1.json 을
.sha256 사이드카 값으로 registry.verify_seal 해야 하며(불일치 시 exit 3),
산출물은 run dir에 JSON 영수증으로 남긴다. 파라미터의 단일 원천은 봉인된
사전등록 문서다 — CLI 플래그는 날짜·경로 선택만 담당한다.

종료 코드: 0 정상 / 2 사용법 오류(argparse) / 3 봉인 불일치·부재 /
4 입력 데이터 부족(전 일자 결측 등).
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from alpha_lab import registry

__all__ = [
    "ANNEX_V3_NAME",
    "DEFAULT_DB_DIR",
    "DEFAULT_RUN_DIR",
    "DEFAULT_RUN_DIR_V2",
    "DEFAULT_RUN_DIR_V3",
    "EXIT_INPUT",
    "EXIT_OK",
    "EXIT_SEAL",
    "LEDGER_NAME",
    "PREREG_NAME",
    "PREREG_V2_NAME",
    "REPO_ROOT",
    "add_date_selection_args",
    "add_run_dir_args",
    "float_list",
    "json_sanitize",
    "load_verified_prereg",
    "mvp_dates",
    "parse_dates",
    "receipt_filename",
    "resolve_dates",
    "setup_logging",
    "spec_float",
    "spec_int",
    "verified_prereg_or_none",
    "write_receipt",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = (
    REPO_ROOT / "docs" / "research" / "condition_research" / "research_runs"
    / "alpha_lab_20260705"
)
DEFAULT_RUN_DIR_V2 = (
    REPO_ROOT / "docs" / "research" / "condition_research" / "research_runs"
    / "alpha_lab_v2_20260706"
)
DEFAULT_RUN_DIR_V3 = (
    REPO_ROOT / "docs" / "research" / "condition_research" / "research_runs"
    / "alpha_lab_v3_20260706"
)
DEFAULT_DB_DIR = REPO_ROOT / "_database"
PREREG_NAME = "preregistration_v1.json"
PREREG_V2_NAME = "preregistration_v2.json"
# v3 파생 패리티 annex — load_verified_prereg(run_dir, ANNEX_V3_NAME)로
# .sha256 사이드카 봉인 검증 후 사용한다(additive).
ANNEX_V3_NAME = "v3_feature_annex.json"
LEDGER_NAME = "n_trials_ledger.jsonl"

EXIT_OK = 0
EXIT_SEAL = 3
EXIT_INPUT = 4

_DATE_RE = re.compile(r"^\d{8}$")


def setup_logging(level_name: str) -> None:
    """루트 로거 레벨/핸들러 구성 — 이미 핸들러가 있으면 레벨만 조정."""
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            stream=sys.stderr,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    root.setLevel(level)


def add_run_dir_args(parser: argparse.ArgumentParser) -> None:
    """--run-dir / --log-level 공통 인자."""
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="사전등록·영수증·원장 run 디렉토리 (기본: 공식 alpha_lab_20260705)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="로그 레벨 (기본 INFO)",
    )


def add_date_selection_args(parser: argparse.ArgumentParser) -> None:
    """--dates(콤마 YYYYMMDD) xor --mvp(사전등록 windows.mvp) — 필수 택1."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dates", help="콤마 구분 YYYYMMDD 목록")
    group.add_argument(
        "--mvp",
        action="store_true",
        help="봉인 사전등록 windows.mvp 일자 사용",
    )


def parse_dates(text: str) -> List[str]:
    """'YYYYMMDD,YYYYMMDD,...' → 검증된 일자 리스트(입력 순서 유지)."""
    dates = [part.strip() for part in str(text).split(",") if part.strip()]
    bad = [d for d in dates if not _DATE_RE.fullmatch(d)]
    if bad or not dates:
        raise ValueError(f"YYYYMMDD 형식이 아닌 일자: {bad or '빈 목록'}")
    return dates


def mvp_dates(prereg: Dict[str, Any]) -> List[str]:
    """사전등록 windows.mvp의 연도 그룹을 키 정렬 순으로 이어붙인다."""
    mvp = prereg.get("windows", {}).get("mvp")
    if not isinstance(mvp, dict) or not mvp:
        raise ValueError("사전등록에 windows.mvp가 없다 — --dates를 사용하라")
    out: List[str] = []
    for key in sorted(mvp):
        out.extend(str(d) for d in mvp[key])
    return out


def resolve_dates(args: argparse.Namespace, prereg: Dict[str, Any]) -> List[str]:
    """--dates xor --mvp 를 일자 리스트로 해석한다(add_date_selection_args 쌍)."""
    if getattr(args, "mvp", False):
        return mvp_dates(prereg)
    return parse_dates(args.dates)


def receipt_filename(value: str) -> str:
    """argparse type — run-dir 안 파일명 강제(경로 구분자 금지, 탈출 방지).

    alpha_dataset_v2의 --receipt-name 검증과 동일 규칙의 공용 헬퍼(additive).
    """
    name = str(value).strip()
    if not name or Path(name).name != name:
        raise argparse.ArgumentTypeError(
            f"경로 구분자 없는 파일명이어야 한다: {value!r}"
        )
    return name


def load_verified_prereg(
    run_dir: Path, prereg_name: str = PREREG_NAME
) -> Tuple[Dict[str, Any], str]:
    """봉인 검증 후 (사전등록 dict, sha256 hex)를 반환한다.

    기대 sha는 '{prereg_name 확장자 제외}.sha256' 사이드카의 첫 토큰이다
    (기본 v1 — v2 CLI 는 prereg_name=PREREG_V2_NAME 로 호출, additive).
    불일치는 registry.SealViolation, 파일 부재는 FileNotFoundError.
    """
    prereg_path = Path(run_dir) / prereg_name
    sidecar = prereg_path.with_suffix(".sha256")
    if not prereg_path.exists() or not sidecar.exists():
        raise FileNotFoundError(
            f"사전등록 또는 사이드카 부재: {prereg_path} / {sidecar}"
        )
    tokens = sidecar.read_text(encoding="utf-8").split()
    if not tokens:
        raise registry.SealViolation(f"빈 sha256 사이드카: {sidecar}")
    expected = tokens[0]
    registry.verify_seal(prereg_path, expected)
    payload = json.loads(prereg_path.read_text(encoding="utf-8"))
    return payload, expected


def verified_prereg_or_none(
    run_dir: Path, logger: logging.Logger, prereg_name: str = PREREG_NAME
) -> Optional[Tuple[Dict[str, Any], str]]:
    """load_verified_prereg의 CLI 래퍼 — 실패 시 error 로그 후 None."""
    try:
        return load_verified_prereg(run_dir, prereg_name)
    except registry.SealViolation as exc:
        logger.error("사전등록 봉인 불일치 — 비정상 종료: %s", exc)
        return None
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("사전등록 적재 실패 — 비정상 종료: %s", exc)
        return None


def json_sanitize(value: Any) -> Any:
    """JSON 직렬화 가능 형태로 재귀 변환(원본 불변).

    - dict: 키 str 강제, '_' 접두(내부) 키 제외.
    - tuple/list/ndarray → list, numpy 스칼라 → 파이썬 스칼라.
    - 비유한 float(nan/inf) → None (엄격 JSON — '측정 불가' 명시).
    """
    if isinstance(value, dict):
        return {
            str(k): json_sanitize(v)
            for k, v in value.items()
            if not str(k).startswith("_")
        }
    if isinstance(value, (list, tuple)):
        return [json_sanitize(v) for v in value]
    if isinstance(value, np.ndarray):
        return [json_sanitize(v) for v in value.tolist()]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        out = float(value)
        return out if math.isfinite(out) else None
    return value


def write_receipt(path: Path, payload: Dict[str, Any]) -> Path:
    """영수증 JSON 기록(sanitize + indent 2 + ensure_ascii=False + 끝 개행)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(
        json_sanitize(payload), ensure_ascii=False, indent=2, allow_nan=False
    )
    target.write_text(body + "\n", encoding="utf-8")
    return target


def spec_int(spec: Dict[str, Any], key: str, default: int) -> int:
    """사전등록 하위 dict에서 int 파라미터를 읽는다(부재 시 봉인 기본값)."""
    value = spec.get(key, default)
    return int(default if value is None else value)


def spec_float(spec: Dict[str, Any], key: str, default: float) -> float:
    """사전등록 하위 dict에서 float 파라미터를 읽는다(부재 시 봉인 기본값)."""
    value = spec.get(key, default)
    return float(default if value is None else value)


def float_list(values: Sequence[Any]) -> List[float]:
    """수치 시퀀스 → float 리스트(층화 빈 경계 등)."""
    return [float(v) for v in values]
