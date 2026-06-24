from __future__ import annotations

from ai_strategy_loop.tmap.template import (
    coordinate_points,
    load_template,
    render,
    validate_rendered,
)


def test_tick_late_0920_0925_template_renders_valid_points() -> None:
    template = load_template("tick_late_0920_0925_continuation")

    assert template.timeframe == "tick"
    buy, sell = render(template)
    assert "92000 <= 시분초 < 92500" in buy
    assert validate_rendered(buy, sell, template.timeframe) == []

    for point in coordinate_points(template):
        buy_code, sell_code = render(template, point["theta"])
        assert validate_rendered(buy_code, sell_code, template.timeframe) == []


def test_min_session_0900_1500_template_caps_entry_and_exit_at_1500() -> None:
    template = load_template("min_session_0900_1500_rotation")

    assert template.timeframe == "min"
    assert template.param("entry_end").default <= 150000
    assert max(template.param("entry_end").values) <= 150000
    assert template.param("force_exit_time").default == 150000

    buy, sell = render(template)
    assert "90000 <= 시분초 <= {entry_end}" not in buy
    assert "시분초 >= 150000" in sell
    assert validate_rendered(buy, sell, template.timeframe) == []

    for point in coordinate_points(template):
        buy_code, sell_code = render(template, point["theta"])
        assert validate_rendered(buy_code, sell_code, template.timeframe) == []
