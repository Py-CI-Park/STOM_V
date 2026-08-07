# P1 A/B 대조 실험 — 사전등록서 (2026-06-15, 실행 전 동결)

> 목적: 무작위 생성(무상태) vs 폐루프 생성(유상태)을 비교해 **"데이터 천장 vs 프로세스 부족"**을
> 가른다. ★실행 *전*에 아래를 동결(데이터 엿보기 차단). 변경 시 날짜·사유 명기.

## 1. 두 arm (동일 조건)
| arm | 명령 | 차이 |
|---|---|---|
| **A 무작위(대조)** | `tmap_multiband_discovery.py --max-iters N` (--stateful 없음) | 직전 결과 미환류(현 야간 동작) |
| **B 폐루프(처치)** | `tmap_multiband_discovery.py --max-iters N --stateful` | ledger 회피/선호 환류 |

동일: 트랙 로테이션(tick_new·tick_anchor·min_new)·config(스모크→전체기간→OOS 격상)·게이트(P0b)·seed 환경. **유일 차이 = --stateful**.

## 2. ★합격 지표 (OOS 단일 — R3 자기채점 차단)
- **합격 판정 = OOS PROMISING 수**(전체기간+OOS 통과, 같은 좌표). baseline = 무작위 arm(현재 0/40).
- **최소검출효과 N**: 폐루프 arm PROMISING ≥ **1**(무작위 0 대비) → "폐루프 우위" 합격 → P3~P5 진행.
- min 트랙은 OOS 오염(min-fullsession이 2026 포함)이라 **honest 합격 카운트는 tick 트랙 한정**. min은 진행 지표 참고만.

## 3. ★대리지표 (진행만 게이트 — 합격 아님). [A2] valid-attempt당 *rate*
- **valid-attempt 정의** = generate 성공 + 스모크 진입(evaluate 도달). gen-fail·0신호는 분모 제외.
- **3 대리지표(rate)**:
  - smoke-pass率 = (verdict∈{smoke-pass,train-pass,train-only,★PROMISING}) / valid-attempt
  - near-miss率 = (q1>0 XOR q2>0, 한쪽만 흑자) / valid-attempt
  - 홍수개선率 = (q1 best가 직전 동트랙 대비 덜 음전/양전) / valid-attempt
- ★**철칙**: 대리지표(rate)는 *진행*만 게이트. **OOS 0이면 대리지표 우위여도 천장선언 금지**(C3로만).
- ★**raw count 금지**: arm 간 valid-attempt 분모가 다르므로 반드시 rate 비교(throughput 교란 차단).

## 4. ★메타 정지규칙 (C3 — 천장선언 트리거)
- "데이터 천장" 선언 = **`P0b 통과(✅ 완료) ∧ 대리지표 rate K회 연속 평탄(우위 무) ∧ OOS PROMISING 0`** AND.
- **K = 3** (연속 3 비교창서 폐루프 rate 우위 무 = 평탄). **평탄 임계 = rate 차 < 0.05**(절대).
- 충족 시: 시계열 규칙탐색 종결 → §10 횡단면([승인필요])로 결론 이관. 미충족(진행 중): P2 코어 정제 계속.
- 양극단 차단: 1회 0에 성급 천장선언 금지 / rate 우위 지속 시 무한재실행 금지(K=3 평탄이면 종료).

## 5. 표본수 n (pilot → full)
- **pilot**: arm당 **n=8** (기계 작동 + 조기 rate 신호 확인용, ~arm당 2~3h). pilot은 *합격 판정 불가*(underpowered) — 대리지표 rate 방향성만.
- **full**: arm당 **n=40** (야간). 합격(OOS≥1)·C3 판정은 full에서만.
- pilot에서 폐루프 rate가 무작위보다 *나쁘면* full 보류(기계 결함 점검).

## 6. 동결 상수 요약
| 상수 | 값 |
|---|---|
| 합격 지표 | OOS PROMISING 수(tick 한정) |
| MDE N | ≥1 (무작위 0 대비) |
| 대리지표 | valid-attempt당 rate 3종(§3) |
| K (평탄 연속) | 3 |
| 평탄 임계 | rate 차 < 0.05 |
| n (pilot/full) | 8 / 40 |
| config | 스모크 2분기 → 전체기간 → OOS (격상) |

## 7. 결정규칙 (실행 후)
1. 폐루프 OOS PROMISING ≥1 (무작위 0) → **합격, P3~P5 진행**.
2. 둘 다 OOS 0 ∧ 대리지표 rate K=3회 평탄 → **C3 천장선언 → 횡단면 이관**.
3. 둘 다 OOS 0 ∧ 폐루프 rate 우위(K 미달) → **천장선언 금지, P2 코어 계속 정제**.
4. 폐루프 rate가 무작위보다 나쁨 → **P2 코어 결함 점검**(환류 배선 수정).
