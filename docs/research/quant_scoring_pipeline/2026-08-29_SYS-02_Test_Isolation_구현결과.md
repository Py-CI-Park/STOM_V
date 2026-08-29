# SYS-02 Test Isolation 구현 결과

> 완료일: 2026-08-29
>
> 구현 브랜치: `codex/process-research-sys-02-test-isolation`
>
> 구현 커밋: `8e5fc501`
>
> 결론: **없는 seed DB를 테스트가 생성하지 않도록 read-only/fail-closed guard를 도입했다. 전체 unit suite는 7,946 PASS로 복구됐고, 추가로 발견한 `/strategy_code` 읽기 side effect도 SQLite `mode=ro`로 제거했다.**

---

## 1. Status Dashboard

```text
┌──────────────────────────────────────────────────────────────┐
│ SYS-02 TEST ISOLATION                                      │
├─────────────────────────┬────────────────────────────────────┤
│ Full Unit Suite         │ 7,946 PASS                        │
│ Skipped                 │ 27                                │
│ Failed                  │ 0                                 │
│ Warnings                │ 54                                │
│ Runtime                 │ 5,376.43s · 1h 29m 36s           │
├─────────────────────────┼────────────────────────────────────┤
│ _database/strategy.db   │ NOT CREATED                       │
│ Seed-dependent cases    │ 14 explicit SKIP                  │
│ Read path regression    │ PASS · file creation 0           │
│ pytest plugin conflict  │ REFUTED                           │
└─────────────────────────┴────────────────────────────────────┘
```

---

## 2. Red→Green Flow

```text
BEFORE
missing seed DB
    │
    └── sqlite3.connect(path)
            │
            ├── 0-byte DB 생성
            └── no such table 실패

AFTER
missing seed DB
    │
    └── open_seed_database(mode=ro)
            │
            ├── 파일 생성 없음
            └── 명시적 environment SKIP
```

```text
/strategy_code read path
    │
    ├── 수정 전: test PASS + loop_strategies.db 0-byte 생성
    └── 수정 후: test PASS + 파일 생성 없음
```

---

## 3. 구현

| 파일 | 변경 |
|---|---|
| `tests/seed_db_guard.py` | SQLite URI `mode=ro`, required table 확인, 부재 시 SKIP |
| `test_seed_db_guard.py` | missing/table missing/valid readonly/source guard 계약 |
| `test_filter_gate.py` | 실제 loop seed를 guard로 조회 |
| `test_time_window.py` | 실제 loop seed를 guard로 조회 |
| `test_w7_champion_clauses.py` | 운영 strategy DB를 guard로 조회 |
| `test_w7_condition_diff.py` | 운영 strategy DB를 guard로 조회 |
| `loop.py` | code/gist/head 읽기 3경로를 SQLite `mode=ro`로 전환 |
| `test_research_pro.py` | `/strategy_code` missing DB non-creation 통합 회귀 |

---

## 4. 검증 결과

| Gate | 결과 |
|---|---|
| guard 단위 | 4 passed |
| seed-dependent actual | 14 skipped · exit 0 |
| guard + API integration | 5 passed |
| guard + UX-05 집중 | 10 passed 당시 확인 |
| strict quality | Ruff PASS · pyright 0 · no-excuse 0 |
| `/strategy_code` 수정 전 | 1 PASS · 0-byte DB 생성 |
| `/strategy_code` 수정 후 | 1 PASS · DB 생성 없음 |
| 전체 unit | 7,946 passed · 27 skipped · 54 warnings |

전체 unit suite는 seed guard 적용 후 실행했고 green이었다. 그 실행에서 `/strategy_code` 읽기 side effect가 만든 transient zero-byte loop DB를 발견했다. 이후 제품 read path를 수정하고 집중 회귀로 파일 생성 0을 확인했다. 최종 3-line read-only 변경 뒤 89분 전체 suite는 반복하지 않았다.

---

## 5. pytest plugin 재검토

```text
초기 현상
UX-05 test → 간헐적 process -1

재검토
├── anyio 제외 ............ 4 PASS
├── pytest-mock 제외 ...... 4 PASS
├── pytest-qt 제외 ........ 4 PASS
├── pytest-timeout 제외 ... 4 PASS
└── 전체 plugin 정상 재시도 4 PASS
```

특정 plugin을 끄면 고쳐지는 결정적 충돌은 재현되지 않았다. 현상은 일시적 호스트 프로세스 종료로 정정하고 plugin 제거·설정 변경을 하지 않았다.

---

## 6. 남은 품질 부채

```text
Full suite duration ........ 89m 36s
Trade-path ordering ........ isolated PASS, 과거 suite flake 1회
Warnings ................... 54
```

다음 단계는 trade-path가 `status=success`를 공개하기 전에 `analysis_success` ledger를 확정하도록 결정적 계약을 만드는 것이다.
