"""P5 (2026-06-12) — LLM 템플릿 가설 생성기 (수동 전용).

프롬프트 자산: ai_strategy_loop/brain/prompts/p5_template_hypothesis.md
근거: 시드 DB 안에 제2의 산 없음(M5 실증) — 새 구조 공급원으로 LLM 가설 생성 승인.

주의:
  - 루프 자동 호출 없음(수동 전용).
  - 생성물 llmgen_ 접두 격리 — 시드·비-LLM 템플릿과 명확히 구분.
  - n_trials 합산 대상(tmap_sweep 시 포함됨).
  - 가드(validate_rendered)가 신규 함수 발명/역스캔을 차단한다.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_template_hypothesis \\
      --provider gpt_auth [--dry-run | --write] [--max-retries 1]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401

from ai_strategy_loop.tmap.template import (  # noqa: E402
    TEMPLATE_DIR,
    load_template,
    render,
    validate_rendered,
)

_PROMPTS_DIR = REPO_ROOT / "ai_strategy_loop" / "brain" / "prompts"
_P5_ASSET = _PROMPTS_DIR / "p5_template_hypothesis.md"
# 누적 기각 이력·교훈 컨텍스트(2026-06-12) — 존재하면 프롬프트에 자동 주입.
_LESSONS_PATH = REPO_ROOT / ".omo/evidence/tmap-walkforward/llm_context_failure_lessons.md"

# =====================================================================
# 순수 함수: registry_summary
# =====================================================================

def registry_summary() -> str:
    """ai_strategy_loop/tmap/templates/*.json을 읽어 이름·θ 수·축 이름 요약 반환.

    반환 예:
        seed_902905 (14θ): cap_max, prev_ratio_min, strength_min, ...
        orderflow_f07_ignition (11θ): window_end, cap_max, flat_angle, ...
    """
    lines: List[str] = []
    for path in sorted(TEMPLATE_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = data.get("name", path.stem)
            params = data.get("params", [])
            axes = ", ".join(p["name"] for p in params[:6])
            if len(params) > 6:
                axes += ", ..."
            lines.append(f"{name} ({len(params)}θ): {axes}")
        except Exception:
            lines.append(f"{path.stem} (로드 실패)")
    return "\n".join(lines)


# =====================================================================
# 순수 함수: build_prompt
# =====================================================================

def build_prompt(principles_text: str, registry_summary_text: str,
                 lessons_text: str = "") -> str:
    """P5 프롬프트 자산에 컨텍스트(기존 템플릿 이름·축 요약, 실패 교훈)를 결합.

    Args:
        principles_text: 원리 설명 텍스트 (P5 자산의 {principle_text} 자리).
        registry_summary_text: registry_summary()의 반환값.
        lessons_text: 누적 실패 교훈 문서 본문(있으면 컨텍스트에 추가 —
            기각된 8계열의 응답곡선 교훈을 주입해 같은 벽에 부딪히지 않게 한다).

    Returns:
        LLM에 전달할 완성된 사용자 프롬프트 문자열.
    """
    # P5 자산에서 시스템 프롬프트 본문 추출 (```...``` 블록 안)
    raw = _P5_ASSET.read_text(encoding="utf-8")
    m = re.search(r"```\n(.*?)```", raw, re.DOTALL)
    system_body = m.group(1).strip() if m else raw

    # {principle_text} 슬롯 치환
    filled_system = system_body.replace("{principle_text}", principles_text)

    context_block = (
        "[기존 템플릿 목록 — 구조 중복 금지]\n"
        + registry_summary_text
        + "\n\n"
        "[실패 교훈]\n"
        "임계 이식 금지·구조 차용: 숫자(임계값)를 그대로 복사하면 5/5 음수."
        " 구조(조건 골격)를 가져오되 모든 숫자는 슬롯으로 비워라."
    )
    if lessons_text:
        context_block += "\n\n[누적 기각 이력과 교훈 — 같은 가설 재제출 금지]\n" + lessons_text

    # 출력 스키마 강제(2026-06-12 — 실전 1회차에서 params 누락/문자열 배열
    # 형식 위반 관측): 정확한 JSON 형태를 예시로 못박는다.
    context_block += (
        "\n\n[출력 형식 — 이 JSON 스키마 그대로, 다른 텍스트 금지]\n"
        '{"name": "llmgen_<영문스네이크>", "timeframe": "tick"|"min", '
        '"niche_claim": "<한 줄 가설>", '
        '"buy_template": "<{슬롯} 포함 매수 코드>", '
        '"sell_template": "<{슬롯} 포함 매도 코드>", '
        '"params": [{"name": "slot명", "default": 숫자, "values": [숫자, ...], '
        '"side": "buy"|"sell", "note": "설명"}, ...]}\n'
        "params는 반드시 객체 배열(문자열 배열 금지). buy/sell_template의 모든"
        " {슬롯}은 params에 정의돼야 한다.\n"
        "[신호 밀도 규칙 — 2026-06-12 실측 교훈] and 조건은 10개 이하로 하라."
        " 조건 15개+의 교집합은 기본값에서 신호 0건이었다(생성물 2종 실측)."
        " default는 각 축의 두 번째로 느슨한 값으로 잡아 기본값 렌더가 실제"
        " 신호를 내게 하라 — 엄격화는 스윕 축이 담당한다.\n"
        "[엔진 비용 규칙 — 2026-06-12 실측] 누적초당·누적분당 계열 변수는"
        " 반드시 (N) 윈도우 인자를 붙여라 — 무인자형은 평가 시간 초과(352초"
        " 타임아웃 vs 윈도우형 31초 실측). 거래 빈도를 연속적으로 조절할 수"
        " 있는 축(거래대금 하한 등)을 최소 1개 포함하라(밀도 절벽 완화)."
    )

    return filled_system + "\n\n" + context_block


# =====================================================================
# 엔진 실측 규칙 (2026-06-12 대조실험) — 정적 차단
# =====================================================================

# 반드시 (N) 인자로 호출해야 하는 함수형 변수 — 무인자 사용 시 항상-거짓
# 비교(전 코너 0건, gen3 실측) 또는 평가 시간 초과(352초, gen2 실측).
_FUNC_REQUIRED_NAMES = (
    "호가갭발생", "횡보감지", "거래대금급증", "체결강도급등", "호가하락압력",
    "누적초당매수수량", "누적초당매도수량", "누적분당매수수량", "누적분당매도수량",
    "등락율각도", "이동평균", "최고현재가", "최저현재가", "현재가N",
    "초당거래대금평균", "체결강도평균", "분당거래대금평균",
    "구간호가총잔량비율", "전일비각도", "당일거래대금각도",
)


def _engine_cost_errors(code: str) -> List[str]:
    """엔진 비용·의미 규칙 위반을 정적으로 찾는다 (순수 함수 — 테스트 대상)."""
    errors: List[str] = []
    for name in _FUNC_REQUIRED_NAMES:
        pat = rf"(?<![가-힣A-Za-z0-9_]){re.escape(name)}(?![가-힣A-Za-z0-9_])(?!\s*\()"
        if re.search(pat, code):
            errors.append(
                f"'{name}' 무인자 사용 금지 — 반드시 (N) 인자로 호출"
                " (무인자형은 항상-거짓 비교 또는 평가 시간 초과, 엔진 실측)"
            )
    n_depth_calls = len(re.findall(r"(?:매도|매수)잔량[1-5]\s*\(", code))
    if n_depth_calls > 2:
        errors.append(
            f"잔량i(N) 호출형 {n_depth_calls}회 — 2회 초과 금지(잔량 5단 호출"
            " 10회만으로 300초 초과 실측). bare(현재값) 또는 잔량iN(1)"
            " 시프트형을 사용하라"
        )
    return errors


# =====================================================================
# 순수 함수: validate_hypothesis
# =====================================================================

def validate_hypothesis(payload: Dict[str, Any]) -> List[str]:
    """LLM 출력 payload를 검증한다.

    payload 형식:
        {
          "name": "llmgen_...",
          "buy_template": "...",   # {slot} 포함 매수 코드
          "sell_template": "...",  # {slot} 포함 매도 코드
          "params": [
            {"name": ..., "default": ..., "values": [...], "side": ..., "note": ...}
          ]
        }

    검증 규칙:
        1. 필수 키 존재: name, buy_template, sell_template, params.
        2. name이 "llmgen_" 접두로 시작해야 한다.
        3. params 각 항목에 name, default, values, side, note 필요.
        4. 기본값 렌더 + 각 축 별 전 후보값 렌더를 validate_rendered로 검증
           (build_f07_template.py와 같은 깔때기).
        5. timeframe(선택, 기본 "tick")은 "tick"|"min"만 허용 — min이면
           분당 변수 스코프로 검증된다(2026-06-12: min 15:19 세션 지원).
        6. [엔진 실측 규칙 — 2026-06-12 대조실험으로 확정]
           (a) 함수형 변수의 무인자 사용 금지: 호가갭발생·누적초당X 등을
               괄호 없이 식에 쓰면 항상-거짓 비교(전 코너 0건) 또는 평가
               시간 초과(352초)가 된다 — 정적 차단.
           (b) 잔량i(N) 호출형 다수 사용 금지: 잔량 5단 호출 10회만으로
               300초 초과 실측 — bare(현재값) 또는 잔량iN(1) 시프트형만.

    Returns:
        오류 문자열 목록. 빈 리스트 = 통과.
    """
    errors: List[str] = []

    # 1) 필수 키 존재
    required_keys = {"name", "buy_template", "sell_template", "params"}
    missing = required_keys - set(payload.keys())
    if missing:
        errors.append(f"필수 키 누락: {sorted(missing)}")
        return errors  # 이후 검증 불가

    name = payload["name"]
    buy_tmpl = payload["buy_template"]
    sell_tmpl = payload["sell_template"]
    params = payload["params"]
    timeframe = payload.get("timeframe", "tick")
    if timeframe not in ("tick", "min"):
        errors.append(f"timeframe '{timeframe}' 불허 — 'tick'|'min'만 허용")
        return errors

    # 타입 가드 (2026-06-12 — 실전 LLM 출력이 params를 문자열 배열로 보내
    # AttributeError 크래시를 낸 실사고의 근본 수정): 형식 위반은 크래시가
    # 아니라 피드백 가능한 오류 문자열이어야 재생성 루프가 교정할 수 있다.
    if not isinstance(name, str) or not isinstance(buy_tmpl, str) \
            or not isinstance(sell_tmpl, str):
        errors.append("name/buy_template/sell_template은 문자열이어야 함")
        return errors
    if not isinstance(params, list) or not all(isinstance(p, dict) for p in params):
        errors.append(
            "params는 객체 배열이어야 함 — 각 항목: "
            '{"name": str, "default": num, "values": [num...], "side": "buy"|"sell", "note": str}'
        )
        return errors

    # 2) llmgen_ 접두 검사
    if not name.startswith("llmgen_"):
        errors.append(
            f"name '{name}'이 'llmgen_' 접두로 시작하지 않음 "
            "(생성물 격리 규칙 위반)"
        )

    # 3) params 각 항목 키 검사
    param_required = {"name", "default", "values", "side", "note"}
    for i, p in enumerate(params):
        missing_p = param_required - set(p.keys())
        if missing_p:
            errors.append(f"params[{i}] 필수 키 누락: {sorted(missing_p)}")

    # 엔진 실측 규칙 (정적 — 렌더 전 원문 텍스트에서 검사)
    errors.extend(_engine_cost_errors(buy_tmpl))
    errors.extend(_engine_cost_errors(sell_tmpl))

    # 오류가 이미 있으면 렌더 검증 전에 반환 (포맷 오류 있으면 렌더가 터짐)
    if errors:
        return errors

    # 4) 전 좌표 렌더 검증 (build_f07 깔때기와 동일)
    defaults = {p["name"]: p["default"] for p in params}

    # 4a) 기본값 렌더
    try:
        buy_rendered = buy_tmpl.format(**defaults)
        sell_rendered = sell_tmpl.format(**defaults)
    except (KeyError, ValueError) as exc:
        errors.append(f"기본값 렌더 실패: {exc}")
        return errors

    render_errors = validate_rendered(buy_rendered, sell_rendered, timeframe)
    for e in render_errors:
        errors.append(f"기본값 렌더 가드: {e}")

    # 4b) 축별 전 후보값 렌더
    for p in params:
        for v in p["values"]:
            theta = {**defaults, p["name"]: v}
            try:
                b = buy_tmpl.format(**theta)
                s = sell_tmpl.format(**theta)
            except (KeyError, ValueError) as exc:
                errors.append(f"{p['name']}={v} 렌더 실패: {exc}")
                continue
            for e in validate_rendered(b, s, timeframe):
                errors.append(f"{p['name']}={v} 가드: {e}")

    return errors


# =====================================================================
# JSON 파싱 헬퍼 (코드펜스 허용)
# =====================================================================

def _parse_json_from_text(text: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON을 추출한다. 코드펜스(```json ... ```)가 있으면 제거."""
    # 코드펜스 제거
    stripped = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped.strip())
    return json.loads(stripped)


# =====================================================================
# main
# =====================================================================

def main(
    *,
    llm_fn: Optional[Callable[[str], str]] = None,
    argv: Optional[List[str]] = None,
) -> int:
    """템플릿 가설 생성 엔트리포인트.

    Args:
        llm_fn: 의존성 주입용 LLM 호출 함수 (prompt: str) -> raw_text: str.
                None이면 --provider 인자로 실제 provider를 생성해 사용.
                테스트에서는 고정 JSON을 반환하는 가짜 함수를 주입한다.
        argv: 명령행 인자 (None이면 sys.argv).

    Returns:
        종료 코드 (0=성공, 1=실패).
    """
    parser = argparse.ArgumentParser(
        prog="gen_template_hypothesis",
        description="P5 LLM 템플릿 가설 생성기 (수동 전용 — 루프 자동 호출 없음)",
    )
    parser.add_argument(
        "--provider", type=str, default="gpt_auth",
        choices=["gpt_auth", "openrouter", "codex_proxy"],
        help="LLM provider (기본: gpt_auth)",
    )
    mode_grp = parser.add_mutually_exclusive_group()
    mode_grp.add_argument(
        "--dry-run", dest="dry_run", action="store_true", default=True,
        help="검증 리포트만 출력, 파일 미저장 (기본)",
    )
    mode_grp.add_argument(
        "--write", dest="dry_run", action="store_false",
        help="검증 통과 시 templates/<name>.json 저장",
    )
    parser.add_argument(
        "--max-retries", type=int, default=1,
        help="검증 실패 시 최대 재생성 횟수 (기본: 1)",
    )
    parser.add_argument(
        "--principles", type=str,
        default="오더플로우 원리: 거래대금·체결강도·잔량 흡수의 조합으로 단기 방향성을 잡는다.",
        help="원리 설명 텍스트 ({principle_text} 슬롯에 삽입)",
    )

    args = parser.parse_args(argv)

    # LLM 함수 준비
    if llm_fn is None:
        llm_fn = _make_provider_fn(args.provider)
        if llm_fn is None:
            print("[ERROR] provider 초기화 실패", file=sys.stderr)
            return 1

    reg_summary = registry_summary()
    lessons = ""
    if _LESSONS_PATH.is_file():
        lessons = _LESSONS_PATH.read_text(encoding="utf-8")
    prompt_text = build_prompt(args.principles, reg_summary, lessons_text=lessons)

    last_errors: List[str] = []
    payload: Optional[Dict[str, Any]] = None

    for attempt in range(1, args.max_retries + 2):  # +2: 초기 1회 + max_retries 회
        # 피드백 포함 프롬프트 구성
        if attempt == 1:
            user_prompt = prompt_text
        else:
            feedback = "\n".join(f"- {e}" for e in last_errors)
            user_prompt = (
                prompt_text
                + f"\n\n[이전 시도 검증 오류 — 반드시 수정]\n{feedback}"
            )

        # LLM 호출
        try:
            raw_text = llm_fn(user_prompt)
        except Exception as exc:
            print(f"[ERROR] LLM 호출 실패: {exc}", file=sys.stderr)
            return 1

        # JSON 파싱
        try:
            payload = _parse_json_from_text(raw_text)
        except json.JSONDecodeError as exc:
            last_errors = [f"JSON 파싱 실패: {exc}"]
            print(f"[시도 {attempt}] JSON 파싱 오류: {exc}")
            if attempt >= args.max_retries + 1:
                break
            continue

        # 검증
        last_errors = validate_hypothesis(payload)
        if not last_errors:
            break  # 통과
        print(f"[시도 {attempt}] 검증 실패 ({len(last_errors)}개 오류):")
        for e in last_errors:
            print(f"  - {e}")
        if attempt >= args.max_retries + 1:
            break

    # 결과 처리
    if last_errors or payload is None:
        print("\n[FAIL] 최종 검증 실패. 파일 저장 안 함.")
        return 1

    name = payload["name"]
    print(f"\n[PASS] 검증 통과: {name}")
    print(f"  params: {len(payload['params'])}θ")

    if args.dry_run:
        print("[dry-run] 파일 저장 생략. 검증 리포트:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    # --write: 저장 + 재로드 identity 확인
    out_path = TEMPLATE_DIR / f"{name}.json"
    spec = {
        "name": name,
        "timeframe": payload.get("timeframe", "tick"),
        "source": "P5 LLM 가설 생성 (gen_template_hypothesis)",
        "description": payload.get("niche_claim", ""),
        "buy_code": payload["buy_template"],
        "sell_code": payload["sell_template"],
        "params": payload["params"],
    }
    out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[저장] {out_path}")

    # 재로드 identity 확인
    rebuilt = load_template(name)
    defaults = {p["name"]: p["default"] for p in payload["params"]}
    b_orig = payload["buy_template"].format(**defaults)
    s_orig = payload["sell_template"].format(**defaults)
    b_rebuilt, s_rebuilt = render(rebuilt)
    if b_orig != b_rebuilt or s_orig != s_rebuilt:
        print("[ERROR] 재로드 identity 실패 — 저장 파일과 원본 불일치", file=sys.stderr)
        return 1
    print("[OK] 재로드 identity 확인 완료")
    return 0


def _make_provider_fn(provider_name: str) -> Optional[Callable[[str], str]]:
    """provider 이름으로 실제 LLM 호출 함수를 만든다.

    반환: (prompt: str) -> raw_text: str
    generator.py의 provider.chat() 경로를 재사용한다(인증/호출 로직 중복 없음).
    gpt_auth면 루프(_loop.py)와 동일하게 OAuth 로컬 프록시를 직접 기동한다
    (2026-06-12 수정 — 종전엔 프록시 기동 누락으로 연결 거부 실사고).
    """
    from ai_strategy_loop.provider.factory import make_provider  # noqa: PLC0415

    if provider_name == "gpt_auth":
        import atexit  # noqa: PLC0415

        from ai_strategy_loop.provider.chatgpt_oauth import (  # noqa: PLC0415
            clear_env,
            inject_env,
            start_proxy_sync,
            stop_proxy_sync,
        )

        inject_env()
        if not start_proxy_sync():
            clear_env()
            print("[ERROR] gpt_auth 프록시 시작 실패", file=sys.stderr)
            return None

        def _cleanup() -> None:
            try:
                stop_proxy_sync()
            finally:
                clear_env()

        atexit.register(_cleanup)

    class _FakeConfig:
        provider = provider_name

    try:
        prov = make_provider(_FakeConfig())
    except Exception as exc:
        print(f"[ERROR] provider 생성 실패: {exc}", file=sys.stderr)
        return None

    def _call(prompt: str) -> str:
        result = prov.chat([
            {"role": "system", "content": "너는 STOM 전략 템플릿 설계자다."},
            {"role": "user", "content": prompt},
        ])
        return getattr(result, "text", "") or ""

    return _call


if __name__ == "__main__":
    raise SystemExit(main())
