"""CL-R03 — append-only EvidenceStore over LoopState's SQLite connection.

design spec: docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/
lattice_v3_design_spec_20260709.md §9(append-only 규칙), §7(스키마 -> payload_json 저장).

EvidenceStore는 새 DB 연결을 열지 않는다 — 기존 LoopState(v11 스키마: state.py
_init_schema에서 CREATE TABLE IF NOT EXISTS로 생성)의 커넥션을 재사용한다. 테스트
편의를 위해 raw sqlite3.Connection도 직접 받을 수 있다.

append-only 규칙(§9):
  - 5개 evidence 테이블(candidate_passports/feedback_envelopes/feedback_consumptions/
    evaluation_manifests/run_receipts)에는 UPDATE/DELETE를 절대 실행하지 않는다.
  - 동일 PK + 동일 payload_json 재삽입은 멱등 no-op(재시도/재실행 안전).
  - 동일 PK + 다른 payload_json 재삽입은 EvidenceCorruptionError(내용이 바뀐 재삽입은
    증거 오염이므로 조용히 덮어쓰지 않고 시끄럽게 실패한다).
  - 커밋 성공 후에만 사람이 읽을 수 있는 JSON 스냅샷을 남긴다(DB가 정본, 스냅샷은
    복구 보조 거울 — 자동 임포트하지 않는다).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ai_strategy_loop.controller.evidence_contract import (
    CandidatePassport,
    EvaluationManifest,
    FeedbackConsumption,
    FeedbackEnvelope,
    RunReceipt,
    canonical_json,
)

__all__ = ["EvidenceStore", "EvidenceCorruptionError", "EvidenceOrphanError"]


class EvidenceCorruptionError(Exception):
    """동일 PK에 다른 payload_json으로 재삽입을 시도했을 때 발생한다.

    append-only 증거는 내용이 바뀌면 안 된다 — 같은 identity가 다른 내용을 낸다는
    것은 hash/identity 계산이 깨졌거나 상위 로직이 재사용 가능한 PK를 실수로 새
    내용에 재사용했다는 뜻이다. 조용히 덮어쓰면 감사 추적이 오염되므로 예외로 막는다.
    """


class EvidenceOrphanError(Exception):
    """DR-03 — a consumption references a prompt_id that is not an actually-
    rendered/persisted prompt (see ``EvidenceStore.append_consumption``'s
    ``require_rendered`` guard). Raised BEFORE any row is written — fail-closed,
    no orphan evidence row is ever committed.
    """


def _now() -> float:
    return time.time()


class EvidenceStore:
    """append-only 증거 저장소 (LoopState 커넥션을 공유해서 쓴다).

    ``EvidenceStore(loop_state)``가 정식 사용법이다 — ``loop_state._con``과
    ``loop_state.snapshot_dir``을 그대로 재사용해 두 번째 DB 연결을 열지 않는다.
    단위 테스트는 raw ``sqlite3.Connection``을 직접 넘길 수 있다(이 경우
    snapshot_dir을 명시하지 않으면 스냅샷을 스킵한다).
    호출 전제(F1): _append는 공유 커넥션에서 commit/rollback을 수행하므로, 상위
    (LoopState.record_*)가 열어둔 미완료 트랜잭션 안에서 호출하면 안 된다. LoopState의
    모든 record_*는 즉시 commit하므로 그 seam(커밋 직후, 열린 트랜잭션 없음)에서
    호출하면 안전하다. CL-R04 controller wiring은 이 전제를 지킨다.
    """

    def __init__(
        self,
        loop_state_or_con: Union[Any, sqlite3.Connection],
        snapshot_dir: Optional[str] = None,
    ) -> None:
        if isinstance(loop_state_or_con, sqlite3.Connection):
            self._con = loop_state_or_con
            self.snapshot_dir = snapshot_dir
        else:
            self._con = loop_state_or_con._con
            self.snapshot_dir = (
                snapshot_dir if snapshot_dir is not None else getattr(loop_state_or_con, "snapshot_dir", None)
            )

    # ------------------------------------------------------------------
    # 내부 — 공통 append 경로 (INSERT-only, 커밋 전까지 트랜잭션 하나)
    # ------------------------------------------------------------------
    def _append(
        self,
        *,
        table: str,
        pk_col: str,
        pk_val: str,
        columns: List[str],
        values: tuple,
        payload_json: str,
        run_id: Optional[str],
        snapshot_kind: str,
    ) -> None:
        col_list = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        cur = self._con.cursor()
        try:
            cur.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                values,
            )
        except sqlite3.IntegrityError as exc:
            self._con.rollback()
            row = self._con.execute(
                f"SELECT payload_json FROM {table} WHERE {pk_col} = ?", (pk_val,)
            ).fetchone()
            if row is not None:
                existing_payload = row[0] if not isinstance(row, sqlite3.Row) else row["payload_json"]
                if existing_payload == payload_json:
                    return  # 동일 PK + 동일 payload — 멱등 no-op.
                raise EvidenceCorruptionError(
                    f"{table}:{pk_val} — 동일 PK에 다른 payload_json 재삽입 시도(증거 오염)"
                ) from exc
            # PK 충돌이 아니면(예: FOREIGN KEY 제약 위반) 원래 예외를 그대로 전파한다.
            raise
        except Exception:
            # IntegrityError 외 오류(OperationalError: locked/full 등)도 공유 커넥션에
            #   트랜잭션을 방치하지 않도록 롤백 후 전파한다(F2). 위 호출 전제상 상위의
            #   미완료 트랜잭션은 없으므로 이 rollback은 이 append 시도만 되돌린다.
            self._con.rollback()
            raise
        try:
            self._con.commit()
        except Exception:
            self._con.rollback()
            raise
        if run_id:
            self._write_evidence_snapshot(run_id, snapshot_kind, pk_val, payload_json)

    def _write_evidence_snapshot(
        self, run_id: str, kind: str, evidence_id: str, payload_json: str
    ) -> None:
        """커밋 후 사람이 읽을 수 있는 거울 스냅샷을 남긴다(실패해도 DB 기록은 유효).

        DB가 정본이다 — 이 스냅샷은 절대 자동으로 다시 읽어 DB에 임포트하지 않는다
        (복구 시 사람이 확인 후 수동으로만 사용).
        """
        if not self.snapshot_dir:
            return
        try:
            target_dir = Path(self.snapshot_dir) / run_id / "evidence" / kind
            target_dir.mkdir(parents=True, exist_ok=True)
            path = target_dir / f"{evidence_id}.json"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(payload_json)
        except OSError:
            # 스냅샷은 안전장치일 뿐 — 실패해도 DB 기록(커밋 완료)은 유효하므로 무시.
            pass

    # ------------------------------------------------------------------
    # append — CandidatePassport
    # ------------------------------------------------------------------
    def append_passport(self, passport: CandidatePassport) -> None:
        payload_json = canonical_json(passport.to_dict())
        self._append(
            table="candidate_passports",
            pk_col="passport_id",
            pk_val=passport.passport_id,
            columns=[
                "passport_id", "candidate_id", "run_id", "round_no", "gen_no",
                "slot_no", "parent_passport_id", "manifest_id", "payload_json",
                "created_at",
            ],
            values=(
                passport.passport_id,
                passport.candidate_id,
                passport.run_id,
                int(passport.round_no),
                int(passport.gen_no),
                int(passport.slot_no),
                passport.parent_passport_id,
                passport.manifest_id,
                payload_json,
                _now(),
            ),
            payload_json=payload_json,
            run_id=passport.run_id,
            snapshot_kind="passport",
        )

    # ------------------------------------------------------------------
    # append — FeedbackEnvelope
    # ------------------------------------------------------------------
    def append_feedback(self, feedback: FeedbackEnvelope, run_id: Optional[str] = None) -> None:
        payload_json = canonical_json(feedback.to_dict())
        self._append(
            table="feedback_envelopes",
            pk_col="feedback_id",
            pk_val=feedback.feedback_id,
            columns=["feedback_id", "source_passport_id", "payload_json", "created_at"],
            values=(
                feedback.feedback_id,
                feedback.source_passport_id,
                payload_json,
                _now(),
            ),
            payload_json=payload_json,
            run_id=run_id,
            snapshot_kind="feedback",
        )

    # ------------------------------------------------------------------
    # append — FeedbackConsumption
    # ------------------------------------------------------------------
    def append_consumption(
        self,
        consumption: FeedbackConsumption,
        run_id: Optional[str] = None,
        *,
        require_rendered: bool = False,
    ) -> None:
        """append a FeedbackConsumption (append-only).

        ``require_rendered`` (DR-03, additive, default False — v1 byte-identical):
        when True, ``consumption.prompt_id`` MUST already be registered in the
        additive ``rendered_prompts`` table (see ``LoopState.record_prompt``) —
        i.e. it must reference an ACTUALLY-rendered/persisted prompt, not an
        absent/synthetic id. Violations raise ``EvidenceOrphanError`` *before*
        any row is written (fail-closed — no partial/orphan consumption row).
        Default False preserves the original v1 behavior exactly, where
        ``prompt_id`` is any free nonempty string (existing tests/fixtures use
        placeholder strings like ``"prompt-1"``).
        """
        if require_rendered and not self.is_rendered_prompt(consumption.prompt_id):
            raise EvidenceOrphanError(
                f"consumption:{consumption.consumption_id} references prompt_id="
                f"{consumption.prompt_id!r} that is not an actually-rendered/"
                "persisted prompt (rendered-only consumption guard, DR-03)"
            )
        payload_json = canonical_json(consumption.to_dict())
        self._append(
            table="feedback_consumptions",
            pk_col="consumption_id",
            pk_val=consumption.consumption_id,
            columns=[
                "consumption_id", "feedback_id", "prompt_id", "target_passport_id",
                "payload_json", "created_at",
            ],
            values=(
                consumption.consumption_id,
                consumption.feedback_id,
                consumption.prompt_id,
                consumption.target_passport_id,
                payload_json,
                _now(),
            ),
            payload_json=payload_json,
            run_id=run_id,
            snapshot_kind="consumption",
        )

    # ------------------------------------------------------------------
    # DR-03 — rendered-prompt registry lookup (see LoopState.record_prompt).
    # ------------------------------------------------------------------
    def is_rendered_prompt(self, rendered_prompt_id: Optional[str]) -> bool:
        """True iff ``rendered_prompt_id`` is registered in ``rendered_prompts``.

        A missing ``rendered_prompts`` table (e.g. a raw ``sqlite3.Connection``
        fixture that never ran ``LoopState._init_schema``) is treated the same
        as "not found" — fail-closed (reject), never fail-open (accept).
        """
        if not rendered_prompt_id:
            return False
        try:
            row = self._con.execute(
                "SELECT 1 FROM rendered_prompts WHERE rendered_prompt_id = ?",
                (rendered_prompt_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return False
        return row is not None

    # ------------------------------------------------------------------
    # append — EvaluationManifest
    # ------------------------------------------------------------------
    def append_manifest(self, manifest: EvaluationManifest) -> None:
        payload_json = canonical_json(manifest.to_dict())
        self._append(
            table="evaluation_manifests",
            pk_col="manifest_id",
            pk_val=manifest.manifest_id,
            columns=["manifest_id", "run_id", "role", "payload_json", "created_at"],
            values=(
                manifest.manifest_id,
                manifest.run_id,
                manifest.role,
                payload_json,
                _now(),
            ),
            payload_json=payload_json,
            run_id=manifest.run_id,
            snapshot_kind="manifest",
        )

    # ------------------------------------------------------------------
    # append — RunReceipt
    # ------------------------------------------------------------------
    def append_receipt(self, receipt: RunReceipt) -> None:
        payload_json = canonical_json(receipt.to_dict())
        self._append(
            table="run_receipts",
            pk_col="receipt_id",
            pk_val=receipt.receipt_id,
            columns=["receipt_id", "run_id", "phase_id", "outcome", "payload_json", "created_at"],
            values=(
                receipt.receipt_id,
                receipt.run_id,
                receipt.phase_id,
                receipt.outcome,
                payload_json,
                _now(),
            ),
            payload_json=payload_json,
            run_id=receipt.run_id,
            snapshot_kind="receipt",
        )

    # ------------------------------------------------------------------
    # 조회 — 5개 테이블 모두 payload_json(canonical dict)을 그대로 복원한다.
    #   consumption/receipt로부터의 "진행 상태"는 여기서 파생 쿼리로만 얻는다
    #   (evidence 행 자체를 UPDATE하지 않는다).
    # ------------------------------------------------------------------
    def _payload(self, row: sqlite3.Row) -> Dict[str, Any]:
        return json.loads(row["payload_json"])

    def get_passport(self, passport_id: str) -> Optional[Dict[str, Any]]:
        row = self._con.execute(
            "SELECT payload_json FROM candidate_passports WHERE passport_id = ?",
            (passport_id,),
        ).fetchone()
        return self._payload(row) if row is not None else None

    def get_manifest(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        row = self._con.execute(
            "SELECT payload_json FROM evaluation_manifests WHERE manifest_id = ?",
            (manifest_id,),
        ).fetchone()
        return self._payload(row) if row is not None else None

    def passports_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        rows = self._con.execute(
            "SELECT payload_json FROM candidate_passports WHERE run_id = ? "
            "ORDER BY gen_no, slot_no",
            (run_id,),
        ).fetchall()
        return [self._payload(row) for row in rows]

    def passports_for_gen(self, run_id: str, gen_no: int) -> List[Dict[str, Any]]:
        rows = self._con.execute(
            "SELECT payload_json FROM candidate_passports WHERE run_id = ? AND gen_no = ? "
            "ORDER BY slot_no",
            (run_id, int(gen_no)),
        ).fetchall()
        return [self._payload(row) for row in rows]

    def feedback_for_passport(self, passport_id: str) -> List[Dict[str, Any]]:
        rows = self._con.execute(
            "SELECT payload_json FROM feedback_envelopes WHERE source_passport_id = ? "
            "ORDER BY created_at",
            (passport_id,),
        ).fetchall()
        return [self._payload(row) for row in rows]

    def unconsumed_feedback(self, run_id: str) -> List[Dict[str, Any]]:
        """지정 run의 passport에서 발생했지만 아직 소비 기록이 없는 피드백.

        feedback_consumptions 존재 여부로 "소비됨"을 파생한다 — feedback_envelopes
        행 자체는 절대 UPDATE하지 않는다(append-only).
        """
        rows = self._con.execute(
            """
            SELECT fe.payload_json AS payload_json
            FROM feedback_envelopes fe
            JOIN candidate_passports cp ON cp.passport_id = fe.source_passport_id
            WHERE cp.run_id = ?
              AND NOT EXISTS (
                  SELECT 1 FROM feedback_consumptions fc WHERE fc.feedback_id = fe.feedback_id
              )
            ORDER BY fe.created_at
            """,
            (run_id,),
        ).fetchall()
        return [self._payload(row) for row in rows]

    def receipts_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        rows = self._con.execute(
            "SELECT payload_json FROM run_receipts WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        return [self._payload(row) for row in rows]
