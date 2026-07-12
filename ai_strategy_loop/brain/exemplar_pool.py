"""생성 few-shot 샘플 풀 — 검증된 우수 전략을 K개 골라 프롬프트에 주입(#67).

배경(사용자 아이디어 #67): 검증된 우수 전략(인간 study / 게이트 통과 조건식)을
AI 생성 프롬프트에 few-shot 샘플로 주면, LLM이 "변수 조합 + 다중 필터 AND 게이팅"의
**구조**를 학습해 과발화/저빈도를 줄이고 시드급 생성 품질에 다가갈 수 있다. 현재까지
시드(Tick_902)만 base_code(refine 출발점)로 주입됐고, "다양한 통과 전략 K개를 few-shot
코드로 주는" 메커니즘은 없었다.

핵심 제약(§3.14 학습 — 맹목 복제 금지):
  - few-shot은 **구조 학습용**이다(변수 조합·필터 게이팅 패턴). 시드 지문 과적합을
    피하려고, 프롬프트(prompt.build_messages)가 "구조/게이팅을 학습하되 변수값·조건을
    그대로 베끼지 말라"고 명시한다. 이 모듈은 그 샘플을 **고르기만** 한다.
  - 다양성: 동일/유사(정규화 AST 해시) 코드를 중복 제거해 단일 시드 반복을 막는다.
  - 게이트 유지: require_filter_gates/require_liquidity_gate reject 게이트는 그대로
    둔다(이 모듈은 게이트를 우회하지 않는다 — 샘플 선택 전용).

설계(부작용 없는 순수 조회 — 엔진 import 없음):
  - source='passing'(기본): loop_runs.db generations에서 gate_passed=1인 buy_name/
    sell_name(kind 매칭)을 모아 loop_strategies.db stockbuy/stocksell에서 코드 조회.
  - source='seed_db': 운영 _database/strategy.db(인간 study 전략) 코드. **읽기 전용**
    (운영 DB에 절대 쓰지 않는다 — SELECT만 한다).
  - timeframe 매칭: 요청 timeframe(min/tick)에서 변수 스코프가 유효한 코드만 채택한다
    (check_variable_scope 재사용). tick 전략을 min 생성에 주면 엔진 exec가 NameError로
    죽으므로, 스코프 위반 샘플은 애초에 제외한다.
  - 길이 상한(_MAX_EXEMPLAR_CHARS): 토큰 폭증 방지로 너무 긴 코드는 제외한다.
  - 무예외: DB 없음/조회 실패/매칭 0개 → 빈 리스트. 어떤 예외도 루프를 막지 않는다.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from ai_strategy_loop.brain.token_check import normalized_ast_hash
from ai_strategy_loop.brain.variable_scope import check_variable_scope

logger = logging.getLogger(__name__)

_VALID_KINDS = ("buy", "sell")
_VALID_TIMEFRAMES = ("min", "tick")
_VALID_SOURCES = ("passing", "seed_db")

# few-shot 샘플 1개의 길이 상한(문자). 너무 긴 코드는 토큰 폭증 → 제외한다.
#   실측 보정: 게이트 통과한 잘-게이트된 매수 전략(8~9 필터 범주 AND 결합)은
#   2348~3836자다 — 이것이 정확히 학습시키고픈 고품질 샘플이라 너무 낮은 상한
#   (예 2000)은 모든 실제 매수 전략을 배제해 기능을 무력화한다. 6000자면 실제 시드급
#   전략을 모두 수용하면서(여유 마진), 병적인 과발화 blob/생성 쓰레기만 차단한다.
_MAX_EXEMPLAR_CHARS = 6000

# 운영 strategy.db(인간 study 전략)의 결정론적 경로. export.PRODUCTION_STRATEGY_DB와
#   동일 의미(repo 루트 _database/strategy.db). 여기서는 **읽기 전용**으로만 연다.
#   .../ai_strategy_loop/brain/exemplar_pool.py → parents[2] = repo 루트.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEED_DB_PATH = _REPO_ROOT / "_database" / "strategy.db"

# --- A-6: seed_db few-shot 우선순위 (2026-07-12 전수검사 보고서 P-6) ---
#   기존에는 테이블 순서 선착순 k개라 항상 같은 study 전략이 선점되고 골드 시드가
#   뽑히지 않았다. 골드(다년 검증)·정본 인간 패밀리를 결정론적으로 우선한다.
#   __AUTO_TMP__ 임시 전략은 few-shot 후보에서 제외한다.
_SEED_DB_EXACT_PRIORITY = (
    "Tick_B_902_905_Update_2", "Tick_S_902_905_Update_2",  # 다년 골드 시드
    "C_T_900_920_U2_B", "C_T_900_920_U2_S",                # 30분 전창 정본
)
_SEED_DB_PREFIX_PRIORITY = ("Tick_", "C_T_", "CSS_V7_", "Min_")
_SEED_DB_EXCLUDE_PREFIXES = ("__AUTO_TMP__",)


def _seed_db_rank(name: str) -> tuple:
    """seed_db 이름의 결정론 우선순위 키(작을수록 먼저). 골드 → 패밀리 → 기타."""
    if name in _SEED_DB_EXACT_PRIORITY:
        return (0, f"{_SEED_DB_EXACT_PRIORITY.index(name):02d}")
    for tier, prefix in enumerate(_SEED_DB_PREFIX_PRIORITY, start=1):
        if name.startswith(prefix):
            return (tier, name)
    return (len(_SEED_DB_PREFIX_PRIORITY) + 1, name)



def _diversity_key(code: str) -> str:
    """다양성 중복 제거용 키. 정규화 AST 해시를 우선, 파싱 불가면 원문 해시 폴백."""
    try:
        return normalized_ast_hash(code)
    except Exception:  # noqa: BLE001 - 파싱 불가 코드는 원문 기준으로만 구분.
        return "raw:" + code.strip()


def _read_codes_from_db(db_path: str, table: str, names: List[str]) -> List[str]:
    """주어진 DB의 (table, names)에서 전략 코드를 names 순서대로 읽어온다.

    code 컬럼은 named 컬럼 "전략코드"를 우선하고, 없으면 위치 컬럼(cols[1])으로
    폴백한다(export._read_strategy_code와 동일 규약 — cp949 garbled 컬럼명 대비).
    조회 실패/없는 이름은 건너뛴다(무예외).
    """
    if not names or not Path(db_path).exists():
        return []
    out: List[str] = []
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if not cols:
            return []
        code_col = "전략코드" if "전략코드" in cols else (cols[1] if len(cols) >= 2 else "전략코드")
        for name in names:
            try:
                row = cur.execute(
                    f'SELECT "{code_col}" FROM {table} WHERE "index" = ?', (name,)
                ).fetchone()
            except sqlite3.OperationalError:
                row = None
            if row and row[0]:
                out.append(row[0])
    finally:
        con.close()
    return out


def _passing_names(runs_db_path: str, kind: str) -> List[str]:
    """loop_runs.db generations에서 gate_passed=1 전략 이름(kind 매칭)을 모은다.

    중복 이름(시드가 여러 run의 gen0으로 반복 등장)은 첫 출현 순서를 유지하며
    제거한다. 최신 run을 앞세우려고 created_at 내림차순으로 정렬한다(다양성 우선).
    """
    if not Path(runs_db_path).exists():
        return []
    col = "buy_name" if kind == "buy" else "sell_name"
    con = sqlite3.connect(runs_db_path)
    try:
        try:
            rows = con.execute(
                f"SELECT {col} FROM generations WHERE gate_passed = 1 "
                f"AND {col} IS NOT NULL ORDER BY created_at DESC, run_id, gen_no"
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        con.close()
    seen: set = set()
    names: List[str] = []
    for (nm,) in rows:
        if nm and nm not in seen:
            seen.add(nm)
            names.append(nm)
    return names


def _seed_db_names(seed_db_path: str, table: str) -> List[str]:
    """운영 _database/strategy.db에서 인간 study 전략 이름(index)을 모은다(읽기 전용)."""
    if not Path(seed_db_path).exists():
        return []
    con = sqlite3.connect(seed_db_path)
    try:
        try:
            rows = con.execute(f'SELECT "index" FROM {table}').fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        con.close()
    return [r[0] for r in rows if r and r[0]]


def select_exemplars(
    *,
    kind: str,
    timeframe: str,
    k: int = 3,
    source: str = "passing",
    db_path: Optional[str] = None,
    runs_db_path: Optional[str] = None,
) -> List[str]:
    """few-shot 코드 샘플을 최대 k개 고른다(검증된 우수 전략, 구조 학습용).

    Args:
        kind: 'buy' | 'sell'. stockbuy/stocksell 및 gate_passed 컬럼 매칭에 쓴다.
        timeframe: 'min' | 'tick'. 이 타임프레임에서 변수 스코프가 유효한 코드만
            채택한다(check_variable_scope). tick 전략을 min 생성에 주면 엔진 exec가
            NameError로 죽으므로 스코프 위반 샘플은 제외한다.
        k: 최대 샘플 수(>=0). 0이거나 음수면 빈 리스트.
        source: 'passing'(기본) — loop_runs.db gate_passed 통과 전략 코드.
                'seed_db' — 운영 _database/strategy.db 인간 study 전략(읽기 전용).
        db_path: 코드를 읽어올 strategy DB 경로(stockbuy/stocksell 보유). None이면
            source별 기본값(passing=bootstrap 루프 DB, seed_db=운영 DB).
        runs_db_path: gate_passed 이름을 읽어올 loop_runs.db 경로(source='passing'만).
            None이면 state.LOOP_RUNS_DB. source='seed_db'면 무시된다.

    Returns:
        few-shot 코드 문자열 리스트(최대 k개). 다양성(정규화 해시) 중복 제거 +
        길이 상한 + timeframe 스코프 유효만. DB 없음/조회 실패/매칭 0개면 빈 리스트.
        어떤 예외도 밖으로 던지지 않는다(루프를 막지 않는 학습 보조 경로).
    """
    if kind not in _VALID_KINDS or timeframe not in _VALID_TIMEFRAMES:
        return []
    if source not in _VALID_SOURCES:
        return []
    if k is None or k <= 0:
        return []

    table = "stockbuy" if kind == "buy" else "stocksell"

    try:
        # 1) 후보 코드 수집(source별 경로).
        if source == "seed_db":
            code_db = str(db_path) if db_path else str(_SEED_DB_PATH)
            names = _seed_db_names(code_db, table)
            # A-6: 임시 전략 배제 + 골드/패밀리 우선 결정론 정렬(선착순 k 폐지).
            names = sorted(
                (n for n in names if not n.startswith(_SEED_DB_EXCLUDE_PREFIXES)),
                key=_seed_db_rank,
            )
            codes = _read_codes_from_db(code_db, table, names)
        else:  # 'passing'
            if db_path:
                code_db = str(db_path)
            else:
                import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415
                code_db = str(bootstrap.LOOP_DB_STRATEGY)
            if runs_db_path:
                rdb = str(runs_db_path)
            else:
                from ai_strategy_loop.controller.state import LOOP_RUNS_DB  # noqa: PLC0415
                rdb = str(LOOP_RUNS_DB)
            names = _passing_names(rdb, kind)
            codes = _read_codes_from_db(code_db, table, names)

        # 2) 필터링(길이 상한 → timeframe 스코프 유효 → 다양성 중복 제거) + cap k.
        selected: List[str] = []
        seen_keys: set = set()
        for code in codes:
            if not code or len(code) > _MAX_EXEMPLAR_CHARS:
                continue
            scope_ok, _ = check_variable_scope(code, timeframe, kind)
            if not scope_ok:
                continue
            key = _diversity_key(code)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            selected.append(code.strip())
            if len(selected) >= k:
                break
        return selected
    except Exception as exc:  # noqa: BLE001 - 학습 보조 경로: 어떤 실패도 루프를 막지 않음.
        logger.info("select_exemplars 실패(무시): %s", exc)
        return []
