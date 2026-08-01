# 핸드오프 — QSP7 매도식 연구 (2026-08-01)

> **이 문서 하나로 이어받을 수 있게 쓴다.** 대화 맥락 없이 읽어도 무엇을 왜 하는지,
> 어디부터 손대면 되는지, 어떤 함정이 있는지 알 수 있어야 한다.
>
> - 브랜치: `feature/qsp3-map-surgery-20260731` (worktree `STOM_V.wt-dev`)
> - 부모: `loop/process-research-pipeline` — **2U_C 로 가지 않는다. main 병합 금지.**
> - 직전 커밋: `54273759 research(손실 해부)` — 이 문서는 그 다음 작업의 출발점이다.
> - 최신 설계 보정: [`2026-08-01_qsp7_trade_episode_exit_research_system_design.md`](./2026-08-01_qsp7_trade_episode_exit_research_system_design.md) — 손절 변형 착수 전에 거래 에피소드·잔여경로·반사실 권위 계약을 우선 적용한다.

---

## 0. 30초 요약

6개 캠페인(QSP1~QSP6) 60여 라운드 동안 **매수식만** 고쳐왔다. 그런데 손실을 해부해 보니
**손실의 대부분이 매도(청산)에서 발생**한다. 그리고 비용을 정밀 계산하니 설계 구간은
**비용 전 흑자**(건당 +4,411원)인데 비용(건당 10,490원)이 적자로 뒤집고 있었다.

→ **다음 연구 대상은 매도식이다.** 아래 P1부터 순서대로 진행한다.

---

## 1. 현재 상태 (사실만)

### 기준 전략
| 항목 | 값 |
|---|---|
| 매수식 | `QSP2ANCH_R8C2_B` (loop_strategies.db `stockbuy` 테이블) |
| 매도식 | `QSP2_T_ANCH_900_920_S` (= `GATE_r8_4_strength_max_250_S` 사본) |
| 설계 구간 | 2022-04-01 ~ 2024-03-31 (2년) · 13,718건 · −83,394,153원 · 건당 −6,079 |
| 표본외 구간 | 2024-04-01 ~ 2026-02-27 (23개월) · 10,755건 · −127,720,802원 · 건당 −11,875 |
| 실행 창 | 09:00~09:30 tick |

### 재현용 CSV (이미 존재 — 재백테 불필요)
```
설계 2년   : backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731234533.csv
표본외 23개월: backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731235145.csv
```
run_id: `20260731-qsp6-design2y` / `20260731-qsp6-holdout23m`
(경로는 `LoopState(readonly=True).get_generations(run_id)` 의 `csv_path` 로도 조회 가능)

---

## 2. 핵심 발견 5가지 (전부 두 구간에서 재현됨)

### F1. 손실은 매도식 2개 조건에 집중
설계 2년 매도 조건별 손익 기여(전체 손실 −83.4M 대비 %):

| 매도 조건 | 건수 | 건당 | 승률 | 기여 |
|---|---|---|---|---|
| `elif 보유시간 > 60 and 현재가 < 최저현재가(int(60), int(보유시간)):` | 4,687 | **−89,887** | 0.0% | **+505%** |
| `elif 시가대비등락율 < 0 and 수익률 <= -2.0 and 현재가 < 최저현재가(...)` | 967 | **−149,742** | 0.1% | **+174%** |
| 전략종료청산(장 마감 강제) | 3,693 | −27,498 | 40.5% | +122% |
| `elif 4.5 < 최고수익률 and 현재가N(1) >= 이동평균(60, 1) and ...` | 1,648 | **+227,467** | 100% | −450% |
| `elif 최고수익률 > 4 and 최고수익률 * 0.6 >= 수익률:` | 958 | **+124,985** | 99.4% | −144% |
| `if 등락율각도(30) >= 10 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * ...` | 871 | +69,577 | 71.1% | −73% |

표본외에서도 **순서까지 동일**(손절1 +268%, 손절2 +102%).

### F2. 손절은 '보호'가 아니라 '조기 이탈'
손절류 청산 5,654건 검증:
- MAE(최저 도달) 평균 **−2.00%** = 실현 −2.00% → **바닥에서 잘림**
- MAE ≤ −3% 까지 간 거래는 **13.6%뿐** (86%는 −3%도 안 갔는데 청산)
- MAE 가 −1% 도 안 갔는데 잘린 거래 **586건 · 합 −24.7M**
- 손절 거래 MFE(최고 도달) 평균 **+0.69%** — 한때 이익이었음

### F3. 보유시간 구조 (건당 손익)
| 보유 | 설계 2년 | 표본외 |
|---|---|---|
| ~30초 | −33,858 (승률 33.5%) | −27,146 |
| 30~60초 | −2,431 (승률 60.4%) | −378 |
| **1~2분** | **−53,957 (승률 16.1%)** | **−63,311 (승률 14.2%)** |
| 2~5분 | +11,058 | +2,771 |
| **5~10분** | **+34,326 (승률 45.4%)** | **+30,415** |
| 10분+ | −11,761 | −14,943 |

**1~2분 구간만 제외하면 설계 건당 −6,079 → +2,246 (흑자 전환).**

### F4. 비용이 결정적 (내 이전 추정 정정본)
수익금은 **이미 비용 차감 후**다(`utility/static.py:GetKiwoomPgSgSp` — 세금 0.18% + 수수료 0.03%).
수량(`매수금액/매수가`) 역산으로 실제 비용을 구했다:

| 구간 | 비용 전 손익 | 비용(건당) | 비용 후 |
|---|---|---|---|
| 설계 2년 | **+4,411원/건 (흑자)** | −10,490원 (진입금액의 **0.210%**) | −6,079원 |
| 표본외 | −1,396원/건 | −10,480원 | −11,875원 |

**목표가 명확해졌다: 건당 0.21%를 넘겨야 한다.**

### F5. 손절/이익실현 비대칭
- 이익 실현은 **최고수익률 4~4.5%** 를 요구, 손절은 **−2%** 에서 발동
- 그 결과 손익분기 승률 **40.4%** 가 필요한데 실제 **38.1%** (부족 2.3%p)
- 표본외는 41.4% 필요 vs 36.8% (부족 4.6%p)

---

## 3. 다음 작업 — QSP7 계획

### P1. 손절 파라미터 스윕 ★최우선
**가설**: 손절1(`보유시간>60 and 현재가<최저현재가(60,보유시간)`)이 너무 예민하다.

변형 후보(매도식 사본을 만들어 각각 백테스트):
| 변형 | 수정 내용 | 근거 |
|---|---|---|
| S1-A | 윈도우 60 → 120 (`최저현재가(int(120), ...)`) | 흔들림 흡수 |
| S1-B | 발동 지연 `보유시간 > 60` → `> 180` | 1~2분 구간이 최악(F3) |
| S1-C | 최소 손실폭 요건 추가 `and 수익률 <= -1.0` | MAE −1% 미달 조기청산 586건 차단(F2) |
| S1-D | 손절1 완전 제거 | 상한선 측정용(반사실) |

**주의**: S1-D 는 실전 후보가 아니라 **상한선을 재는 실험**이다.

### P2. 이익 트리거 하향
`4.5 < 최고수익률` → 3.0 / 2.5 로 낮춰 실현 빈도를 올린다. 손익비는 낮아지지만
승률 허들(40.4%)이 내려간다. **P1 과 조합해서 봐야 한다**(단독 비교는 오해를 부른다).

### P3. 장 마감 청산 재설계
전략종료청산 3,693건(27%) · 건당 −27,498. 시간 기반 단계 청산(예: 특정 시각 이후
이익권만 유지) 설계 필요.

### P4. 비용 인식 채점
목표를 `건당 손익` 에서 `건당 손익 − 비용` 또는 `비용 넘는 거래 비율` 로.
러너에 이미 `--objective per_trade` 가 있으니 `per_trade_net` 추가가 자연스럽다.

### P5. 매도식 자동 탐색 엔진
매수식에 만든 제안→게이트→재백테 루프를 매도식 **파라미터 축**에 적용.
원장 백로그의 "CSS 파라미터형 제안기"가 이것이다.

---

## 4. 실행 방법 (그대로 복사해 쓰면 된다)

### 4-1. 분석 스크립트 (저장소에 커밋됨 — 그대로 재실행 가능)
```bash
cd C:/System_Trading/STOM/STOM_V.wt-dev
export PYTHONUTF8=1 STOM_ALLOW_MINIMAL_SETTING=1 PYTHONPATH=C:/System_Trading/STOM/STOM_V.wt-dev

python docs/research/quant_scoring_pipeline/scripts/loss_anatomy.py    # 손실 분포·승패 구조·보유시간·일별
python docs/research/quant_scoring_pipeline/scripts/exit_forensics.py  # 1~2분 구간 해부(MFE/MAE·진입 변수 구분력)
python docs/research/quant_scoring_pipeline/scripts/sell_anatomy.py    # 매도 조건 전수 분해 + 비용
```
세 스크립트 모두 상단에 CSV 경로가 상수로 박혀 있다(§1의 두 파일). 다른 전략을
분석하려면 그 상수만 바꾸면 된다. 실행 시간은 각 1~3분.

### 4-2. 매도식 변형 만들기
```python
import sqlite3
con = sqlite3.connect('ai_strategy_loop/state/loop_strategies.db')
code = con.execute('SELECT 전략코드 FROM stocksell WHERE "index"=?',
                   ('QSP2_T_ANCH_900_920_S',)).fetchone()[0]
new = code.replace('최저현재가(int(60), int(보유시간))', '최저현재가(int(120), int(보유시간))')
con.execute('DELETE FROM stocksell WHERE "index"=?', ('QSP7_S1A_S',))
con.execute('INSERT INTO stocksell ("index", 전략코드) VALUES (?,?)', ('QSP7_S1A_S', new))
con.commit(); con.close()
```
**매도식은 `stocksell` 테이블**이다(매수는 `stockbuy`). 혼동 주의.

### 4-3. 백테스트 실행
```bash
# pairs 파일 작성 후
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval \
  --pairs-json docs/research/quant_scoring_pipeline/rounds/qsp7_s1_pairs.json \
  --config-json docs/research/quant_scoring_pipeline/config_qsp6.json \
  --run-id 20260801-qsp7-s1
# 표본외는 --config-json config_qsp6_holdout.json 으로 한 번 더
```
pairs 형식: `[{"label": "s1a", "buy": "QSP2ANCH_R8C2_B", "sell": "QSP7_S1A_S"}, ...]`

소요: 설계 2년 약 6~8분(준비 4분 + 평가), 표본외 23개월 약 6분.

---

## 5. 함정 (실제로 당한 것들)

| 함정 | 증상 | 대응 |
|---|---|---|
| **잔존 프로세스** | 캠페인 중단 후 러너가 살아남아 뒤늦게 기록을 남김 → 재기동 시 base 오염 | 중단 시 `psutil` 광역 스캔(`ai_strategy_loop\|multiprocessing\|backengine`)으로 0 확인 후 재기동 |
| **index.lock 스테일** | `git add` 가 "Another git process" 로 실패 | `rm -f C:/System_Trading/STOM/STOM_V/.git/worktrees/STOM_V.wt-dev/index.lock` 후 재시도 |
| **구간함수 변수** | `체결강도평균`·`등락율각도` 등을 `변수 > 값` 형태로 조건식에 쓰면 엔진에서 함수 vs float 비교 → **타임아웃 정지** | 조건식에선 반드시 `등락율각도(30)` 처럼 창 인자와 함께. 필터 자동생성은 `filtersmith._GUGAN_FUNCS` 가 금지 중 |
| **캡처 컬럼 ≠ 런타임 함수** | `B_체결강도평균`(사전계산 배열)과 `체결강도평균(30)`(런타임)이 다른 값 | 캡처 분위수를 함수 임계로 옮기지 말 것 |
| **추정 vs 실측** | 리프/조건 제거의 "빼기 추정"은 실측과 최대 67% 차이(자금 재배분) | 추정은 후보 순위용, **채택은 항상 엔진 재백테** |
| **Bash heredoc 이스케이프** | 파이썬 코드에 `\n` 을 넣으면 실제 개행이 되어 문법 깨짐 | 파일로 Write 한 뒤 실행할 것 |
| **PowerShell 문법** | Bash 툴은 Git Bash — PowerShell 문법(`$_`, `@{}`)이 깨짐 | psutil 파이썬으로 대체 |

---

## 6. 지켜야 할 규율 (사용자 지시 누적)

| 규율 | 내용 |
|---|---|
| 실전 반영 금지 | 조건식을 실거래에 넣지 않는다. 항상 사용자 결정 |
| 재백테 게이트 | 제거·필터·조임 무엇이든 **엔진 재백테 실측**으로만 채택 |
| 표본외 동반 | 설계만 좋아지는 개선은 채택하지 않는다 |
| 자가채점 금지 | 게이트 점수는 별도 컨텍스트 독립 감사가 매긴다 |
| DB 경계 | GUI `_database/strategy.db` 읽기 전용 · `loop_strategies.db` INSERT-only · `backtest/graph/` 보호 |
| 보고 형식 | 답변은 **테이블 중심**, 연구 결과는 **HTML 아티팩트** + 대시보드 [보고서] 탭 등록 |
| 한계 기록 | 발견한 한계는 `limitation_ledger.md` 에 누적(현재 60행+) |

---

## 7. 자산 위치

| 종류 | 경로 |
|---|---|
| 한계 원장 | `docs/research/quant_scoring_pipeline/limitation_ledger.md` |
| 라운드 기록 | `docs/research/quant_scoring_pipeline/rounds/{tag}_r*.json` |
| 보고서(HTML) | `docs/research/quant_scoring_pipeline/2026-0*.html` (대시보드 등록됨) |
| 대시보드 등록 | `python docs/research/quant_scoring_pipeline/register_reports.py` (재생성 시 재실행) |
| 파이프라인 코드 | `ai_strategy_loop/revision/{surgeon,filtersmith,deep_search,proposer,round_runner,convergence}.py` |
| 분석 코드 | `ai_strategy_loop/autopsy/{label_dataset,feature_map,folds,analyze}.py` |
| 캠페인 드라이버 | `docs/research/quant_scoring_pipeline/scripts/*.bat` |
| 테스트 | `tests/unit/test_{surgeon,filtersmith,deep_search,revision_p2,convergence_p3}*.py` (57~61건) |

---

## 8. 이어받는 첫 명령 (그대로 실행)

```
QSP7 P1 착수: 손절 파라미터 스윕.
docs/research/quant_scoring_pipeline/HANDOFF_2026-08-01_QSP7_매도식연구.md 를 먼저 읽고,
§3 P1 의 변형 4종(S1-A/B/C/D)을 만들어 설계(config_qsp6.json)와
표본외(config_qsp6_holdout.json) 양 구간에서 백테스트한 뒤,
건당 손익·승률·손절 비중·MAE 분포를 표로 비교 보고할 것.
채택은 재백테 실측 + 표본외 동반 개선일 때만. 실전 반영은 하지 않는다.
```
