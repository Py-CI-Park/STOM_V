"""Full official raw-column fixtures, separate from normalized trade projections."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path


def feature_csv(path: Path, *, legacy: bool = False, minute: bool = False) -> Path:
    header, row = official_pair(legacy=legacy)
    columns = header.strip().split(",")
    base = dict(zip(columns, next(csv.reader([row.strip()]))))
    names = ["NA", '인용 "이름"', "쉼표,이름", "줄\r\n바꿈"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for i in range(40):
            values = dict(base)
            buy = f"2025040709{1 + i % 15:02d}00"
            sell = f"2025040709{2 + i % 15:02d}00"
            values.update(
                {
                    "종목명": names[i % len(names)],
                    "매수시간": buy[:12] if minute else buy,
                    "매도시간": sell[:12] if minute else sell,
                    "보유시간": "1" if minute else "60",
                    "시가총액": str(2500 + (i % 2) * 10000),
                    "수익률": "1" if i % 2 else "-1",
                    "수익금": "100" if i % 2 else "-100",
                    "B_현재가": str(10000 + i),
                    "B_등락율": str(1 + i % 10),
                    "B_체결강도": str(80 + i),
                    "B_매수총잔량": str(100 + i),
                    "B_매도총잔량": "100",
                    "R_MFE": "2.5",
                }
            )
            if "B_RSI" in values:
                values["B_RSI"] = "" if i % 5 == 0 else str(i)
            writer.writerow(values)
    return path


def revision_csv(path: Path) -> Path:
    """Official version of the existing two-leaf proposer test distribution."""
    header, row = official_pair()
    columns = header.strip().split(",")
    base = dict(zip(columns, next(csv.reader([row.strip()]))))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for group in range(2):
            for i in range(80):
                win = i < (20 if group == 0 else 60)
                values = dict(base)
                values.update(
                    {
                        "종목명": "X" if group == 0 else "Y",
                        "시가총액": "1000" if group == 0 else "12000",
                        "매수시간": f"2025040709{i % 2:02d}{5 + group * 30:02d}",
                        "매도시간": f"2025040709{1 + i % 2:02d}{5 + group * 30:02d}",
                        "보유시간": "60",
                        "수익률": "1" if win else "-1",
                        "수익금": "1000" if win else "-1000",
                        "B_현재가": "10000" if group == 0 else "50000",
                        "B_등락율": "5" if group == 0 else "3",
                        "B_매수총잔량": "100",
                        "B_매도총잔량": "100",
                        "B_당일거래대금": "100" if group == 0 else "900",
                        "B_시가총액": "1000" if group == 0 else "12000",
                        "B_체결강도": "100",
                        "B_전일동시간비": str(
                            ((2.0 if win else 0.2) if group == 0 else 1.0) + i * 1e-3
                        ),
                    }
                )
                writer.writerow(values)
    return path
