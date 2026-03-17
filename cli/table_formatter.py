"""터미널 테이블 포맷터 — 외부 의존성 없이 컬럼 정렬 + 값 truncation."""

from __future__ import annotations


def format_table(rows: list[dict], columns: list[tuple[str, str, int]],
                 max_width: int = 120) -> str:
    """딕트 리스트를 터미널 테이블 문자열로 포맷한다.

    Args:
        rows: 출력할 데이터 행 목록.
        columns: [(key, header_label, min_width), ...] 정의.
        max_width: 테이블 전체 최대 폭 (문자 수).

    Returns:
        정렬된 터미널 테이블 문자열.
    """
    if not rows or not columns:
        return '(no data)'

    # 각 컬럼 실제 너비 계산: max(min_width, header_len, 최대 값 길이)
    col_widths = []
    for key, header, min_w in columns:
        w = max(min_w, len(header))
        for row in rows:
            val = _truncate(str(row.get(key, '')), 40)
            w = max(w, len(val))
        col_widths.append(w)

    # max_width 내로 축소
    total = sum(col_widths) + len(columns) * 3 + 1  # borders: | col | col |
    if total > max_width and col_widths:
        excess = total - max_width
        # 가장 넓은 컬럼부터 줄임
        while excess > 0:
            idx = col_widths.index(max(col_widths))
            shrink = min(excess, col_widths[idx] - columns[idx][2])
            if shrink <= 0:
                break
            col_widths[idx] -= shrink
            excess -= shrink

    # 헤더
    header_cells = []
    for i, (_, header, _) in enumerate(columns):
        header_cells.append(f' {header:<{col_widths[i]}} ')
    header_line = '|' + '|'.join(header_cells) + '|'
    sep_line = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'

    lines = [sep_line, header_line, sep_line]

    # 데이터 행
    for row in rows:
        cells = []
        for i, (key, _, _) in enumerate(columns):
            val = _truncate(str(row.get(key, '')), col_widths[i])
            cells.append(f' {val:<{col_widths[i]}} ')
        lines.append('|' + '|'.join(cells) + '|')

    lines.append(sep_line)
    return '\n'.join(lines)


def _truncate(value: str, max_len: int) -> str:
    """값이 max_len을 초과하면 잘라내고 '...'을 붙인다."""
    if len(value) <= max_len:
        return value
    if max_len <= 3:
        return value[:max_len]
    return value[:max_len - 3] + '...'
