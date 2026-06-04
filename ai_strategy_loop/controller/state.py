"""US-005 Phase 2b — 루프 상태 영속 (SQLite WAL + JSON 스냅샷).

`ai_strategy_loop/state/loop_runs.db`를 WAL 모드로 열어 run/generation을
기록한다. WAL을 쓰는 이유: 헤드리스 루프가 한 세대를 쓰는 동안 별도 프로세스
(모니터/대시보드 등)가 락 에러 없이 동시에 읽을 수 있어야 하기 때문이다.

세대마다 JSON 스냅샷을 `ai_strategy_loop/state/snapshots/`에 떨군다 — DB가
깨져도 사람이 읽을 수 있는 진행 기록을 남기기 위한 단순 안전장치다.

resume 계약: 같은 run_id를 다시 열면 마지막 완료 세대 다음부터 이어간다.
세대 번호는 절대 중복되지 않는다(같은 (run_id, gen_no)는 UPSERT).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 패키지 루트 (.../ai_strategy_loop)
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_STATE_DIR = _PACKAGE_DIR / "state"
_SNAPSHOT_DIR = _STATE_DIR / "snapshots"
LOOP_RUNS_DB = _STATE_DIR / "loop_runs.db"

# generations 테이블의 현재 스키마 버전 (P3 연구 파이프라인).
#   ALTER 누적을 버전으로 관리한다 — 기존 DB는 _migrate_schema에서 누락 컬럼만
#   멱등하게 보강하고 schema_meta에 현재 버전을 기록한다. 새 DB는 처음부터 v3다.
#     v1: mdd/profit/strategy_gist (legacy — schema_meta 없던 시절).
#     v2: parent_gen(계보), diff_from_parent(변경 요약) 추가.
#     v3: total_profit_pct(수익률 %) 추가 — 대시보드 세대 이력/차트(P10)가 표시한다.
#     v4: daily_avg_trades(일평균거래횟수) 추가 — 빈도 게이트 주 기준을 이력/대시보드에 표시.
#     v5: payoff_ratio(손익비), give_back_rate(기회 반납률) 추가 — 청산 품질 대시보드 노출.
#     v6: dispersion_term(다종목 분산 보상항), max_hold_count(최대 동시보유 종목 수) 추가
#         — R8 품질지표 LIVE 노출(GradedResult에서 전파). calmar/uptrend_r2는 v1부터 존재.
#     v7: prompts 테이블 신규(generations 컬럼 변경 없음) — P1c 프롬프트 영속화(재현성).
#         LLM 호출별 프롬프트(system 해시+user 전문+주입 피처+토큰/응답 해시)를 옵트인
#         토글로 기록. CREATE TABLE IF NOT EXISTS라 구버전 DB도 안전(하위호환).
#     v8: 부모 대비 숫자 델타 컬럼(P1b, diff_from_parent의 SQL 조회가능 형태) 추가.
#     v9: hypotheses_json 컬럼(P2a) 추가 — 이 세대가 검증한 가정+판정 직렬화.
#         직전 세대 부검이 세운 가정을 이 세대의 부모 대비 델타로 채택/기각한 결과를
#         JSON 리스트로 영속한다(추가 백테 없음). NULL 기본(부모 없는 세대·토글 OFF).
#     v10: equity_points 테이블 신규(generations 컬럼 변경 없음) — 백테 시계열 영속(O2).
#         per-trade CSV에서 다운샘플한 누적수익곡선·일별손익·낙폭을 (run_id,gen_no)별로
#         영속해 CSV 삭제 후에도 곡선을 보존하고 SQL 분석을 가능케 한다. CREATE TABLE
#         IF NOT EXISTS라 구버전 DB도 안전(하위호환). 옵트인 토글(기본 OFF).
SCHEMA_VERSION = 10

# US-007 — 루프↔대시보드 라이브 상태 파일 + 정지 플래그 파일.
#   current_state.json : 루프가 매 세대/백테스트 시점에 atomic write 하는
#                        LoopState 스냅샷(contract.py). 대시보드가 폴링/푸시한다.
#   STOP               : 대시보드가 쓰는 정지 플래그. 루프가 세대 시작 전 확인.
CURRENT_STATE_FILE = _STATE_DIR / "current_state.json"
STOP_FLAG_FILE = _STATE_DIR / "STOP"


def _now() -> float:
    return time.time()


class LoopState:
    """루프 run/generation 영속 저장소 (WAL SQLite + JSON 스냅샷).

    하나의 LoopState 인스턴스는 하나의 DB 파일 연결을 소유한다. 기본 경로는
    LOOP_RUNS_DB이며, 테스트는 tmp 경로를 주입할 수 있다.
    """

    def __init__(self, db_path: Optional[str] = None, snapshot_dir: Optional[str] = None):
        self.db_path = str(db_path or LOOP_RUNS_DB)
        self.snapshot_dir = str(snapshot_dir or _SNAPSHOT_DIR)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.snapshot_dir).mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: 프록시/엔진이 별도 스레드를 쓰더라도 동일
        #   연결을 안전하게 재사용(루프는 단일 스레드 순차 기록이라 경합 없음).
        self._con = sqlite3.connect(self.db_path, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        # WAL 모드 — 동시 reader 비차단. journal_mode는 영구 설정이다.
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    # ------------------------------------------------------------------
    # 스키마
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        self._con.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                started_at  REAL,
                config_json TEXT,
                status      TEXT,
                best_gen    INTEGER,
                best_score  REAL,
                finished_at REAL
            );
            CREATE TABLE IF NOT EXISTS generations (
                run_id      TEXT,
                gen_no      INTEGER,
                buy_name    TEXT,
                sell_name   TEXT,
                status      TEXT,
                score       REAL,
                calmar      REAL,
                uptrend_r2  REAL,
                gate_passed INTEGER,
                reason      TEXT,
                csv_path    TEXT,
                trade_count INTEGER,
                mdd         REAL,
                profit      REAL,
                strategy_gist TEXT,
                created_at  REAL,
                PRIMARY KEY (run_id, gen_no)
            );
            CREATE TABLE IF NOT EXISTS schema_meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS prompts (
                prompt_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id       TEXT,
                gen_no       INTEGER,
                kind         TEXT,
                attempt      INTEGER,
                system_sha   TEXT,
                user_text    TEXT,
                user_sha     TEXT,
                injected_features TEXT,
                prior_error  TEXT,
                model        TEXT,
                prompt_tokens     INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                response_sha TEXT,
                created_at   REAL
            );
            CREATE INDEX IF NOT EXISTS idx_prompts_run_gen ON prompts(run_id, gen_no);
            CREATE TABLE IF NOT EXISTS equity_points (
                run_id      TEXT,
                gen_no      INTEGER,
                t_index     INTEGER,
                date        INTEGER,
                daily_pnl   REAL,
                cum_profit  REAL,
                cum_pct     REAL,
                drawdown    REAL,
                PRIMARY KEY (run_id, gen_no, t_index)
            );
            CREATE INDEX IF NOT EXISTS idx_equity_run_gen ON equity_points(run_id, gen_no);
            """
        )
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """generations 스키마를 현재 SCHEMA_VERSION까지 멱등하게 올린다.

        CREATE TABLE IF NOT EXISTS는 이미 존재하는 테이블의 컬럼을 추가하지
        못하므로, 누락 컬럼을 PRAGMA table_info로 탐지해 ADD COLUMN 한다. 이미
        있는 컬럼은 건너뛰므로(멱등) 같은 DB를 여러 번 열어도 안전하다. 마지막에
        schema_meta에 현재 버전을 기록해 ALTER 누적을 버전으로 추적한다.

        기존 DB(구버전 loop_runs.db) 호환:
          - mdd/profit/strategy_gist 누락(v1 이전) → 추가(INSERT 실패 방지).
          - parent_gen/diff_from_parent 누락(v2 이전) → 추가(P3 계보/diff).
          - total_profit_pct 누락(v3 이전) → 추가(P10 수익률 %).
          - daily_avg_trades 누락(v4 이전) → 추가(빈도 게이트 주 기준).
          - payoff_ratio/give_back_rate 누락(v5 이전) → 추가(청산 품질 대시보드 노출).
          - dispersion_term/max_hold_count 누락(v6 이전) → 추가(R8 다종목 분산 LIVE 노출).
          - d_graded..d_uptrend_r2 누락(v8 이전) → 추가(P1b 부모 대비 숫자 델타).
          - hypotheses_json 누락(v9 이전) → 추가(P2a 가정+판정 직렬화).
        새 컬럼은 모두 NULL/명시 기본이라 기존 행의 의미를 바꾸지 않는다(하위호환).
        """
        existing_cols = {row[1] for row in self._con.execute("PRAGMA table_info(generations)")}
        # (컬럼, 선언) — 순서대로 누락분만 추가한다. 새 버전의 컬럼을 여기 가산한다.
        for col, decl in (
            ("mdd", "REAL"),            # v1
            ("profit", "REAL"),          # v1
            ("strategy_gist", "TEXT"),   # v1
            ("parent_gen", "INTEGER"),   # v2 — 계보(이 세대가 개선한 부모 세대).
            ("diff_from_parent", "TEXT"),  # v2 — 부모 대비 변경 요약(NL).
            ("total_profit_pct", "REAL"),  # v3 — 수익률(총수익률, %). 대시보드 표시용.
            ("daily_avg_trades", "REAL"),  # v4 — 일평균거래횟수. 빈도 게이트 주 기준.
            ("payoff_ratio", "REAL"),      # v5 — 손익비(평균이익/abs(평균손실)). 청산 품질.
            ("give_back_rate", "REAL"),    # v5 — 기회 반납률(MFE 도달 후 손실 비율). 청산 품질.
            # v6 — R8 다종목 분산 LIVE 노출(GradedResult.dispersion_term/max_hold_count).
            #   dispersion_term은 보상항(중립=1.0)이라 DEFAULT 1.0으로 ADD해 기존 행도 중립값으로
            #   백필한다(ALTER ADD COLUMN DEFAULT는 기존 행을 NULL이 아닌 지정값으로 채운다).
            #   max_hold_count는 DEFAULT 0.0으로 백필. 두 컬럼 모두 기존 행의 의미를 바꾸지 않는다.
            ("dispersion_term", "REAL DEFAULT 1.0"),
            ("max_hold_count", "REAL DEFAULT 0.0"),
            # v8 — P1b 부모 대비 숫자 델타(diff_from_parent의 SQL 조회가능 형태).
            #   DEFAULT 없음 → NULL. 부모 없는 세대(시드/gen0/fresh)·기존 행은 NULL(하위호환).
            #   meta/analyze가 NL 빈도 대신 AVG/ORDER BY로 트렌드를 집계할 수 있다.
            ("d_graded", "REAL"),
            ("d_mdd", "REAL"),
            ("d_trades", "REAL"),
            ("d_profit", "REAL"),
            ("d_daily_trades", "REAL"),
            ("d_calmar", "REAL"),
            ("d_uptrend_r2", "REAL"),
            # v9 — P2a 가정+판정 직렬화(이 세대가 검증한 직전 가정 리스트의 JSON).
            #   DEFAULT 없음 → NULL. 부모 없는 세대·토글 OFF·기존 행은 NULL(하위호환).
            ("hypotheses_json", "TEXT"),
        ):
            if col not in existing_cols:
                self._con.execute(f"ALTER TABLE generations ADD COLUMN {col} {decl}")
        # 현재 스키마 버전 기록(멱등 UPSERT).
        self._con.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._con.commit()

    def get_schema_version(self) -> int:
        """현재 DB의 schema_version을 읽는다(없으면 0 = 마이그레이션 전 legacy)."""
        try:
            row = self._con.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
        except sqlite3.OperationalError:
            return 0
        if row is None or row[0] is None:
            return 0
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # run 라이프사이클
    # ------------------------------------------------------------------
    def start_run(self, config: Any, run_id: Optional[str] = None) -> str:
        """새 run을 시작하고 run_id를 반환한다.

        run_id 미지정 시 타임스탬프 기반으로 생성한다. config는 to_dict()가
        있으면 그것을, 없으면 dict로 직렬화한다.
        """
        rid = run_id or f"run_{int(_now())}"
        config_json = json.dumps(_config_to_dict(config), ensure_ascii=False)
        self._con.execute(
            "INSERT OR REPLACE INTO runs "
            "(run_id, started_at, config_json, status, best_gen, best_score, finished_at) "
            "VALUES (?, ?, ?, 'running', NULL, NULL, NULL)",
            (rid, _now(), config_json),
        )
        self._con.commit()
        return rid

    def resume_or_start(self, config: Any, run_id: Optional[str] = None) -> str:
        """run_id가 이미 있으면 재개(상태 running 복원), 없으면 새로 시작한다.

        재개 시 config_json은 기존 값을 보존한다(원래 실행 설정 유지).
        """
        if run_id is not None:
            row = self._con.execute(
                "SELECT run_id FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is not None:
                self._con.execute(
                    "UPDATE runs SET status = 'running', finished_at = NULL WHERE run_id = ?",
                    (run_id,),
                )
                self._con.commit()
                return run_id
        return self.start_run(config, run_id=run_id)

    def record_generation(
        self,
        run_id: str,
        gen_no: int,
        *,
        buy_name: str,
        sell_name: str,
        status: str,
        score: float,
        calmar: float = 0.0,
        uptrend_r2: float = 0.0,
        gate_passed: bool = False,
        reason: str = "",
        csv_path: Optional[str] = None,
        trade_count: int = 0,
        daily_avg_trades: float = 0.0,
        mdd: float = 0.0,
        profit: float = 0.0,
        total_profit_pct: float = 0.0,
        strategy_gist: str = "",
        parent_gen: Optional[int] = None,
        diff_from_parent: Optional[str] = None,
        payoff_ratio: float = 0.0,
        give_back_rate: float = 0.0,
        dispersion_term: float = 1.0,
        max_hold_count: float = 0.0,
        d_graded: Optional[float] = None,
        d_mdd: Optional[float] = None,
        d_trades: Optional[float] = None,
        d_profit: Optional[float] = None,
        d_daily_trades: Optional[float] = None,
        d_calmar: Optional[float] = None,
        d_uptrend_r2: Optional[float] = None,
        hypotheses_json: Optional[str] = None,
    ) -> None:
        """한 세대 결과를 기록한다 (UPSERT — 세대 번호 중복 없음).

        기록 직후 JSON 스냅샷을 남긴다. daily_avg_trades/mdd/profit/total_profit_pct/
        strategy_gist는 대시보드 세대 행(GenerationInfo)이 그대로 표시하는 값이라 함께
        영속한다. daily_avg_trades(일평균거래횟수)는 빈도 게이트의 주 기준값이다.
        total_profit_pct(수익률 %)는 profit(수익금 원)과 별개 지표다. 기본 0.0이라
        이 인자를 주지 않던 기존 호출부도 그대로 동작한다(하위호환).
        payoff_ratio(손익비)/give_back_rate(기회 반납률)는 청산 품질 지표다. 기본 0.0이라
        이 인자를 주지 않던 기존 호출부도 그대로 동작한다(하위호환).
        dispersion_term(다종목 분산 보상항)/max_hold_count(최대 동시보유 종목 수)는 R8
        품질지표 LIVE 노출용이다. dispersion_term 기본 1.0(중립), max_hold_count 기본 0.0이라
        이 인자를 주지 않던 기존 호출부도 그대로 동작한다(하위호환).

        parent_gen/diff_from_parent(P3 연구 파이프라인): 이 세대가 점진 개선한
        부모 세대 번호와 부모 대비 변경 요약(NL)이다. 둘 다 None이면(예: gen0 시드,
        GA 미배선) NULL로 저장돼 기존 동작과 동일하다(하위호환). **전략 코드 전문은
        복제 저장하지 않는다** — 코드는 stockbuy/stocksell에 namespaced로 이미 존재.

        d_graded..d_uptrend_r2: 부모 대비 숫자 델타(P1b). None이면 NULL(부모 없는
        세대). diff_from_parent NL과 같은 값의 숫자형으로, SQL 집계(AVG/ORDER BY)를
        가능케 한다.

        hypotheses_json(P2a): 이 세대가 검증한 가정+판정의 JSON 직렬화 문자열.
        직전 세대 부검이 세운 가정을 이 세대의 부모 대비 델타로 채택/기각한 결과다.
        None이면 NULL(부모 없는 세대·토글 OFF·기존 호출부). 기본 None이라 이 인자를
        주지 않던 기존 호출부도 그대로 동작한다(하위호환·byte-identical).
        """
        self._con.execute(
            "INSERT OR REPLACE INTO generations "
            "(run_id, gen_no, buy_name, sell_name, status, score, calmar, uptrend_r2, "
            " gate_passed, reason, csv_path, trade_count, daily_avg_trades, mdd, profit, "
            " total_profit_pct, strategy_gist, parent_gen, diff_from_parent, "
            " payoff_ratio, give_back_rate, dispersion_term, max_hold_count, "
            " d_graded, d_mdd, d_trades, d_profit, d_daily_trades, d_calmar, d_uptrend_r2, "
            " hypotheses_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id, gen_no, buy_name, sell_name, status, float(score),
                float(calmar), float(uptrend_r2), 1 if gate_passed else 0,
                reason, csv_path, int(trade_count), float(daily_avg_trades),
                float(mdd), float(profit), float(total_profit_pct), strategy_gist,
                (None if parent_gen is None else int(parent_gen)),
                diff_from_parent,
                float(payoff_ratio), float(give_back_rate),
                float(dispersion_term), float(max_hold_count),
                # P1b 부모 대비 숫자 델타. None이면 NULL(부모 없는 세대) — float()를
                #   씌우지 않아 NULL을 0.0으로 바꾸지 않는다(부모 없음 ↔ 델타 0 구분).
                (None if d_graded is None else float(d_graded)),
                (None if d_mdd is None else float(d_mdd)),
                (None if d_trades is None else float(d_trades)),
                (None if d_profit is None else float(d_profit)),
                (None if d_daily_trades is None else float(d_daily_trades)),
                (None if d_calmar is None else float(d_calmar)),
                (None if d_uptrend_r2 is None else float(d_uptrend_r2)),
                # P2a 가정+판정 직렬화. 문자열 그대로 저장(None이면 NULL).
                hypotheses_json,
                _now(),
            ),
        )
        self._con.commit()
        self._write_snapshot(run_id, gen_no, {
            "run_id": run_id,
            "gen_no": gen_no,
            "buy_name": buy_name,
            "sell_name": sell_name,
            "status": status,
            "score": float(score),
            "calmar": float(calmar),
            "uptrend_r2": float(uptrend_r2),
            "gate_passed": bool(gate_passed),
            "reason": reason,
            "csv_path": csv_path,
            "trade_count": int(trade_count),
            "daily_avg_trades": float(daily_avg_trades),
            "mdd": float(mdd),
            "profit": float(profit),
            "total_profit_pct": float(total_profit_pct),
            "strategy_gist": strategy_gist,
            "parent_gen": parent_gen,
            "diff_from_parent": diff_from_parent,
            "payoff_ratio": float(payoff_ratio),
            "give_back_rate": float(give_back_rate),
            "dispersion_term": float(dispersion_term),
            "max_hold_count": float(max_hold_count),
            # P1b 부모 대비 숫자 델타. None이면 그대로 None(JSON null) — 부모 없는 세대.
            "d_graded": d_graded,
            "d_mdd": d_mdd,
            "d_trades": d_trades,
            "d_profit": d_profit,
            "d_daily_trades": d_daily_trades,
            "d_calmar": d_calmar,
            "d_uptrend_r2": d_uptrend_r2,
            # P2a 가정+판정 직렬화. None이면 그대로 None(JSON null) — 부모 없는 세대·토글 OFF.
            "hypotheses_json": hypotheses_json,
        })

    def record_prompt(
        self,
        run_id: str,
        gen_no: int,
        kind: str,
        attempt: int,
        *,
        system_text: str = "",
        user_text: str = "",
        injected_features: Optional[Dict[str, Any]] = None,
        prior_error: Optional[str] = None,
        model: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        response_text: str = "",
    ) -> None:
        """한 LLM 호출의 프롬프트를 prompts 테이블에 기록한다 (P1c 프롬프트 영속화).

        재현성: 현재 호출별 프롬프트가 휘발해 어떤 프롬프트가 어떤 전략을 낳았는지
        사후에 추적할 수 없다. generate_strategy가 매 LLM 호출 성공 직후 콜백으로
        이 메서드를 호출해 프롬프트를 영속한다(config.prompt_logging_enabled=ON일 때만).

        system 전문은 정적 v1 자산이라 sha만 저장하고(system_sha), user 전문은
        동적이라 전문 저장한다(user_text + user_sha; 용량 가드). injected_features는
        json으로 직렬화해 저장한다(어떤 피처/토글이 이 프롬프트에 주입됐는지).
        sha는 hashlib.sha256(UTF-8)으로 계산하며 빈 문자열도 안전하다. 예외는
        삼키지 않는다 — 호출측(콜백 try/except)이 처리한다(로깅 실패가 루프를
        막지 않도록).
        """
        system_sha = hashlib.sha256((system_text or "").encode("utf-8")).hexdigest()
        user_sha = hashlib.sha256((user_text or "").encode("utf-8")).hexdigest()
        response_sha = hashlib.sha256((response_text or "").encode("utf-8")).hexdigest()
        features_json = (
            json.dumps(injected_features, ensure_ascii=False)
            if injected_features is not None
            else None
        )
        self._con.execute(
            "INSERT INTO prompts "
            "(run_id, gen_no, kind, attempt, system_sha, user_text, user_sha, "
            " injected_features, prior_error, model, prompt_tokens, completion_tokens, "
            " total_tokens, response_sha, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id, int(gen_no), kind, int(attempt),
                system_sha, user_text, user_sha,
                features_json, prior_error, model,
                int(prompt_tokens), int(completion_tokens), int(total_tokens),
                response_sha, _now(),
            ),
        )
        self._con.commit()

    def get_prompts(self, run_id: str) -> List[Dict[str, Any]]:
        """이 run의 모든 프롬프트 기록을 prompt_id 순으로 반환한다 (재현/조회용)."""
        rows = self._con.execute(
            "SELECT * FROM prompts WHERE run_id = ? ORDER BY prompt_id", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_equity_curve(
        self, run_id: str, gen_no: int, series: Optional[Dict[str, Any]]
    ) -> int:
        """한 세대의 백테 시계열(다운샘플)을 equity_points에 영속한다 (O2, 멱등).

        series는 fitness.equity_series.parse_backtest_series 결과(daily/cumulative/
        drawdown/summary)다. **파싱은 호출부(loop.py)가 하고 여기엔 이미 파싱된 series만
        넘긴다** — state가 fitness를 import하지 않도록(레이어 분리).

        같은 (run_id, gen_no)를 먼저 DELETE 후 삽입해 멱등(재기록 시 중복이 쌓이지
        않는다). daily/cumulative/drawdown 세 시계열을 거래일(date) 순번(t_index)으로
        zip해 한 행씩 INSERT한다. 세 시계열은 parse_backtest_series가 동일 거래일 인덱스로
        만들어 길이가 같다(다운샘플도 동일 인덱스). 빈 series(daily=[])면 기존 행만 지우고
        0을 반환한다(CSV 없음/파싱 실패의 no-op 흡수).

        Returns:
            삽입한 시점(point) 수.
        """
        # 같은 (run_id, gen_no) 기존 점들을 먼저 제거(멱등 — 재기록 시 중복 방지).
        self._con.execute(
            "DELETE FROM equity_points WHERE run_id = ? AND gen_no = ?",
            (run_id, int(gen_no)),
        )

        daily = list((series or {}).get("daily", []) or [])
        cumulative = list((series or {}).get("cumulative", []) or [])
        drawdown = list((series or {}).get("drawdown", []) or [])

        if not daily:
            # 빈 구조(CSV 없음/파싱 실패) → 기존 점만 지우고 no-op. 토글 ON이어도 안전.
            self._con.commit()
            return 0

        # cumulative/drawdown은 daily와 같은 길이/거래일 순서다. date는 daily 기준으로
        #   잡고(존재 보장), cum/drawdown은 동일 인덱스에서 가져온다(누락 시 0.0/None).
        rows_to_insert = []
        for t_index, d in enumerate(daily):
            date = int(d.get("date", 0) or 0)
            daily_pnl = float(d.get("daily_pnl", 0.0) or 0.0)
            cum = cumulative[t_index] if t_index < len(cumulative) else {}
            dd = drawdown[t_index] if t_index < len(drawdown) else {}
            cum_profit = float(cum.get("cum_profit", 0.0) or 0.0)
            cum_pct_raw = cum.get("cum_pct")
            cum_pct = None if cum_pct_raw is None else float(cum_pct_raw)
            drawdown_val = float(dd.get("drawdown", 0.0) or 0.0)
            rows_to_insert.append((
                run_id, int(gen_no), int(t_index), date,
                daily_pnl, cum_profit, cum_pct, drawdown_val,
            ))
        self._con.executemany(
            "INSERT INTO equity_points "
            "(run_id, gen_no, t_index, date, daily_pnl, cum_profit, cum_pct, drawdown) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows_to_insert,
        )
        self._con.commit()
        return len(rows_to_insert)

    def get_equity_points(self, run_id: str, gen_no: int) -> List[Dict[str, Any]]:
        """한 세대의 equity_points 시점들을 t_index 순으로 반환한다 (테스트·O1 차트용)."""
        rows = self._con.execute(
            "SELECT * FROM equity_points WHERE run_id = ? AND gen_no = ? ORDER BY t_index",
            (run_id, int(gen_no)),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_best(self, run_id: str, best_gen: int, best_score: float) -> None:
        """run의 best_gen/best_score를 갱신한다 (더 높은 점수일 때만)."""
        row = self._con.execute(
            "SELECT best_score FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        current = row["best_score"] if row is not None else None
        if current is None or float(best_score) > float(current):
            self._con.execute(
                "UPDATE runs SET best_gen = ?, best_score = ? WHERE run_id = ?",
                (int(best_gen), float(best_score), run_id),
            )
            self._con.commit()

    def finish_run(self, run_id: str, status: str = "complete") -> None:
        """run을 종료 상태로 마킹한다."""
        self._con.execute(
            "UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?",
            (status, _now(), run_id),
        )
        self._con.commit()

    # ------------------------------------------------------------------
    # 조회 / resume 보조
    # ------------------------------------------------------------------
    def get_last_completed_gen(self, run_id: str) -> int:
        """기록된 마지막 세대 번호를 반환한다. 없으면 -1.

        resume는 이 값 + 1 부터 이어간다.
        """
        row = self._con.execute(
            "SELECT MAX(gen_no) AS m FROM generations WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None or row["m"] is None:
            return -1
        return int(row["m"])

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        row = self._con.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def get_generations(self, run_id: str) -> list:
        rows = self._con.execute(
            "SELECT * FROM generations WHERE run_id = ? ORDER BY gen_no", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_cumulative_generation_count(self, run_id: str) -> int:
        """이 run에 기록된 총 세대 수 (cost-cap 판정에 사용)."""
        row = self._con.execute(
            "SELECT COUNT(*) AS c FROM generations WHERE run_id = ?", (run_id,)
        ).fetchone()
        return int(row["c"]) if row is not None else 0

    def list_runs(self) -> List[Dict[str, Any]]:
        """모든 run 행을 시작 시각 순으로 반환한다 (run 비교/메타분석용)."""
        rows = self._con.execute(
            "SELECT * FROM runs ORDER BY started_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_generations(self) -> List[Dict[str, Any]]:
        """모든 run의 모든 세대 행을 반환한다 (메타분석 누적 집계용, P4).

        run_id, gen_no 순으로 정렬한다. 여러 run에 걸친 누적 generations를
        한 번에 읽어 "어떤 변경이 개선을 낳나"를 집계한다.
        """
        rows = self._con.execute(
            "SELECT * FROM generations ORDER BY run_id, gen_no"
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------
    def _write_snapshot(self, run_id: str, gen_no: int, payload: Dict[str, Any]) -> None:
        path = Path(self.snapshot_dir) / f"{run_id}_g{gen_no}.json"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        except OSError:
            # 스냅샷은 안전장치일 뿐 — 실패해도 DB 기록은 유효하므로 무시.
            pass

    def close(self) -> None:
        try:
            self._con.close()
        except sqlite3.Error:
            pass


def _config_to_dict(config: Any) -> Dict[str, Any]:
    """config를 직렬화 가능한 dict로 변환한다 (to_dict 우선, 아니면 dict/그대로)."""
    if config is None:
        return {}
    to_dict = getattr(config, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(config, dict):
        return config
    return {"repr": repr(config)}


# =====================================================================
# US-007 — 라이브 상태 발행 (current_state.json) + 정지 플래그 (STOP).
#   루프(서브프로세스)와 대시보드(FastAPI)를 잇는 파일 기반 seam이다.
#   계약 스키마는 controller/contract.py: LoopState (pydantic) 참조.
# =====================================================================
def publish_loop_state(state: Any, path: Optional[str] = None) -> None:
    """LoopState(contract) 스냅샷을 current_state.json에 ATOMIC write 한다.

    같은 디렉토리에 `.tmp`로 쓰고 os.replace로 교체해 부분 쓰기(half-written
    JSON)를 폴링 reader가 읽는 것을 막는다. state는 contract.LoopState
    (model_dump_json/ .dict()) 또는 이미 직렬화된 dict 둘 다 받는다.

    발행 실패는 루프를 막지 않는다(라이브 상태는 가시화 보조이지 정확성
    필수 경로가 아니다) — 예외를 흡수한다.
    """
    target = Path(path or CURRENT_STATE_FILE)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # pydantic v2(model_dump_json) → v1(json) → dict 순으로 직렬화.
        dump = getattr(state, "model_dump_json", None)
        if callable(dump):
            text = dump()
        elif hasattr(state, "json") and callable(state.json):
            text = state.json()
        else:
            text = json.dumps(state, ensure_ascii=False)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, target)
    except OSError:
        # 라이브 상태 발행은 안전장치일 뿐 — 실패해도 루프는 계속한다.
        pass


def read_current_state(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """current_state.json을 dict로 읽는다. 없거나 손상이면 None.

    대시보드 GET /status / WS push가 사용한다.
    """
    target = Path(path or CURRENT_STATE_FILE)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def clear_current_state(path: Optional[str] = None) -> None:
    """current_state.json을 제거한다 (idle 복원용)."""
    target = Path(path or CURRENT_STATE_FILE)
    try:
        target.unlink()
    except OSError:
        pass


def set_stop_flag(path: Optional[str] = None) -> str:
    """정지 플래그 파일을 쓴다 (대시보드 stop 제어). 경로를 반환한다.

    루프는 매 세대 시작 전 stop_requested()로 이 파일을 확인한다.
    """
    target = Path(path or STOP_FLAG_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(time.time()), encoding="utf-8")
    return str(target)


def stop_requested(path: Optional[str] = None) -> bool:
    """정지 플래그가 존재하는지 확인한다 (루프가 매 세대 시작 전 호출)."""
    return Path(path or STOP_FLAG_FILE).exists()


def clear_stop_flag(path: Optional[str] = None) -> None:
    """정지 플래그를 제거한다 (루프 시작 시 / 종료 시 cleanup)."""
    try:
        Path(path or STOP_FLAG_FILE).unlink()
    except OSError:
        pass


# R8 — active_config 스냅샷에 실을 주요 config 필드. 5종 안전토글 + 진화/평가/스코프
#   설정을 한 자리에 모아 대시보드가 "지금 무슨 설정으로 돌고 있나"를 LIVE로 보여준다.
#   (config 객체에 없는 필드는 getattr 폴백으로 건너뛰므로 LoopConfig 버전 차이에 안전.)
_ACTIVE_CONFIG_FIELDS = (
    # 5종 안전/Track B 토글.
    "dispersion_prompt_enabled",
    "dispersion_enabled",
    "min_hold_symbols",
    "target_daily_trades",
    "require_liquidity_gate",
    "mdd_control_enabled",
    # 진화/우승 목표.
    "evolution_mode",
    "winner_objective",
    "profit_weight",
    # 평가 엔진/스코프.
    "bt_engine_mode",
    "bt_scope",
    "bt_timeframe",
    "bt_refine_from_best",
    "freeze_buy_on_mdd_only",
    "bt_full_start",
    "bt_full_end",
    "bt_universe_start_time",
    "bt_universe_end_time",
    "bt_betting",
    # 게이트 경계(가시화).
    "mdd_cap",
    "min_trades",
    "min_daily_trades",
    "overtrade_softcap",
    "tpi_gate_enabled",
    "tpi_gate",
    "exit_quality_enabled",
    "target_score",
    "max_generations",
)

# 토글로 강조 렌더할 bool 필드(프론트가 켜진 것만 강조). 가시화 보조 메타.
_ACTIVE_CONFIG_TOGGLES = (
    "dispersion_prompt_enabled",
    "dispersion_enabled",
    "require_liquidity_gate",
    "mdd_control_enabled",
    "bt_refine_from_best",
    "freeze_buy_on_mdd_only",
    "tpi_gate_enabled",
    "exit_quality_enabled",
)


def build_active_config(config: Any) -> Dict[str, Any]:
    """config에서 LIVE 노출용 주요 설정/토글을 dict로 추출한다(없는 필드는 생략).

    순수 함수(테스트 가능). config가 None이면 빈 dict. _ACTIVE_CONFIG_FIELDS에
    나열된 필드만 골라 담고, 토글 분류는 'toggles' 키에 bool 필드 이름 목록으로
    덧붙여 프론트가 켜진 토글을 강조할 수 있게 한다(가시화 보조).
    """
    if config is None:
        return {}
    snapshot: Dict[str, Any] = {}
    for name in _ACTIVE_CONFIG_FIELDS:
        if hasattr(config, name):
            snapshot[name] = getattr(config, name)
    # 토글 분류 메타: 실제 config에 존재하는 bool 토글 이름만(프론트 강조용).
    snapshot["toggles"] = [t for t in _ACTIVE_CONFIG_TOGGLES if t in snapshot]
    return snapshot


def to_loop_state(
    summary: Dict[str, Any],
    generations: List[Dict[str, Any]],
    *,
    config: Any = None,
    status: str = "running",
    current_gen: int = -1,
    latest: Optional[Dict[str, Any]] = None,
    cumulative_tokens: int = 0,
    page_data: Optional[Dict[str, Any]] = None,
) -> Any:
    """루프 요약 + 세대 기록을 contract.LoopState로 빌드한다.

    summary는 run_loop가 반환하는 dict(run_id, best_*, winner_* 등) 형태,
    generations는 LoopState(SQLite).get_generations(run_id) 행 형태를 받는다.
    config는 LoopConfig(provider/bt_timeframe/max_generations) — 없으면 기본값.
    page_data는 contract v2 패스스루(후속 페이지가 자기 키에 자기 데이터). None이면
    빈 dict로 발행해 v1과 동일 결과를 유지한다(하위호환).

    contract.LoopState(pydantic) 인스턴스를 반환한다. publish_loop_state로
    바로 발행 가능하다.
    """
    from ai_strategy_loop.controller import contract as C  # noqa: PLC0415

    provider = str(getattr(config, "provider", "") or "")
    bt_timeframe = str(getattr(config, "bt_timeframe", "") or "")
    max_gen = int(getattr(config, "max_generations", 0) or summary.get("max_generations", 0) or 0)

    best = C.BestInfo(
        gen=int(summary.get("best_gen", -1) if summary.get("best_gen") is not None else -1),
        graded_score=summary.get("best_score"),
        gate_passed=False,  # best는 graded 선택 — 게이트 통과 여부는 행에서 보강.
        buy_name=summary.get("best_buy"),
        sell_name=summary.get("best_sell"),
    )

    winner = None
    if summary.get("winner_gen", -1) is not None and int(summary.get("winner_gen", -1)) >= 0:
        winner = C.WinnerInfo(
            gen=int(summary["winner_gen"]),
            score=summary.get("winner_score"),
            buy_name=summary.get("winner_buy"),
            sell_name=summary.get("winner_sell"),
        )

    # best 세대의 gate_passed를 generations 행에서 보강.
    gen_rows: List[Any] = []
    for g in generations:
        gate_passed = bool(g.get("gate_passed"))
        if int(g.get("gen_no", -1)) == best.gen:
            best.gate_passed = gate_passed
        # P2b-2 — 이 세대가 검증한 가정+판정(hypotheses_json)을 파싱해 대시보드에 노출한다.
        #   NULL/빈/파싱실패/리스트 아님 → [](하위호환: 토글 OFF/구 상태/부모 없는 세대).
        raw = g.get("hypotheses_json")
        hyps: List[Dict[str, Any]] = []
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    hyps = parsed
            except (ValueError, TypeError):
                hyps = []
        gen_rows.append(C.GenerationInfo(
            gen_no=int(g.get("gen_no", -1)),
            status=str(g.get("status", "")),
            graded_score=float(g.get("score", 0.0) or 0.0),
            gate_passed=gate_passed,
            gate_reason=str(g.get("reason", "") or ""),
            trade_count=int(g.get("trade_count", 0) or 0),
            # 일평균거래횟수. 구 DB 행(컬럼 없음)은 키가 없거나 NULL이라 0.0 폴백.
            daily_avg_trades=float(g.get("daily_avg_trades", 0.0) or 0.0),
            mdd=float(g.get("mdd", 0.0) or 0.0),
            profit=float(g.get("profit", 0.0) or 0.0),
            # P10 — 수익률(%). 구 DB 행(컬럼 없음)·구 run·에러 세대는 키가 없거나 NULL이다.
            #   NULL을 0.0으로 강제하면 '미측정'과 '실제 0%'가 구분 불가해 대시보드가
            #   손실 세대를 0%로 잘못 표시한다. None(미측정)은 그대로 전파하고, 값이
            #   있으면(0.0 포함) float로 보존한다(정보 손실 수정).
            total_profit_pct=(
                None if g.get("total_profit_pct") is None
                else float(g.get("total_profit_pct"))
            ),
            strategy_gist=str(g.get("strategy_gist", "") or ""),
            # 청산 품질. 구 DB 행(v5 이전)은 키가 없거나 NULL이라 0.0 폴백.
            payoff_ratio=float(g.get("payoff_ratio", 0.0) or 0.0),
            give_back_rate=float(g.get("give_back_rate", 0.0) or 0.0),
            # R8 — 위험조정 품질(calmar/uptrend_r2, v1부터 존재) + 다종목 분산(v6 신설).
            #   is None 가드는 키가 없는 dict 입력(합성/인메모리 행)·명시적 NULL을 방어한다.
            #   실제 마이그레이션된 DB 행은 ALTER ADD COLUMN DEFAULT에 의해 1.0/0.0을 갖는다.
            #   `or` 폴백이 0.0을 1.0으로 바꾸지 않도록 dispersion_term은 None만 1.0으로 처리한다.
            calmar=float(g.get("calmar", 0.0) or 0.0),
            uptrend_r2=float(g.get("uptrend_r2", 0.0) or 0.0),
            dispersion_term=(1.0 if g.get("dispersion_term") is None
                             else float(g.get("dispersion_term"))),
            max_hold_count=float(g.get("max_hold_count", 0.0) or 0.0),
            # P2b-2 — 위에서 파싱한 가정 리스트(없으면 [] = 하위호환).
            hypotheses=hyps,
        ))

    # #64 — step_timings는 {단계명: 소요초} dict. 키는 str, 값은 float로 정규화한다
    #   (구 상태/잘못된 타입 방어). 미발행이면 빈 dict라 프론트가 완료 배지를 생략한다.
    _raw_timings = (latest or {}).get("step_timings", {}) or {}
    step_timings: Dict[str, float] = {}
    if isinstance(_raw_timings, dict):
        for _k, _v in _raw_timings.items():
            try:
                step_timings[str(_k)] = float(_v)
            except (TypeError, ValueError):
                continue
    latest_info = C.LatestInfo(
        phase=str((latest or {}).get("phase", "")),
        last_checkpoint=str((latest or {}).get("last_checkpoint", "")),
        message=str((latest or {}).get("message", "")),
        recent_logs=list((latest or {}).get("recent_logs", [])),
        current_step=int((latest or {}).get("current_step", -1)),
        # #64 — LIVE 진행시간(단계/세대 시작 epoch + 단계별 소요초). 기본 0.0/빈 dict라
        #   이 값을 발행하지 않던 구 상태도 그대로 검증 통과한다(하위호환).
        phase_started_at=float((latest or {}).get("phase_started_at", 0.0) or 0.0),
        gen_started_at=float((latest or {}).get("gen_started_at", 0.0) or 0.0),
        step_timings=step_timings,
    )

    return C.LoopState(
        run_id=summary.get("run_id"),
        status=status,
        current_gen=current_gen,
        max_generations=max_gen,
        provider=provider,
        bt_timeframe=bt_timeframe,
        best=best,
        winner=winner,
        generations=gen_rows,
        latest=latest_info,
        cumulative=C.CumulativeInfo(
            tokens=int(cumulative_tokens),
            cost_or_count=len(gen_rows),
        ),
        page_data=dict(page_data or {}),
        # R8 — 적용된 config의 주요 설정/토글 스냅샷(없으면 빈 dict=하위호환).
        active_config=build_active_config(config),
        updated_at=time.time(),
    )
