"""Research config presets for late-tick and min full-session discovery."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, Sequence, TypedDict, assert_never


class PresetName(StrEnum):
    """Stable CLI values for research preset selection."""

    TICK_LATE_0920_0925 = "tick_late_0920_0925"
    MIN_FULL_0900_1500 = "min_full_0900_1500"


PresetValue = str | int | float | bool | None


class ResearchPreset(TypedDict):
    """Serializable preset payload with metadata plus LoopConfig values."""

    name: str
    description: str
    command_hint: str
    config: dict[str, PresetValue]


@dataclass(frozen=True, slots=True)
class UnknownPresetError(ValueError):
    """Raised when a preset CLI value is not registered."""

    raw: str

    def __str__(self) -> str:
        return f"unknown research preset: {self.raw}"


_COMMON_DISCOVERY: Final[dict[str, PresetValue]] = {
    "provider": "gpt_auth",
    "bt_engine_mode": "warm",
    "bt_scope": "universe",
    "bt_betting": "5",
    "bt_universe_start_time": 90000,
    "bt_warm_engine_count": 32,
    "bt_timeout": 900,
    "bt_warm_run_timeout": 180,
    "max_generations": 15,
    "mdd_cap": 20.0,
    "min_trades": 20,
    "min_daily_trades": 0.05,
    "sparse_positive_prompt_enabled": True,
    "exec_budget_prompt_enabled": True,
    "sell_exec_budget_guard_enabled": True,
    "report_principles_enabled": True,
    # A-2: 차트술사 구조론 핵심 원리 블록 — 연구 프리셋에서만 ON(전역 기본 OFF 유지).
    "structure_principles_prompt_enabled": True,
    # A-3: 정본 연구 프로파일 공통 세트 — 검증된 생성/청산/증거 토글을 연구 lane에서 전부 켠다.
    #   (전역 LoopConfig 기본값은 전부 OFF 유지 — 운영 무변경 불변식 4 준수.)
    "principle_gate_enabled": True,        # CSC-06/07/10 reject 게이트(T4.3)
    "evidence_ledger_enabled": True,       # CL-R04/05 passport/envelope/consumption 원장
    "mdd_control_enabled": True,           # 매도 MDD 억제 최우선 블록
    "exit_edge_feedback_enabled": True,    # edge_ratio 청산 효율 환류
    "dispersion_prompt_enabled": True,     # 분산매매 유도(과발화 억제)
    "dispersion_enabled": True,            # graded 동시보유 분산 보상 항
    "meta_seed_enabled": True,             # P4 누적 메타 인사이트 주입
    "prompt_logging_enabled": True,
    # P3 환류 토글 ON (전역 LoopConfig 기본값은 OFF 유지 — 연구 경로에서만 켠다).
    #   "실행→분석→불필요 구간 제거/임계 제안/가정 판정→재생성" 폐루프를 활성화한다.
    #   안전판: P0b 진짜 재백테 게이트 + FDR(다중검정 보정)이 선택편향을 차단한다.
    "segment_feedback_enabled": True,
    "quantile_feedback_enabled": True,
    "counterfactual_feedback_enabled": True,
    "hypothesis_tracking_enabled": True,
    "feature_importance_feedback_enabled": True,
    "exit_forensics_feedback_enabled": True,
}


def preset_names() -> list[str]:
    """Return stable preset names in CLI display order."""
    return [item.value for item in PresetName]


def preset_payload(name: PresetName | str) -> ResearchPreset:
    """Build a research preset payload without touching runtime state."""
    parsed = _parse_name(name)
    match parsed:
        case PresetName.TICK_LATE_0920_0925:
            return _tick_late_0920_0925()
        case PresetName.MIN_FULL_0900_1500:
            return _min_full_0900_1500()
        case unreachable:
            assert_never(unreachable)


def write_preset(name: PresetName | str, out_path: str | Path) -> Path:
    """Write only the LoopConfig-compatible config JSON for a preset."""
    path = Path(out_path)
    payload = preset_payload(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload["config"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _parse_name(name: PresetName | str) -> PresetName:
    try:
        return PresetName(name)
    except ValueError as exc:
        raise UnknownPresetError(raw=str(name)) from exc


def _tick_late_0920_0925() -> ResearchPreset:
    config: dict[str, PresetValue] = {
        **_COMMON_DISCOVERY,
        "bt_timeframe": "tick",
        "bt_full_start": 20230101,
        "bt_full_end": 20251231,
        "bt_universe_end_time": 93000,
        "time_cap_bucket_generation_enabled": True,
        "time_cap_bucket_end_time": 93000,
        "classification_generation_enabled": True,
        "require_filter_gates": True,
        "min_filter_categories": 5,
        "require_meaningful_time_window": True,
        "segment_fine_time": True,
        "encourage_time_dispersion": True,
        "few_shot_enabled": True,
        "few_shot_source": "seed_db",
        "few_shot_k": 3,
    }
    return {
        "name": PresetName.TICK_LATE_0920_0925.value,
        "description": "tick 09:20~09:25 후반 안정화/재가속 후보 발굴용 프리셋",
        "command_hint": (
            "PYTHONUTF8=1 python -m ai_strategy_loop.controller.loop "
            "--config-json ai_strategy_loop/state/run_tick_late_0920_0925_config.json "
            "--run-id tick_late_0920_0925_<date>"
        ),
        "config": config,
    }


def _min_full_0900_1500() -> ResearchPreset:
    config: dict[str, PresetValue] = {
        **_COMMON_DISCOVERY,
        "bt_timeframe": "min",
        "bt_full_start": 20250401,
        "bt_full_end": 20260228,
        "bt_universe_end_time": 92800,
        "full_session_enabled": True,
        "bt_min_universe_end_time": 150000,
        "require_filter_gates": True,
        "min_filter_categories": 5,
        "require_meaningful_time_window": True,
        # mdd_control/exit_edge는 A-3에서 _COMMON_DISCOVERY로 승격(중복 제거).
        "few_shot_enabled": True,
        "few_shot_source": "seed_db",
        "few_shot_k": 3,
    }
    return {
        "name": PresetName.MIN_FULL_0900_1500.value,
        "description": "min 09:00~15:00 전체 분봉 세션 조건식 발굴용 프리셋",
        "command_hint": (
            "PYTHONUTF8=1 python -m ai_strategy_loop.controller.loop "
            "--config-json ai_strategy_loop/state/run_min_full_0900_1500_config.json "
            "--run-id min_full_0900_1500_<date>"
        ),
        "config": config,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for writing preset config JSON files."""
    parser = argparse.ArgumentParser(
        prog="research_presets",
        description="Write AI strategy-loop research preset configs.",
    )
    parser.add_argument("preset", choices=preset_names())
    parser.add_argument("--out", required=True, help="Output config JSON path.")
    parser.add_argument(
        "--with-metadata",
        action="store_true",
        help="Write metadata and config instead of config-only JSON.",
    )
    args = parser.parse_args(argv)
    payload = preset_payload(args.preset)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body: ResearchPreset | dict[str, PresetValue]
    body = payload if args.with_metadata else payload["config"]
    out_path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[preset] wrote {payload['name']} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
