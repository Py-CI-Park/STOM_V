# 밴드 파라미터화 전략 생성기 — 아키텍처 설계 (2026-06-02)

> **상태**: 설계 전용(구현 아님). 모든 변경 전제 = 토글 기본 OFF·byte-identical·code-reviewer APPROVE·결정론 baseline 신규0·엔진/하드게이트/backtest_graph 무수정.
> **방법**: Workflow(5 에이전트) — 백파인더·엔진계약·밴드템플릿·일별승자 4영역 병렬 조사 → architect 종합. 전 설계는 검증된 코드에 grounded.
> **전체 원문**: 워크플로 출력 `tasks/w0yinopcc.output`.

## 핵심 결론(먼저)
밴드 패러다임은 **과발화를 *구조적으로* 불가능**하게 하고(고정 조건집합 → 거래폭증 경로 제거), **튜닝불가를 해결**(밴드=gradient 있는 벡터 → Bayesian/coordinate descent). **생성품질(레짐 과적합)은 부분만 개선** — 밴드는 표현력 천장(함수형·변수상호작용)을 갖고, 레짐 강건은 여전히 holdout/다년 교차로만 확보.

## 1. 밴드 표현
전략 = **고정 조건집합** 위 밴드 벡터. 각 조건 `(변수, op, [lo,hi], active)`. `active=False`(또는 lo/hi가 자연도메인 전범위)=미게이트(off=전범위, 좁히면=연구). 변수 템플릿=코퍼스 924전략 실측(등락율76%·시총65%·체결강도64%·거래대금·보유시간·수익률). JSON 스키마: `kind/timeframe/preconditions(관심종목·VI·라운드피겨)/time_windows/band_sets[var]{lo,hi,op,active,window}`.
**op enum(결정론 핵심·유한집합)**: lt_le(`lo<v<=hi`)·ge_le·gt(`v>lo`)·lt·gt_lt·ratio_gt. off조건 충족 시 그 줄 미emit.

## 2. 밴드→코드 컴파일러
엔진 기대 정규형(`매수=True`→`if not(밴드): 매수=False` 체인→`if 매수: self.Buy()`)으로 **결정론 변환**. 보장: ①CANONICAL_ORDER 고정변수순서 ②op enum 유한 ③float 포맷 고정(`f"{x:g}"`) ④분기=선언순서 → 동일 밴드벡터 = byte-identical 코드(dedup·baseline 정합).
**엔진 0수정 + 5 PRE-SAVE 게이트 자동통과**: timeframe 정합(variable_scope 허용집합만 노출)·validate(정규형=valid)·token(화이트리스트만)·liquidity(당일거래대금 active 강제)·filter_categories(active 변수=distinct 범주, 직접 제어). 함수형 인자(`각도(w)`)는 `window` 필드+템플릿 전개, w는 고정 하이퍼파라미터(표현력 한계 §9).

## 3. 생성기 (3 소스 공존·토글)
기존 자유형 generate_strategy 무수정, 신규 `generate_band_strategy` 병렬 추가, `band_generation_enabled`(OFF=byte-identical):
- **①LLM 밴드 JSON 제안**: LLM 역할 "코드 작성자→밴드 값 제안자"로 축소. JSON 파싱→도메인 클램프→active≥min→컴파일→기존 게이트(이중안전). 망가진 JSON도 컴파일러가 정규형만 emit=**과발화 저장 경로 없음**.
- **②feature importance/일별승자 시드**: 분위경계(q25~q75)=데이터구동 목표밴드.
- **③자유형 공존**: 기존 경로 유지, 같은 백테/채점/winner 공유.
**과발화 구조적 불가 논증**: 자유코드 과발화 2메커니즘(`매수=True` 단일조건·리터럴) 둘 다 밴드 공간에 *표현 불가*. 거래수=밴드 좁기로 단조·bounded. 750거래 OOM 부재.

## 4. 밴드 최적화
제약=백테 예산(OOM, 1평가=1백테, compute_fitness 무수정 호출). **권장=Bayesian(Optuna TPE, 30~80평가 수렴) + coordinate descent 폴백**. CMA-ES 비권장(예산초과). search space=active 밴드 [lo,hi]+window 이산축, objective=기존 graded. **예산관리**: 1개월 탐색(빠름·OOM안전)→top-k만 3개월/1년 holdout, trial cap(기본30), 거래수 pruner, TPE seed고정(결정론). **seed-refine 대체**: refine "LLM이 밴드 못좁힘"(§3.16-D)을 직접 최적화로 해소.

## 5. 루프 통합 (무변경 보장)
config 토글(전부 기본 OFF): `band_generation_enabled`·`band_opt_enabled`·`band_opt_max_trials(30)`·`band_opt_window(1m)`·`band_seed_source`. fitness/하드게이트/엔진/backtest_graph 무변경(밴드는 입력 코드만 바꿈). 신규 모듈 `brain/band_compiler.py`·`band_generator.py`·`band_optimizer.py`. 대시보드: 밴드 패널(변수별 [lo,hi] 막대·off=회색)·Optuna trial 산점도(기존 contract 확장·NULL 하위호환).

## 6. 백파인더 차용 (✅ 실존 `backtest/backfinder.py`)
| 아이디어 | 채택 |
|---|---|
| **Lookahead 라벨링→밴드 시드 통계**(미래 +X% 직전틱 피처분포 q25~q75=데이터구동 목표밴드) | **채택(고가치)** |
| 탐색틱수/탐색등락율 파라미터화(승리셋업 정의) | 채택(보조) |
| 피처/라벨 분리→분포게이트(=Hypothesis 루프 동형) | 부분(시드용, 합격판정 아님 — §3.14 정적게이트 불가) |
**caveat**: BackFinder 라벨=사후적(lookahead). 실전 밴드는 진입시점 인과 피처만 active + holdout OOS 필수.

## 7. 일별 승자 그룹화 (사용자 아이디어 = 환류 설계)
**경로 A(즉시·룩어헤드 작음, 권장 1차)**: `feature_importance_from_csvs(backtest/csv/*_buy_*.csv)` 재사용(진입시점 관측피처). →KMeans 군집(등락율·체결강도·거래대금·회전율·시총log·시분초)→승리군집(승률·edge_ratio↑)→군집 분위경계=그룹별 목표밴드. 예: "초소형×0900-0905 → 등락율[5,9]·체결강도[150,250]". `generate_quantile_candidates`(BH-FDR)로 우연변수 제거.
**경로 B(후반·룩어헤드 주의)**: moneytop 전수 시뮬 라벨링(시초 30분 분포 표면화)·forward-only 피처·holdout 필수.

## 8. 단계적 롤아웃
| Phase | 산출 | 수용기준 |
|---|---|---|
| **P0** | band_compiler(밴드→코드). 시드902를 밴드로 인코딩→컴파일→seed_strategy_output.txt byte-동등 재현 | round-trip byte동등+5게이트통과+테스트 |
| **P1(MVP)** | 수동 밴드→컴파일→백테1회. band_generation_enabled | 거래 bounded·OOM 0 |
| **P2** | 밴드 최적화(Optuna 1개월 cap). seed-refine 대체실험 | 30trial내 시드 graded≥baseline·결정론 |
| **P3** | feature_importance/일별승자→밴드 시드(§7 A) | 데이터밴드>무작위·holdout통과 |
| **P4** | BackFinder 라벨→시드(§6)+경로B+대시보드 밴드패널 | OOS강건 밴드·LIVE |
| **P5** | 다년(2023~25) 교차 밴드최적화→레짐강건 밴드만 | 다년 우상향 winner |
공통: code-reviewer APPROVE·baseline 신규0·엔진/하드게이트 무수정·토글 OFF byte-identical.

## 9. 위험·반론 (정직)
1. **표현력 천장(최대 한계)**: 밴드=축별 박스(axis-aligned box)만. 시드의 `초당매수수량 > 매도총잔량*0.20`(변수비율)·`현재가 > 고가-(고가-저가)*0.20`(파생위치)·함수형은 [lo,hi]로 못 담음 → 고정 템플릿 조각으로 별도. **변수 상호작용(A 높을때만 B게이트) 박스로 불가**.
2. **템플릿 고정 천장**: 조건집합 고정→템플릿 밖 엣지 영영 못찾음(reference 매도 체결강도 페이드처럼 추가 전엔 부재). 밴드최적화 천장=변수템플릿 완전성.
3. **밴드최적화≠레짐강건**: Optuna가 1개월 graded 최대화=구간 과적합 위험(§3.6 재발). holdout/다년(P5) 없으면 곡선맞춤.
4. **게이트통과≠수익(불변)**: R7.4·§3.14 유효. active 5범주여도 흑자 보장 아님.
5. 함수형 윈도우 탐색폭발·6. float 결정론은 포맷규약 엄격고정 필요(P0 테스트).

## 10. 미해결 본질 결론
| 본질 | 해결도 | 근거 |
|---|---|---|
| **과발화(거래폭증·OOM)** | **✅ 구조적 해결** | 조건집합 고정+AND체인만+min범주하한 → `매수=True`·필터삭제 표현불가. 거래수 bounded·단조 |
| **튜닝불가** | **✅ 해결** | 밴드=벡터→Optuna/coordinate descent. refine 천장 직접 최적화로 대체 |
| **생성품질(레짐 과적합)** | **⚠️ 부분/상당부분 미해결** | 데이터구동 밴드 시드가 무작위보다 낫지만, 박스 표현력 천장+레짐강건은 holdout/다년으로만+게이트≠수익. 밴드는 과적합을 *더 잘 측정·압박하는 그릇*이지 레짐불변성 자체는 못 줌(§3.14·15·16 "코드 아닌 시장레짐이 흑/적 가름"). |

**최종 판정**: 밴드 패러다임 = STOM 두 본질(과발화·튜닝불가) 실질 해결하는 **정당한 차세대 생성기**. 자유형 무한표현력을 "고정조건집합 위 밴드"로 의도적 축소하는 대가로 gradient·구조안전·해석가능성 획득. 레짐 과적합은 완전히는 못 풂(시장구조적 한계). 정직한 기대=**과발화 종식+튜닝가능 연구루프→시드급/이상 밴드를 holdout-강건 탐색**. reference 고빈도·다종목·저MDD 형태는 변수템플릿 확장+다년교차+(필요시)박스밖 조각 추가 동반돼야 도달.

## 신규 파일(구현 시)
`brain/band_compiler.py`(밴드→코드)·`band_generator.py`(밴드 제안)·`band_optimizer.py`(Optuna). 부착점: generator.py(generate_strategy 무수정·옵트인 분기)·filter_gate.py(범주 1:1)·variable_scope.py(허용집합)·config.py(band_* 토글)·feature_importance.py(시드원)·backtest/backfinder.py(lookahead 라벨)·seed_strategy_output.txt(P0 round-trip 기준).
