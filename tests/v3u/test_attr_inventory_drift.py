"""V3U attr inventory drift 회귀 차단 (재발 방지 §5-1+§5-2).

scripts/v3u_attr_inventory_diff.py를 통해 2U 추론 노하우 + V3 외부 참조 + V3U init
3-way diff을 측정하고, baseline을 초과하는 새 CRITICAL drift가 추가되면 fail.

baseline 정책: 사이클 N 시작 시점의 CRITICAL 수를 보수적으로 고정한다. 사이클 진행 중
CRITICAL 줄어들면 baseline도 함께 감소시켜 회귀 안전망을 점진적으로 강화한다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DIFF_SCRIPT = _REPO_ROOT / "scripts" / "v3u_attr_inventory_diff.py"
# 2026-05-21 사이클 6 A2 완료 시점 baseline: 0 measured (filter 보강 + 5건 fix +
# setattr/메서드 추출 패턴 추가). 새 외부 참조 추가 시 즉시 fail하는 strict 모드.
# 향후 외부 V3 코드가 새 ui.X 추가 시 1~2건의 여유 허용 가능하나 사이클 6 종료 시점에는
# 0을 유지. drift 발생 시 _CRITICAL_BASELINE_MAX 조정 + LESSONS.md §6에 결함 기록.
_CRITICAL_BASELINE_MAX = 0


def _run_diff_tool(tmp_path: Path) -> dict:
    import json

    # tmp_path는 repo 외부 디렉토리. 도구 출력은 repo 내 .omx/logs/v3u/test_*.json 사용
    out_rel = f".omx/logs/v3u/test_attr_inventory_{tmp_path.name}.json"
    output_abs = _REPO_ROOT / out_rel
    output_abs.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(_DIFF_SCRIPT), "--output", out_rel],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"v3u_attr_inventory_diff.py 비정상 종료 (exit={result.returncode}):\n"
        f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    assert output_abs.is_file(), f"출력 JSON 누락: {output_abs}"
    return json.loads(output_abs.read_text(encoding="utf-8"))


def test_attr_inventory_diff_tool_runnable(tmp_path) -> None:
    """도구 자체가 실행 가능하고 JSON 출력 정상."""
    payload = _run_diff_tool(tmp_path)
    assert "summary" in payload
    assert "diff" in payload
    assert payload["sources"]["v3u_init_count"] > 100  # 최소 100개 attr init
    assert payload["sources"]["v3_external_count"] > 500  # 외부 ref 500개 이상


def test_critical_drift_within_baseline(tmp_path) -> None:
    """V3 external이 참조하나 V3U init/widget builder에 없는 CRITICAL drift가
    baseline 이내. baseline을 넘으면 새 누락 발생 신호 → 4단계 워크플로우 발동.

    baseline 초과 시 조치:
    1. `python scripts/v3u_attr_inventory_diff.py` 실행 후 .omx/logs/v3u/attr_inventory_diff.json 확인
    2. critical[] 항목 중 진짜 결함은 ui/main_window.py에 init 추가
    3. false positive(위젯 등)는 filter 패턴 보강
    4. baseline 갱신 (_CRITICAL_BASELINE_MAX) 후 LESSONS.md §7 통계 갱신
    """
    payload = _run_diff_tool(tmp_path)
    critical_count = payload["summary"]["critical_count"]
    critical_items = payload["diff"]["critical"]
    assert critical_count <= _CRITICAL_BASELINE_MAX, (
        f"CRITICAL drift {critical_count} > baseline {_CRITICAL_BASELINE_MAX}.\n"
        f"신규 누락 attr 예시 (상위 10):\n"
        + "\n".join(f"  - {a}" for a in critical_items[:10])
        + f"\n전체 목록: .omx/logs/v3u/attr_inventory_diff.json"
    )


def test_known_critical_attrs_in_baseline(tmp_path) -> None:
    """이전 사이클에서 발견된 핵심 결함 attr이 이미 init되어 baseline에 없는지 확인.

    backengine_starting, back_tick_cunsum, draw_homechart, update_crawling_data 등은
    사이클 1·5에서 모두 fix 완료. CRITICAL 목록에 다시 나타나면 회귀.
    """
    payload = _run_diff_tool(tmp_path)
    critical_set = set(payload["diff"]["critical"])
    must_not_be_critical = {
        "self.backengine_starting",
        "self.back_tick_cunsum",
        "self.draw_homechart",
        "self.draw_home_chart",
        "self.update_crawling_data",
        "self.update_telegram_msg",
        "self.process_kill",
        "self.webc",
    }
    regressed = critical_set & must_not_be_critical
    assert not regressed, (
        f"이전에 fix된 attr이 CRITICAL drift로 회귀: {sorted(regressed)}. "
        f"LESSONS.md §6의 결함 #{1, 2, 7, 8, 9, 10}을 다시 확인."
    )
