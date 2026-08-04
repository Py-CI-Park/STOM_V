# G-0c/0d/0e — 페이지 17~21 · 평가 프로토콜 v2 배선 · 세대 수렴 판정

> 작성일: 2026-08-04
> 브랜치: `feature/qsp7-g0-loss-region-engine-20260803`
> 선행: [G-0a 프로파일러](./2026-08-04_qsp7_g0a_loss_profile_evidence.md) · [G-0b 생성기](./2026-08-04_qsp7_g0b_region_proposer_evidence.md)

---

## 1. 🧭 한 줄 결론

엔진(G-0a/0b)이 화면과 API 로 이어졌고, **후보당 백테스트를 2회에서 1회로 줄이는 v2 분할
판정**이 게이트까지 배선됐다. 화면 5개 신설 + 채택 게이트 2모드화로 **21페이지 전부 구현**됐다.

---

## 2. 🔌 API 6종 (`ai_strategy_loop/dashboard/loss_region_api.py`)

| 메서드 | 경로 | 권위 | 반환 |
|---|---|---|---|
| GET | `/bt/trade-path/loss-profile` | 진단 | 변수별 분위·형태·최악구간·파레토 |
| GET | `/bt/trade-path/loss-pockets` | 진단 | 2D 포켓·FDR·연속성 |
| POST | `/bt/trade-path/removal-simulate` | 자문 | 유지율·건당 개선·예산·STOM 코드 미리보기 |
| POST | `/bt/trade-path/region-candidates` | 자문 | 복합 제거 후보 N개(절·근거·예산) |
| GET | `/bt/trade-path/generations` | 정본 | 세대 이력·수렴 판정·롤백 대상 |
| GET | `/bt/trade-path/split-diagnostics` | 정본 | 구간 분할 요약 + **검산** |

- POST 2종은 `SAFE_BACKTEST` 권한 테이블에 등재했다.
- 분할 경계 기본값은 `lane_manifest.split_boundary` 에서 온다 — 화면에 수기 입력 경로를 두지 않는다.
- 런 CSV 는 (경로, mtime) 키로 2개까지 캐시한다. 86,390행을 요청마다 다시 읽지 않기 위함이다.

### 2.1 실서버 확인 (127.0.0.1:8771)

| 호출 | 결과 |
|---|---|
| `lane-manifest?lane=tick` | 200 · `evaluation_protocol=v2_single_run_date_split` · split 20250825 · eval 20240304~20260227 |
| `generations?lane=tick` | 200 · `verdict=not_started` · "아직 세대가 없습니다." |
| `loss-profile?job_id=nope` | 200 · `available=false` · `backtest_result_missing` (예외 아님) |

---

## 3. 🖥️ 화면 5개 신설 + 2개 강화

| # | 파일 | 핵심 시각 요소 |
|---:|---|---|
| 17 | `bt-loss-profile.jsx` | 10분위 막대 2줄(설계·홀드아웃) · 형태 배지 6색 · 최악 구간 하이라이트 · 표본부족 빗금 · 파레토 전선 |
| 18 | `bt-loss-pockets.jsx` | 10×10 위치 격자 · 포켓별 q·낭비·제거율 · 변수쌍 재탐색 |
| 19 | `bt-removal-sim.jsx` | 제거 장바구니 · 유지율 게이지(40% 하한선) · 건당 델타 · **STOM 코드 미리보기** · **후보 자동 생성** |
| 20 | `bt-generation-curve.jsx` | 세대별 건당 2선 · 추가 개선폭 막대 · 누적 유지율 · 수렴/발산/예산소진 배지 · 롤백 안내 |
| 21 | `bt-split-diagnostics.jsx` | 분할 타임라인 · 구간 카드 3장 · **검산 표시** · 기존 `/bt/analysis/*` 구간별 열기 |
| 8b | `bt-removal-sim.jsx` 내 자동 후보 | 복합 묶음 + 절별 근거(카드 출처) 표시 |
| 11 | `bt-oos-gate.jsx` | **v2 분할 / 4-job 독립 2모드** · 홀드아웃 명칭 · 검산 표시 · 자본 연속 경고 |

시각화 규율: 손실=적색, 이익=청록, 표본부족=회색 빗금, 권위 배지 상시, 시뮬레이터에는
**"재유입 미반영 · 순위용"** 고정 노출. 새 차트 라이브러리는 도입하지 않았다.

---

## 4. 📐 평가 프로토콜 v2 배선 (G-0d)

### 4.1 무엇이 바뀌었나

| | v1 | **v2** |
|---|---|---|
| 후보당 백테스트 | 2회(설계 런 + OOS 런) | **1회** |
| 구간 | 별도 job | **CSV 날짜 분할** |
| 명칭 | OOS | **홀드아웃** |
| 판정 | 총손익 + 건당 | **건당 중심** |

### 4.2 계약 변경

| 경로 | 변경 |
|---|---|
| `POST /bt/trade-path/official-pair` | `period: {t_start, t_end} \| null` 추가 — 지정 시 해당 기간 거래만 비교 |
| `POST /bt/trade-path/promotion-gate` | **2-job 모드** 추가. 4-job 모드는 회귀 없이 유지. 두 모드를 섞어 보내면 422 |

### 4.3 검산을 게이트에 넣었다

2-job 모드는 설계·홀드아웃 외에 **전체 런** pair 를 한 번 더 계산해
`설계 거래수 + 홀드아웃 거래수 == 전체 거래수` 를 확인한다. 어긋나면 `split_does_not_reconcile`
로 **차단**한다. 분할이 구간을 빠뜨리면 판정 자체가 무의미하기 때문이다.

실데이터 확인: tick 86,390 = 설계 69,034 + 홀드아웃 17,356 ✅

---

## 5. 🔁 세대 수렴 판정 (G-0e, `revision/generation_runner.py`)

| 판정 | 규칙 |
|---|---|
| `converged` | 홀드아웃 건당 개선이 **3세대 연속 50원 미만** |
| `budget_exhausted` | 누적 유지율 < 40% (다른 판정보다 우선) |
| `diverged` | 홀드아웃 건당이 **2세대 연속 악화** → 직전 세대로 롤백 |

- 판정 입력은 **홀드아웃 건당 손익**이다. 총손익은 거래를 줄이기만 해도 좋아진다.
- 이력은 JSONL 추가 전용이다. 손상된 줄은 건너뛰고 나머지를 읽는다.

---

## 6. 🐛 이번 단계에서 잡은 문제

| # | 문제 | 조치 |
|---:|---|---|
| 1 | `FrozenPayload` 가 strict 라 JSON 배열이 튜플로 변환되지 않아 시뮬레이터가 422 | 기존 모델과 같은 `mode="before"` 검증기 추가 |
| 2 | 화면 계약 테스트가 옛 버튼 문구를 고정하고 있어 v2 2모드 도입 시 실패 | 문구가 아니라 **계약**(두 모드 존재·홀드아웃 명칭·검산 표시)을 검사하도록 갱신 + 테스트 1건 신설 |
| 3 | 세션 쿠키가 `/bt/jobs` 로는 발급되지 않음(BOOTSTRAP_PATHS 한정) | 클라이언트 부트스트랩을 `/ui/v4` 로 교정 — G-1 실행 절차에 기록 |

---

## 7. ✅ 검증

| 항목 | 값 |
|---|---|
| QSP7 집중 테스트 | §8 참조 (G-0b 기준선 1,085 + 신규) |
| nonrelease verifier | PASS |
| runtime JSX | **PASS 118 JSX / 568 files** (기존 113/563 + 신규 5) |
| 실서버 QA | 신규 GET 3종 200 · 미존재 job 은 예외 없이 사유 반환 |
| 실데이터 v2 분할 | 86,390 = 69,034 + 17,356 검산 통과 · 후보 4건 재현 동일 |

---

## 8. 📌 남은 것

| 단계 | 내용 |
|---|---|
| G-1 | tick 기준선 공식 런(진행 중) → 1세대 후보 4개 공식 실측 |
| G-2~G-4 | 2~4세대 |
| G-5 | `rounds/G_tick_20260804.md` |
