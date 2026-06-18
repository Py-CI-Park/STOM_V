"""TMAP G1 — 템플릿 규격·렌더러 (조건식의 모수화).

템플릿 = 조건 구조(코드)는 고정하고 임계값만 θ 슬롯({name})으로 뚫은 매수/매도 쌍.
JSON 파일로 영속하며, 렌더러는 θ를 채워 실행 가능한 전략 코드를 만든다.

정직성 계약:
  - **identity**: 기본값(θ=defaults) 렌더는 원본 시드 코드와 정확히 같아야 한다
    (템플릿화가 알파를 변형하지 않았음의 보증 — 단위 테스트로 고정).
  - 렌더 결과는 기존 생성 가드(compile/token/scope)를 통과해야 주입된다.

분석/연구 전용 — 엔진·하드게이트 무수정.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """θ 슬롯 하나: 이름·후보값·기본값(원본 시드의 리터럴)."""

    name: str
    values: Tuple[Any, ...]
    default: Any
    side: str = "buy"  # 'buy' | 'sell' — 어느 코드의 슬롯인가(정보용).
    note: str = ""


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    name: str
    timeframe: str
    buy_code: str   # {slot} 플레이스홀더 포함.
    sell_code: str
    params: Tuple[ParamSpec, ...]
    description: str = ""
    source: str = ""  # 원본 시드 이름 등.

    def param(self, name: str) -> ParamSpec:
        for p in self.params:
            if p.name == name:
                return p
        raise KeyError(name)

    def defaults(self) -> Dict[str, Any]:
        return {p.name: p.default for p in self.params}


def load_template(path_or_name: str) -> TemplateSpec:
    """JSON 템플릿을 로드한다. 이름만 주면 내장 templates/ 디렉토리에서 찾는다."""
    path = Path(path_or_name)
    if not path.suffix:
        path = TEMPLATE_DIR / f"{path_or_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    params = tuple(
        ParamSpec(
            name=p["name"], values=tuple(p["values"]), default=p["default"],
            side=p.get("side", "buy"), note=p.get("note", ""),
        )
        for p in data["params"]
    )
    return TemplateSpec(
        name=data["name"], timeframe=data.get("timeframe", "tick"),
        buy_code=data["buy_code"], sell_code=data["sell_code"],
        params=params, description=data.get("description", ""),
        source=data.get("source", ""),
    )


def render(template: TemplateSpec, theta: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """θ를 채워 (매수 코드, 매도 코드)를 만든다. 미지정 슬롯은 기본값."""
    values = template.defaults()
    if theta:
        unknown = set(theta) - set(values)
        if unknown:
            raise KeyError(f"unknown params: {sorted(unknown)}")
        values.update(theta)
    return template.buy_code.format(**values), template.sell_code.format(**values)


def validate_rendered(buy_code: str, sell_code: str, timeframe: str) -> List[str]:
    """렌더 결과를 생성 가드(compile/token/scope/시간무결성)로 검증한다."""
    from ai_strategy_loop.brain.time_integrity import check_time_integrity  # noqa: PLC0415
    from ai_strategy_loop.brain.token_check import check_tokens  # noqa: PLC0415
    from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: PLC0415

    errors: List[str] = []
    for kind, code in (("buy", buy_code), ("sell", sell_code)):
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as exc:
            errors.append(f"{kind} compile: {exc}")
            continue
        ok, msg = check_tokens(code)
        if not ok:
            errors.append(f"{kind} token: {msg}")
        ok, missing = check_variable_scope(code, timeframe, kind)
        if not ok:
            errors.append(f"{kind} scope: {missing}")
        # N4(2026-06-11) — 미래참조 리터럴 인자 정적 차단(θ 렌더가 음수/0
        #   윈도우를 만들 수 있는 유일한 진입점이라 여기서 막는다).
        errors.extend(f"{kind} {e}" for e in check_time_integrity(code))
    return errors


def coordinate_points(
    template: TemplateSpec,
    *,
    params: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """좌표 스윕 포인트: 한 번에 한 슬롯만 후보값으로 바꾸고 나머지는 기본값.

    경향성 지도(변수별 응답 곡선)의 표준 입력이다. 기본값 점(원본 시드)을 맨 앞에
    1회 포함한다(베이스라인). 반환 항목: {"label": "...", "theta": {...},
    "param": 슬롯명 또는 "__default__", "value": 값}.
    """
    target = list(params) if params else [p.name for p in template.params]
    points: List[Dict[str, Any]] = [{
        "label": "TMAP __default__",
        "theta": {},
        "param": "__default__",
        "value": None,
    }]
    for name in target:
        spec = template.param(name)
        for value in spec.values:
            if value == spec.default:
                continue  # 기본값 점은 베이스라인 1회로 충분(중복 평가 방지).
            points.append({
                "label": f"TMAP {name}={value}",
                "theta": {name: value},
                "param": name,
                "value": value,
            })
    return points


def strategy_names(template: TemplateSpec, index: int) -> Tuple[str, str]:
    """스윕 포인트의 loop DB 전략 이름(ASCII)을 만든다."""
    base = f"TMAP_{template.name}_{index:03d}"
    return f"{base}_B", f"{base}_S"


def parse_point_label(label: str) -> Optional[Tuple[str, Optional[float]]]:
    """strategy_gist 라벨('TMAP cap_max=2000' | 'TMAP __default__')을 파싱한다.

    반환 (param, value) — 기본값 점은 ("__default__", None). TMAP 라벨이 아니면 None.
    """
    if not label or not label.startswith("TMAP "):
        return None
    body = label[len("TMAP "):].strip()
    if body == "__default__":
        return "__default__", None
    if "=" not in body:
        return None
    name, _, raw = body.partition("=")
    try:
        return name.strip(), float(raw)
    except ValueError:
        return name.strip(), None


def grid_points(
    template: TemplateSpec, param_a: str, param_b: str
) -> List[Dict[str, Any]]:
    """C6/P1(2026-06-11) — 두 슬롯의 데카르트 격자 좌표(기본점 1 + |A|×|B|).

    1-D 단면(coordinate_points)의 한계(L1 — 상호작용 비가시)를 직접 해소한다:
    두 1-D 고원의 교차점이 실제 '고원 면(mesa)'인지 면으로 측정한다.
    라벨 'TMAP2 a=x|b=y'는 grid_summary가 파싱한다(1-D tendency는 무시 — 공존).
    """
    by_name = {p.name: p for p in template.params}
    for name in (param_a, param_b):
        if name not in by_name:
            raise KeyError(f"unknown grid param: {name}")
    points: List[Dict[str, Any]] = [
        {"label": "TMAP __default__", "param": "__default__", "value": None, "theta": {}}
    ]
    for va in by_name[param_a].values:
        for vb in by_name[param_b].values:
            points.append({
                "label": f"TMAP2 {param_a}={va}|{param_b}={vb}",
                "param": f"{param_a}|{param_b}", "value": None,
                "theta": {param_a: va, param_b: vb},
            })
    return points


def parse_grid_label(label: str) -> Optional[Tuple[str, float, str, float]]:
    """'TMAP2 a=x|b=y' → (a, x, b, y). 격자 라벨이 아니면 None."""
    if not label or not label.startswith("TMAP2 "):
        return None
    body = label[len("TMAP2 "):].strip()
    parts = body.split("|")
    if len(parts) != 2:
        return None
    try:
        a, _, ra = parts[0].partition("=")
        b, _, rb = parts[1].partition("=")
        return a.strip(), float(ra), b.strip(), float(rb)
    except ValueError:
        return None
