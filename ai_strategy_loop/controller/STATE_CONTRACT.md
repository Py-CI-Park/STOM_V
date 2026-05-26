# STATE_CONTRACT — 루프 ↔ 대시보드 상태 계약 (US-007)

> **CONTRACT_VERSION = 1**
> 정본 스키마: `ai_strategy_loop/controller/contract.py` (`LoopState` pydantic 모델)

## 목적

헤드리스 진화 루프(`controller/loop.py`)와 대시보드(`dashboard/app.py`)는
**서로 다른 프로세스**다. 루프는 대시보드가 띄운 서브프로세스이거나 CLI에서
독립 실행되며, 대시보드는 FastAPI/uvicorn 프로세스다. 둘을 잇는 유일한 seam이
이 상태 계약이다.

루프는 진행 상황을 단일 JSON 파일
`ai_strategy_loop/state/current_state.json`에 **atomic write** 한다.
대시보드는 그 파일을 읽어(`GET /status`) 보여주고, 변경을 폴링해
WebSocket(`/ws`)으로 push 한다.

## 버전 규칙

- `contract_version`은 모든 스냅샷에 박혀 나간다 (`CONTRACT_VERSION` 상수).
- 필드 **제거/타입 변경/의미 변경**(깨는 변경)은 `CONTRACT_VERSION`을 +1 한다.
- 필드 **추가**(기존 소비자가 무시 가능)는 버전을 올리지 않아도 된다 (pydantic은
  알 수 없는 키를 기본 무시, 누락 필드는 기본값으로 채운다).

## LoopState 스키마 (v1)

| 필드 | 타입 | 설명 |
|------|------|------|
| `contract_version` | int | 항상 `CONTRACT_VERSION` (현재 1) |
| `run_id` | str \| null | 현재(또는 마지막) run id |
| `status` | str | `idle` \| `running` \| `stopping` \| `complete` \| `error` |
| `current_gen` | int | 현재 진행 중인 세대 번호 (없으면 -1) |
| `max_generations` | int | 세대 수 상한 (LoopConfig.max_generations) |
| `provider` | str | LLM provider (gpt_auth \| openrouter \| codex_proxy) |
| `bt_timeframe` | str | 백테스트 타임프레임 (min \| tick) |
| `best` | object | GRADED 최고 세대 (선택 그래디언트) — 아래 BestInfo |
| `winner` | object \| null | 하드 게이트 통과 우승 세대 — 아래 WinnerInfo. 통과 세대 없으면 null |
| `generations` | list | 세대별 요약 행 리스트 — 아래 GenerationInfo |
| `latest` | object | 현재 단계/백테스트 진행 상태 — 아래 LatestInfo |
| `cumulative` | object | 누적 비용/사용량 — 아래 CumulativeInfo |
| `updated_at` | float | 마지막 갱신 epoch 초 |

### BestInfo (`best`)
| 필드 | 타입 | 설명 |
|------|------|------|
| `gen` | int | best 세대 번호 (없으면 -1) |
| `graded_score` | float \| null | GRADED 점수 |
| `gate_passed` | bool | 그 세대가 하드 게이트를 통과했는지 |
| `buy_name` | str \| null | best 매수 전략 이름 (namespaced) |
| `sell_name` | str \| null | best 매도 전략 이름 (namespaced) |

### WinnerInfo (`winner`, null 가능)
| 필드 | 타입 | 설명 |
|------|------|------|
| `gen` | int | 우승 세대 번호 |
| `score` | float \| null | 하드 composite 점수 |
| `buy_name` | str \| null | 우승 매수 전략 이름 |
| `sell_name` | str \| null | 우승 매도 전략 이름 |

### GenerationInfo (`generations[]`)
| 필드 | 타입 | 설명 |
|------|------|------|
| `gen_no` | int | 세대 번호 |
| `status` | str | `ok` \| `error` \| `running` |
| `graded_score` | float | GRADED 점수 |
| `gate_passed` | bool | 하드 게이트 통과 여부 |
| `gate_reason` | str | 게이트 사유/거리 |
| `trade_count` | int | 거래 수 |
| `daily_avg_trades` | float | 일평균거래횟수(거래수/거래일수) — 빈도 게이트 주 기준 |
| `mdd` | float | MDD(%) |
| `profit` | float | 총 손익 |
| `strategy_gist` | str | 전략 핵심 한 줄 요약 |

### LatestInfo (`latest`)
| 필드 | 타입 | 설명 |
|------|------|------|
| `phase` | str | `backtest_start` \| `backtest_end` \| `generation_done` 등 |
| `last_checkpoint` | str | 백테스트 진행 체크포인트 |
| `message` | str | 사람이 읽을 진행 메시지 |

### CumulativeInfo (`cumulative`)
| 필드 | 타입 | 설명 |
|------|------|------|
| `tokens` | int | 누적 토큰 (집계 가능한 provider) |
| `cost_or_count` | int | 토큰 합산 불가 provider(gpt_auth)에선 세대 수 = 비용 프록시 |

## 라이브 발행 시점 (루프 → 파일)

`controller/state.py: publish_loop_state()`가 `current_state.json`에 atomic
write 한다. `controller/loop.py`는 다음 시점에 발행한다:

1. **백테스트 시작 직전** — `latest.phase = "backtest_start"`
2. **백테스트 종료 직후** — `latest.phase = "backtest_end"`
3. **세대 기록 후** — `latest.phase = "generation_done"`, generations 갱신
4. **종료 시** — `status = complete | error`

## 제어 (대시보드 → 루프)

- **start**: 대시보드가 `python -m ai_strategy_loop.controller.loop ...` 를
  서브프로세스로 띄운다 (기동 전 STOP 플래그 제거).
- **stop**: 대시보드가 STOP 플래그 파일
  `ai_strategy_loop/state/STOP` 를 쓴다. 루프는 매 세대 시작 전 이 파일을
  확인하고, 있으면 `status=stopping → complete`로 깔끔히 종료한다.
- **final_approval**: 대시보드가 `export.export_winner(...)`를 호출해
  우승 전략을 운영 strategy.db로 export 한다 (사람 승인 게이트).

## Atomic write 규약

`publish_loop_state()`는 같은 디렉토리에 `*.tmp`로 쓰고 `os.replace()`로
교체한다 — 부분 쓰기(half-written JSON)를 폴링 reader가 읽는 일을 막는다.
