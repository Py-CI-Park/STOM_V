# 측정계 보정 감사 (B2) — MDD·거래수 정의와 기준 이식성 (2026-06-10)

> 목적: "선택 기준이 시드조차 탈락시킨다"(원인1)의 수치 근거를 코드 수준에서 확정하고,
> seed_relative_v1 임계값의 정당성을 문서화한다. 읽기 전용 감사 — 엔진/지표 코드 무수정.

## 1. MDD 산출 정의 (코드 실측)

`backtest/back_static.py:682 AddMdd` (엔진 공식 산출, 모든 백테 결과 공통):

```python
array = 수익금합계            # 거래별 누적 수익금 곡선 (원)
lower = argmax(cummax(array) - array)   # 최심 낙폭의 저점 인덱스
upper = argmax(array[:lower])           # 그 직전 피크 인덱스
mdd   = |array[upper] - array[lower]| / (array[upper] + seed) * 100
mdd_  = |array[upper] - array[lower]|   # 낙폭 금액(원)
```

- `seed` = GetResult가 산출한 **필요자금 추정치**(배팅 단위 × 동시보유 규모에 비례).
- 즉 **MDD% = 낙폭금액 / (피크 시점 평가자본)** — 계좌 기준 정의로서 타당하다.
- 루프 metrics의 `mdd` = 이 `최대낙폭률`을 `cli/runner._extract_metrics`가 그대로 사용
  (`mdd_pct: row['최대낙폭률']`).

## 2. 핵심 발견 — 같은 공식, 다른 분모: 절대 MDD 기준은 포지션 레짐 간 이식 불가

| 전략 유형 | 동시보유 | seed(분모) 규모 | 같은 100만원 낙폭의 MDD% |
|---|---|---|---|
| 시드(Tick_902/905, 1포지션 니치) | ~1 | ~5백만(배팅 5M) | **~17~20%** |
| 17개 우수전략(보고서) | 6~12 | ~30~60백만 | **~1.7~3.3%** |

- 2026-06-10 train 실측: 시드 MDD 17.44%(낙폭금액 기준 ~백만원대) — 17개 우수전략
  문서의 MDD 1.9~6.75%와 **같은 엔진·같은 공식**이되 분모가 6~12배 다르다.
- 따라서 `sparse_positive_v1`의 `MDD<=10` 절대 기준은 (a) 다포지션 분산 전략 기준으로는
  자연스럽지만 (b) 1포지션 니치 전략에는 **시드조차 통과 불가한 기준**이 된다.
  이것이 원인1("기준-목표 비정합")의 수치적 메커니즘이다.
- 같은 이유로 거래수 회랑(20~250/3년)도 분산 전략 프레임(일평균 10~23회)과 니치 프레임
  (시드 0.4회/일=3년 307건)을 섞은 비정합 값이었다.

## 3. 함의

1. **seed_relative_v1 정당화**: MDD 한도를 같은 측정계의 시드 프로파일에 상대화
   (`max(20, 시드MDD×1.1)`)하고 거래 회랑을 50~400으로 보정한 것은 측정 정의상 옳다.
2. **MDD%를 실제로 낮추는 구조 레버는 분산(동시보유↑)**: 같은 낙폭금액이라도 분모가
   커진다. Track B(분산매매 토글: dispersion_*)가 이미 이 방향이며, 우수전략의 낮은
   MDD는 상당 부분 6~12 동시보유의 산물이다.
3. **비교 보고 시 단위 명시**: 결정 카드/대시보드에서 MDD%와 함께 낙폭금액(`mdd_`)을
   병기해야 레짐 간 오독을 막는다(후속 개선 후보 — 현재 metrics에 mdd_amount=0.0 고정,
   `cli/runner.py:702`).
4. 일평균거래수 정의 = 거래수/거래일수(루프 metrics) — 우수전략 문서의 "일평균 10~23"과
   동일 정의이므로 그대로 비교 가능(프레임만 다름).

## 4. 검증 재현 명령

```powershell
# 시드 train 행(2026-06-10) 수치 확인
PYTHONUTF8=1 python - <<'PY'
import sqlite3
con = sqlite3.connect(r'ai_strategy_loop/state/loop_runs.db')
row = con.execute("SELECT mdd, trade_count, profit FROM generations"
                  " WHERE run_id='cldgen_train_2023_2025_20260610' AND gen_no=0").fetchone()
print('seed train mdd/trades/profit =', row)
PY
```
