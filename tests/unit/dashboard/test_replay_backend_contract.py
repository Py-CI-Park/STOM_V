from __future__ import annotations

from typing import Any

import anyio
import pytest
from pydantic import ValidationError

from ai_strategy_loop.dashboard import replay_engine as replay
from ai_strategy_loop.dashboard import simulation_api as simulation


def _frames() -> list[dict[str, Any]]:
    return [
        {"t": 90000, "items": [{"code": "005930", "c": 100.0}]},
        {"t": 90100, "items": [{"code": "005930", "c": 101.0}]},
        {"t": 130000, "items": [{"code": "005930", "c": 102.0}]},
    ]


class _RecordingWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.messages.append(payload)


def test_elapsed_time_uses_validated_clock_seconds_across_market_gap() -> None:
    # Given: frames separated by a morning-to-afternoon market gap.
    data = replay.ReplayData(20250102, "min", ["005930"], _frames(), (90000, 130000))

    # When: the authoritative elapsed time is queried at the last frame.
    elapsed = data.elapsed_seconds_at(2)

    # Then: it is the real four-hour clock gap, not HHMMSS subtraction or a clamp.
    assert elapsed == 14_400


@pytest.mark.parametrize("timestamps", [[96000], [90100, 90000], [90000, 90000]])
def test_replay_timeline_rejects_malformed_or_non_monotonic_timestamps(
    timestamps: list[int],
) -> None:
    # Given: a malformed, reversed, or duplicate replay timeline.
    frames = [{"t": timestamp, "items": []} for timestamp in timestamps]

    # When / Then: construction fails closed before a replay can start.
    with pytest.raises(replay.ReplayTimelineError):
        replay.ReplayData(20250102, "min", ["005930"], frames, (0, 0))


def test_seek_index_replaces_history_through_the_exact_target_frame() -> None:
    # Given: a loaded replay and an empty client-side history sink.
    websocket = _RecordingWebSocket()
    session = simulation.SimReplaySession(websocket)
    session.data = replay.ReplayData(
        20250102,
        "min",
        ["005930"],
        _frames(),
        (90000, 130000),
    )

    # When: the client seeks to actual frame index 2.
    accepted = session.handle_seek_index(2)
    anyio.run(session._send_history)

    # Then: the replacement includes frame 2 and reports authoritative position metadata.
    assert accepted is True
    assert websocket.messages == [
        {
            "type": "history",
            "index": 2,
            "frame_count": 3,
            "t": 130000,
            "elapsed_seconds": 14_400,
            "items_by_code": {
                "005930": [
                    {"code": "005930", "c": 100.0, "t": 90000},
                    {"code": "005930", "c": 101.0, "t": 90100},
                    {"code": "005930", "c": 102.0, "t": 130000},
                ],
            },
        },
    ]


def test_seek_index_rejects_non_frame_end_sentinel() -> None:
    # Given: a three-frame replay.
    session = simulation.SimReplaySession(_RecordingWebSocket())
    session.data = replay.ReplayData(
        20250102,
        "min",
        ["005930"],
        _frames(),
        (90000, 130000),
    )

    # When: the caller supplies bars_total, which is a count rather than a frame index.
    accepted = session.handle_seek_index(session.data.bars_total)

    # Then: the request fails closed and leaves the live cursor unchanged.
    assert accepted is False
    assert session.cursor == 0


@pytest.mark.parametrize("index", [True, False, -1, 10_000_001, 1.0, "1"])
def test_seek_index_boundary_accepts_only_a_strict_bounded_integer(index: Any) -> None:
    # Given: an untrusted WebSocket control payload.
    payload = {"action": "seek_index", "index": index}

    # When / Then: bools, coercible values, and global out-of-range values are rejected.
    with pytest.raises(ValidationError):
        simulation._REPLAY_CONTROL_ADAPTER.validate_python(payload)


@pytest.mark.parametrize("timestamp", [96000, 236000, -1, True, "090000"])
def test_seek_time_boundary_rejects_malformed_hhmmss(timestamp: Any) -> None:
    # Given: an untrusted seek action with a malformed or coercible clock value.
    payload = {"action": "seek", "t": timestamp}

    # When / Then: parsing fails before the replay timeline can be mutated.
    with pytest.raises(ValidationError):
        simulation._REPLAY_CONTROL_ADAPTER.validate_python(payload)


def test_seek_in_one_session_does_not_mutate_an_unrelated_live_session() -> None:
    # Given: independent archive/display and live replay sessions over immutable data.
    data = replay.ReplayData(20250102, "min", ["005930"], _frames(), (90000, 130000))
    archive_session = simulation.SimReplaySession(_RecordingWebSocket())
    live_session = simulation.SimReplaySession(_RecordingWebSocket())
    archive_session.data = data
    live_session.data = data
    live_session.cursor = 1
    live_session.running = True

    # When: the archive/display session seeks elsewhere.
    accepted = archive_session.handle_seek_index(2)

    # Then: the unrelated live run retains its cursor and lifecycle state.
    assert accepted is True
    assert live_session.cursor == 1
    assert live_session.running is True
