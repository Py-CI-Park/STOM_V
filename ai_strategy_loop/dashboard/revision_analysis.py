"""Admission-first read-only revision preview using the existing proposer owners."""

from __future__ import annotations

from ai_strategy_loop.controller import strategy_preflight
from ai_strategy_loop.dashboard.feature_context import (
    FeatureContext,
    FeatureResponse,
    FeatureStatus,
    blocked_feature,
)
from ai_strategy_loop.dashboard.feature_snapshot import (
    SnapshotFrameError,
    snapshot_dataset,
)
from ai_strategy_loop.revision import intent_gate, proposer


def revision_result(context: FeatureContext, top_k: int) -> FeatureResponse:
    payload = FeatureResponse({**context.envelope().root, "proposals": None})
    source = context.source
    snapshot = source.checked.snapshot
    if not source.analysis_ready or snapshot is None:
        return payload
    if source.record is None:
        return blocked_feature(
            payload, FeatureStatus.NO_STRATEGY, "세대의 원본 기록이 없습니다."
        )
    buy_name = source.record.text("buy_name")
    if not buy_name:
        return blocked_feature(
            payload, FeatureStatus.NO_STRATEGY, "세대의 매수식 이름이 없습니다."
        )
    try:
        dataset = snapshot_dataset(snapshot)
        buy_code = strategy_preflight.load_loop_strategy_code("buy", buy_name)
        if not buy_code:
            return blocked_feature(
                payload, FeatureStatus.NO_STRATEGY, f"매수식 없음: {buy_name}"
            )
        specs = proposer.propose(
            dataset, buy_code, buy_name, top_k=max(1, min(top_k, 5))
        )
        out = []
        for spec in specs:
            new_code, apply_reason = proposer.apply(spec, buy_code)
            item = FeatureResponse.model_validate(
                {"spec": spec, "apply": apply_reason}
            ).root
            if new_code:
                verdict = intent_gate.verify(buy_code, new_code, [spec])
                preview = [
                    {"line": index + 1, "old": old, "new": new}
                    for index, (old, new) in enumerate(
                        zip(buy_code.splitlines(), new_code.splitlines())
                    )
                    if old != new
                ][:6]
                item.update(
                    FeatureResponse.model_validate(
                        {
                            "gate": {
                                "ok": verdict.ok,
                                "reason": verdict.reason,
                                "diffs": verdict.diffs,
                            },
                            "diff_preview": preview,
                        }
                    ).root
                )
            out.append(item)
        return FeatureResponse.model_validate(
            {
                **payload.root,
                "buy_name": buy_name,
                "proposals": out,
                "reason": "ok"
                if specs
                else "실효 제안 없음(HIER 아님·표본 부족·변별 부족 중 하나)",
            }
        ).finite()
    except SnapshotFrameError as exc:
        return blocked_feature(payload, FeatureStatus.PROCESSING_ERROR, str(exc))
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
        SyntaxError,
    ) as exc:
        return blocked_feature(
            payload,
            FeatureStatus.PROCESSING_ERROR,
            f"제안 미리보기를 완료하지 못했습니다 ({type(exc).__name__}).",
        )
