"""Full-column snapshot adapter to the existing analytics parser, without file I/O."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, override

from ai_strategy_loop.autopsy import label_dataset as labels

if TYPE_CHECKING:
    from ai_strategy_loop.dashboard.trade_csv_models import CsvSnapshot


@dataclass(frozen=True, slots=True)
class SnapshotFrameError(Exception):
    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


def snapshot_dataset(snapshot: CsvSnapshot) -> labels.LabelDataset:
    """Reparse captured cells with the legacy dtype/NA rules; retain original hash."""
    with StringIO(newline="") as stream:
        writer = csv.writer(stream)
        _ = writer.writerow(snapshot.headers)
        writer.writerows(snapshot.rows)
        stream.seek(0)
        frame = labels.load_csv(stream)
    if len(frame) != len(snapshot.rows):
        raise SnapshotFrameError("원본 snapshot과 분석 프레임의 행 수가 다릅니다.")
    if tuple(frame.columns) != snapshot.headers:
        raise SnapshotFrameError("원본 snapshot과 분석 프레임의 열 이름이 다릅니다.")
    for index, column in enumerate(snapshot.headers):
        if column not in ("보유시간", "수익률", "수익금") and not column.startswith(
            ("B_", "S_", "R_")
        ):
            continue
        missing = labels.numeric_series(frame, column).isna()
        for raw, absent in zip(snapshot.rows, missing, strict=True):
            if raw[index].strip() and absent:
                raise SnapshotFrameError(
                    f"분석 파서가 원본 수치 열을 해석하지 못했습니다: {column}"
                )
    return labels.enrich(frame)
