# STOM 조건식 자동발굴 시스템 재설계 청사진 (2026-06-14)

> 본 문서는 v6 청사진 초안에 적대적 검증 3대 완화책을 반영한 **수정 최종안**이다.
> 검증이 지적한 자기기만(다밴드 OR가 엣지를 만든다는 미입증 가설, build_v5 묘비 은폐, flag-level attribution의 엔진 의존성)을 정면 인정하고, 목표를 "엣지 발굴"에서 "**검증된 앵커의 정직한 다밴드 확장 + 사후착시 차단**"으로 재포지셔닝했다.

> **★2026-06-14 정정·갱신 (이 줄이 최신 권위)**: 초안이 "다밴드 = 방어 전용·신규알파 미약속"으로 비관 프레이밍한 것은 **부정확했다.** 결정적 반례 = **T2C3**(`seed_902905_t2late.json`)는 곧 다밴드(시간대×시총 이산 분기) 구조이며, 제3밴드(09:05~ 시총 반전)를 더해 **OOS 2022 +24%·OOS 2026 +143%·워크포워드 4창 전부 적격**으로 단일밴드 THETA를 일반화에서 **능가**한다. 즉 **잘 설계된 시간대×시총 밴드 추가는 일반화를 개선한다(입증됨).** 전멸한 것은 *점수합산*(build_v5)이지 *이산 분기*(T2C3)가 아니다 — 둘은 다른 구조. **따라서 다밴드는 방어가 아니라 챔피언의 생성 원리다.** 진짜 빠진 것은 "생성기가 이런 다밴드를 *생성*하지 못함"이었고, 이를 보강:
> - ✅ `gen_template_hypothesis.py` 화이트리스트에 `초당거래대금N·매수/매도총잔량N` 추가 — 검증기가 검증된 시드(THETA/T2C3) 어휘를 재현 가능(이전엔 검증된 시드조차 검증 실패).
> - ✅ `p5_template_hypothesis.md` 프롬프트를 **시간대×시총 이산 분기 다밴드 생성**으로 개정 + 시드/T2C3 few-shot 골격 샘플 + build_v5 점수합산 실패예시 + 비용가드(익절≥0.3%).
> - ✅ 검증: 검증된 다밴드 시드 3종 오류 0 통과, 생성 경로 단위테스트 37/37(신규 5) 통과. 엔진 무수정.
> - 다음: 다밴드 후보 *생성*→백테→**재백테 게이트**(희석 밴드 제거)→OOS. (§5.2·§8 P2~P3 유효, 단 "방어 전용" 표현은 위 정정으로 갱신.)

---

## 1. 요약

**무엇을** — STOM 조건식 자동발굴 시스템을 "LLM이 조건식을 통째 생성 → 합격/불합격" 1-shot 구조에서, **분석주도 폐루프(생성→백테→매매기록→기여도분석→변이→재백테 게이트→워크포워드)**로 재설계한다. genome 4계층(Atom→Block→Flag→Genome)을 엔진 개조가 아니라 `tmap/template.py` 렌더러 확장 + 생성 스키마 확장 + 기존 자산 배선으로 구현한다.

**왜** — 14~28세대 15가설 + v5 복합점수가 전멸했고(아래 §2.3), 사후 슬라이스가 재백테에서 부호 반전하는 착시(+1.07M→-1.15M)가 실측됐다. 1-shot 구조는 (a) 다시간대/시총 분기를 생성하지 못하고 (b) 사후착시를 거르지 못하며 (c) 선택 동력이 인샘플이라 구조적으로 과적합을 양산한다.

**어떻게** — 엔진(`trade/base_strategy.py`)을 **무수정**으로 두고, 8대 맹점을 렌더러/스키마/배선 변경으로 메운다. 단 검증이 적발한 두 한계 — (i) 다밴드 OR 결합이 엣지를 만든다는 증거가 0이고 오히려 build_v5가 반증, (ii) flag-level attribution은 엔진의 trade log가 플래그 발화를 기록하지 못해 작동 불가 — 를 수용하여, **목표를 2앵커(THETA/T2C3) 정직 운영 + 게이트로 낮추고, attribution을 genome 단위로 격하하며, 첫 실험을 "2앵커 합본 OOS 비교"로 변경**한다.

---

## 2. 연구 이력 회고

### 2.1 시간순 연구 아크 (각 단계 결론 1줄)

| 단계 | 시기 | 무엇을 했나 | 결론 |
|---|---|---|---|
| A. 시드 발굴 (R·T·M 트랙) | ~6/13 | 인간 시드(902905) 부검(R)·09:25 시간확장(T)·min 전세션 지도(M) | T2C3 신규 챔피언 발굴, min 전세션 안정 알파 부재 |
| B. 고정 OOS 정직검증 | 6/4 | sparse-positive + 다년 train + 고정 2022/2026 OOS | AI 단일전략 일관 REJECT — 시드 대비 ~15배 열세 |
| C. 방향성 검토 | 6/5 | 파이프라인 단계별 해부 | "환류 신호가 전부 인샘플 → 구조적 과적합 생산" |
| D. 비상관 니치 세대 11~17 | 6/13 | 대형주후반·다이어트·돌파전·F07극단·exit2·전일동시간비 | 17세대까지 전멸 |
| E. Ralph 야간 루프 18~28 | 6/13밤~6/14새벽 | 미시도 알파 9종+라운드피겨+누적순매수 자율 생성 | 14~28 총 15가설 전멸, 활성 생성 종료 |
| F. min 전세션 회전 스윕 | 6/14 아침 | min_session 0900_1500 회전 28축 100좌표 전축 스윕 | 전 좌표 음전·전 축 plateau=0 |
| G. 분석/히트맵 | 6/14 | min 시드를 시총×전일동시간비 해부, 홀드아웃 검증 | "데이터 한계가 아니라 프로세스 한계", 버린 시드에 흑자 포켓 발견 |
| H. 재백테 게이트 반전 | 6/14 | 흑자 포켓을 조건식 조각으로 재백테 | 사후 +1.07M → 재백테 -1.15M 반전. 사후슬라이스≠엣지 확정 |
| I. 분석주도 루프 전환 | 6/14 | 생성→백테→분석→히트맵→재백테게이트→반복 설계 착수 | 방법론 전환, 본 청사진 |

### 2.2 검증된 알파 — 명예의 전당 (불변)

세 모델 모두 V1~V5(V6) 정직검증 완주. 연 OOS 수익률 약 42~52%.

| 모델 | 구조 | train | OOS 2022 | OOS 2026 | 강건성 근거 |
|---|---|---|---|---|---|
| **🥇 THETA_seed_902905_06** | 인간 시드 + cap_max 2500·take_hard 9·trail_start 4 (09:00~05 소형주 첫 돌파) | +10,965,479 / MDD 10.04 / 272건 / payoff 1.53 | +2,097,751 (55건) | +164,602 (9건) | V1 DSR 0.945·V2 플라시보 12종 압도·V5 슬리피지 2틱 견딤 |
| **🥇 T2C3** | THETA θ + 제3분기 09:05~09:15 (시총 4000억+ 대형주 반전, burst 4.0) | +9,866,240 / MDD 11.30 / 356건 / payoff 1.66 | +2,593,894 (60건, THETA +24%) | +400,701 (15건, THETA +143%) | train만 열위, OOS·WF·슬리피지 능가 = 일반화 우월 |
| **🥇 포트폴리오 V6** | THETA 50% + T2C3 50% 균등 | M4 48개월 +13,044,334 vs 시드 +10,550,472 (+24%) | — | — | 레짐 상보성 — 2026 위축장을 T2C3가 헤지 |

### 2.3 전멸한 알파 클래스 (14~28세대, 15가설 전부 no-go)

| 세대 | 알파 클래스 | 대표 결과 | 실패 분류 |
|---|---|---|---|
| 14 | F07 burst 극단×전일동시간비 | Q1 -6.32M/254건 · Q2 -5.66M/308건 | 홍수형 |
| 15 | exit2 레짐 조건부 청산 | Q1 -1.84M/106건 · Q2 -1.93M/166건 | 억제형 |
| 16 | min 한낮 강도급등×유동성×돌파 | Q1 0.2건/일 게이트탈락 · Q2 0신호 | 0신호형 |
| 17 | 전일동시간비 극단(≥500) | Q1 -58.3M/1838건 · Q2 -61.0M/2673건 (최악) | 홍수형 |
| 18 | 평균회귀 과매도반등 | 0신호→완화 -5.5M/-7.2M | 0신호→홍수 |
| 19 | 시초 1분 미시구조 | -1.35M/-1.85M (3년 train -2.54M 기각) | 억제형 |
| 20 | 호가 매도벽 소멸 돌파 | -38M/1651건 · -52M/2550건 | 홍수형 |
| 21 | 변동성 수축→확장 돌파 | -22.2M/-15.4M | 홍수형 |
| 22 | 회전율 급등 품질필터 | -12.4M/-12.1M | 억제형 |
| 23 | 2단계 확인 돌파 | -35.5M/-42.3M | 홍수형 |
| 24 | 호가 매수벽 지지 돌파 | -9.46M/-9.99M | 홍수형 |
| 25 | 체결강도 지속 가속 | -7.29M/-4.15M | 억제형 |
| 26 | 거래대금 가속도(2차 미분) | -4.28M/-8.50M | 억제형 |
| 27 | 라운드피겨 돌파 | -808K/-965K | 억제형 |
| 28 | 누적 순매수 축적 | -12.95M/-10.12M | 홍수형 |
| **v5** | **복합점수 19플래그 합의 + 시간 5구간 (★다밴드 genome 완성형)** | **스모크 -1.11억/4,989건, 최엄격 게이트 -0.65억, 시간버킷 6개 전부 음(-)** | **홍수형 + 합산무효** |

**실패 3분류:**
- **(a) 홍수형** — 느슨한 조건이 거짓신호를 폭주(1600~2700건)시켜 대형 적자. 호가 동학(20·24)은 변동이 잦아 신호가 홍수가 됨.
- **(b) 억제형** — 필터가 손실만 줄이고 부호는 못 바꿈. 저MDD를 달성해도 흑자 미달.
- **(c) 0신호형** — 과엄격 조건이 공집합/소표본을 만들어 측정 자체 실패.

### 2.4 ★하드 교훈 — 새 시스템이 반드시 존중 (위반 불가)

| # | 하드 교훈 | 근거(실측) | 시스템 반영 |
|---|---|---|---|
| **a** | 사후 슬라이스 ≠ 추출 엣지 | min 중형주 포켓 +1.07M(283건) → 조각 재백테 -1.15M(318건) 반전 | 모든 슬롯·밴드 채택에 **재백테 게이트** 필수 |
| **b** | 엔진은 비용 net | 수수료 0.015%×2 + 세금 0.18% 차감 순손익. 슬리피지만 미반영(고정체결) | take floor 비용가드 + 슬리피지는 V5/페이퍼로만 |
| **c** | 단일밴드 천장 | 엔진이 per-stock if-Buy 모델. 횡단면 랭킹 불가 | 횡단면 랭킹은 [승인필요]로 격리 |
| **d** | 빈도↑ ≠ 수익 | min 시드 일 34건·payoff 1.49인데 흑자 코너 전무(-290M) | 밴드 OR 추가 자체 금지. Lift>0 + 재백테 게이트 통과 시에만 |
| **e** | 레짐 의존 (전천후 알파 부재) | 시드도 2026 OOS -191,109. 전천후는 시드 코어가 유일 | 단일 동결전략의 교차레짐 강건을 목표로 삼지 않음. 앵커 고정 + 탐색밴드만 |
| **f** | 32엔진 최적 | 32엔진 prepare 73s < 64엔진 104s(HT 초과). 64는 >16점 스윕만 | 단일 평가·OOS 다회 모두 32엔진 |
| (보조) g | 환류 신호 전부 인샘플 → 과적합 | 부검은 train 거래만, best/winner 선택이 인샘플 점수 | holdout 기본 ON + 선택 동력을 OOS로 |
| (보조) h | 2분기 스모크는 필요조건이지 충분조건 아님 | 소표본 20건 양분기 흑자는 우연 가능 | 3년 train + plateau가 진짜 관문 |

### 2.5 데이터 경계 (고정·확장 불가)

- **tick: 09:00~09:30 고정**. 단 `bt_universe_end_time=92800`(09:28) 하드클립이 기회 모수를 28분으로 제한했던 별도 이슈 존재(→ §9·[승인필요]).
- **min: 2025-04~2026-02 (11개월). 2022 OOS 없음** → 기간분할(전반 20250408~20250912 105일 / 후반 20250915~20260227 105일) 검증으로만 강건성 판정.
- 비상관 니치 재개는 신규 데이터(09:30 너머·유니버스 확대·2022/2026 레짐 포함) 도착 후가 현실적. 현 데이터에서 규칙기반 탐색은 tick·min 양쪽 소진.

---

## 3. 핵심 진단 — 8대 맹점 + 비용 net 사실

### 3.1 8대 맹점 (파일:대상 + 변경 요지)

| # | 맹점 | 파일 : 대상 | 변경 요지 |
|---|---|---|---|
| 1 | 다시간대 분기 생성 불가 | `tmap/template.py:Branch/render_branches` + `scripts/gen_template_hypothesis.py:validate_hypothesis` | branches 배열 도입(§4). LLM이 밴드별 시간창 생성 |
| 2 | 시간대별 시총 분기 불가 | `tmap/template.py:Branch.cap_lo/cap_hi` | 밴드마다 독립 시총 게이트. cap_hi 슬롯 허용 |
| 3 | 진입 밴드별 차등 청산 불가 | `tmap/template.py:Branch.exit_ref` + sell_code의 `exit_table` | 엔진 무수정 제약상 매수 시 밴드 태그 전달 불가 → 청산식이 `진입시분초`(보유상태 변수)로 밴드 역추정 |
| 4 | 비용-인지 사후뿐 | `tmap/atom_library.py` + `validate_hypothesis` + `fitness/` | 정적 가드(take floor) + 점수 페널티 이중화 |
| 5 | 템플릿 경로 개선루프 부재 | `autopsy/` ↔ `tmap/` 신규 `scripts/tmap_autopsy_loop.py` | sweep→trade log→autopsy→변이→재sweep 어댑터. **단 attribution은 genome 단위로 격하**(§3.3) |
| 6 | 슬롯 후보 재백테 게이트 없음 | `scripts/tmap_sweep.py` + 신규 `tmap/refine_gate.py` | 후보를 조각 재렌더 후 재백테. Lift 재현 확인. 하드교훈 a 강제 |
| 7 | holdout/OOS 기본 OFF | `fitness/holdout.py` + `controller/contract.py` | 기본 ON 반전. 채택 판정을 WF 통과 필수로 |
| 8 | tick/min 표현력 비대칭 | `tmap/template.py:render_branches` (min 분기) | min도 동일 branches로 다밴드 |

### 3.2 비용 net 사실 — 엣지 이중계산 주의

- **백테는 이미 net**(하드교훈 b): 수수료·세금을 차감한 순손익을 산출한다. **따라서 점수함수에서 비용을 다시 빼면 이중계산**이다. 비용 인지는 (i) 백테 net 결과를 신뢰하고, (ii) **생성 단계에서 익절폭이 왕복비용 아래인 후보를 정적 차단**(take floor)하는 방식으로만 추가한다.
- **왕복비용 ≈ 0.21%** (수수료 0.015%×2 + 세금 0.18%). `atom_library.py`에 `MIN_TAKE_FLOOR = 0.30`(왕복 0.21% + 슬리피지 마진 0.09%) 상수. `validate_hypothesis`가 `side=="sell"` 이고 이름에 `take`/`익절` 포함 슬롯의 `values` 최솟값 < 0.30이면 오류 반환.
- **보정 대상은 슬리피지뿐**: 고정체결이라 사이징 확대 시 백테는 선형이나 실제 시장충격은 증가. 슬리피지는 점수에서 빼지 말고 **V5 슬리피지 틱 테스트 + 페이퍼/소액 실전**으로만 검증한다.
- **[정직 정정]** `validate_hypothesis`에는 현재 side별 슬롯값 하한 검사가 **없다**(키 존재만 검사). `_engine_cost_errors`가 잡는 건 비용 폭탄(무인자 함수·shift<1·잔량 5단 호출)이지 손익 net이 아니다. take floor는 **신규 구현**이며 "추가만 하면 됨"보다 일이 있다.

### 3.3 ★flag-level attribution의 엔진 의존성 — 정직 인정 + 격하

- **검증이 적발한 치명 결함**: autopsy의 `B_COLUMNS`는 `backtest/back_static.py`의 `TRADE_RESULT_B_COLUMNS`에 맞춘 **14개 고정 엔진 스칼라**(현재가·등락율·체결강도·시가총액·전일동시간비 등)다. **어느 flag(F01~F20)가 발화했는지, band_id가 무엇인지 기록하는 컬럼이 없다.** 또한 `analyze.py`는 `is_holdout=True`면 ValueError를 던져 **구조적으로 train에서만 동작**한다.
- **귀결**: 초안이 약속한 "flag별 Lift 환류"는 엔진이 trade log에 플래그 발화를 기록하지 못해 **작동 불가**다. "어댑터만 만들면 됨"은 거짓이었다.
- **수정안 — attribution을 genome 단위로 격하**:
  - flag/밴드 단위 Lift 측정은 **포기**(엔진 무수정 원칙 유지). 환류는 **genome(템플릿) 전체 단위 attribution**으로만 수행 — 즉 "이 genome의 OOS 성과가 앵커 단독 대비 개선/열화"만 측정한다.
  - flag-level Lift가 정말 필요하면 `back_static.py`에 플래그 발화 컬럼 추가가 필요 → **[승인필요]** 항목으로 격상(§9). 본 청사진 P0~P5는 격하안(genome 단위)으로 진행한다.

---

## 4. 재설계 아키텍처 — genome 4계층 ↔ STOM 파일 매핑

### 4.1 매핑 원칙 — "엔진 함수가 아니라 코드 텍스트 합성"

리포트의 호가/갭/세력 합성지표는 엔진 내장 함수가 아니라 **화이트리스트 primitive로 전략 코드 안에서 인라인 합성**된다(`build_v5_composite_template.py:41~122`가 `매수공격비_5초`·`상단1호가소화율`·`VI근접`을 전부 로컬 대입으로 생성). 4계층은 STOM 코드 레이어에 다음과 같이 대응한다.

| genome 계층 | STOM 구현 위치 | 형태 |
|---|---|---|
| **Atom** | 신규 `ai_strategy_loop/tmap/atom_library.py` | `name → 코드 조각 문자열({슬롯} 포함)` 딕셔너리 |
| **Block** | 같은 파일, atom 참조 조합 | `block_id → {atoms:[...], expr:"A and B and C"}`. F-flag 정의식이 곧 Block |
| **Strategy Flag** | template JSON의 `branches[].flags[]` | `"F05"` 라벨 → Block expr (`build_v5:104~122` 패턴) |
| **Genome** | template JSON 1개 (`branches` 배열) | Hard Gate + branches(밴드별 flags/filters/슬롯/청산) + Score/Risk |

장점: `build_v5_composite_template.py`가 정확히 이 패턴을 손으로 구현해 가드를 통과시켰다. 우리는 그 손작업을 **데이터 구조로 일반화**할 뿐이다.

> **★중대 경고 (검증 반영)**: `build_v5`는 이 4계층의 **완성형이자 묘비**다. 시총 4단계×시간 5구간×19플래그 복합점수 = 정확히 본 청사진의 "branches + flags OR" 구조이고, 그 결과는 **-1.11억/4,989건, 시간버킷 6개 전부 음(-)**이었다(§2.3). 따라서 4계층 인프라는 **"엣지를 만드는 도구"가 아니라 "검증된 앵커를 정직하게 표현하고 사후착시를 거르는 그릇"**이다. 신규 알파를 약속하지 않는다.

### 4.2 template.py 렌더러 확장 — `branches` 배열 (하위호환 유지)

현 `TemplateSpec`은 평면 `buy_code: str` 하나(line 39)다. 시드 `seed_902905.json`는 `if 시분초<90200 / elif {window_start}<=시분초<{window_end} / else` 3밴드를 buy_code 안에 하드코딩 — 다밴드는 가능하지만 사람이 쓴 한 덩이여서 LLM 생성경로가 못 만든다.

| 추가 항목 | 정의 | 해결 맹점 |
|---|---|---|
| `Branch.band_id` | "early"/"band1"... 라벨 | 1 |
| `Branch.time_lo / time_hi` | 시분초 하한(int) / 상한(슬롯 허용) | 1 |
| `Branch.cap_lo / cap_hi` | 시총 밴드 하한/상한(슬롯 허용) | 2 |
| `Branch.flags` | OR로 묶을 flag id (atom_library 참조) | 1·8 |
| `Branch.filters` | AND 추가 필터 (atom expr) | — |
| `Branch.exit_ref` | 이 밴드 진입분의 청산 파라미터 키 | 3 |

`TemplateSpec`에 `branches: Tuple[Branch, ...] = ()` 추가. `render()`는 branches가 비면 **현행 buy_code.format() 경로 그대로**(identity 보증), 채워지면 새 `render_branches()`가 if/elif 체인을 조립한다(`build_v5:197~242`와 동일 텍스트를 데이터로 생성).

**[하드캡 — 검증 반영]** 차원폭발·타임아웃(11세대 교훈, 윈도우함수 ≤3 권장)을 막기 위해:
- 밴드 수 **≤ 2** (앵커 1밴드 + 탐색 1밴드).
- 밴드당 flag **≤ 3**, AND 조건 **≤ 10**.
- 윈도우함수 총 호출 **≤ 3** (기존 실측 한계).
- `coordinate_points`(1-D)·`grid_points`(2-D) 너머는 스윕 금지. 다밴드 구조 자체는 스윕 축이 아니라 고정 구성으로 둔다.

### 4.3 gen_template_hypothesis.py 스키마 확장 (맹점 1 생성경로)

현 `validate_hypothesis()`는 `buy_template`(평면 문자열)만 받는다(line 271 `required_keys`). payload에 `branches` 배열을 선택적 허용:

- payload에 `branches` 키가 있으면 Branch 스키마 검증 + `render_branches`로 렌더 후 기존 `validate_rendered`(compile/token/scope/time_integrity) 깔때기 통과.
- 없으면 현행 평면 `buy_template` 경로 (하위호환).
- `_engine_cost_errors`(line 201)·`_window_shift_errors`는 렌더된 텍스트에 그대로 적용 → 다밴드여도 비용 폭탄 정적 차단.

### 4.4 p5 프롬프트 개정 (다밴드 + few-shot)

`p5_template_hypothesis.md` 개정:
- 출력 스키마에 `branches` 배열 추가, 각 branch에 `{time_lo,time_hi,cap_lo,cap_hi,flags,filters,exit_ref}`.
- **few-shot 샘플 2개**: (1) `seed_902905` 3밴드 구조, (2) `build_v5` 5시간구간×4시총 분기 — 단 **숫자는 전부 슬롯으로 비우고 구조만 제시**(`build_prompt:99` "임계 이식 금지·구조 차용" 강화).
- **신호밀도 규칙 유지**(line 117): 밴드당 AND 조건 10개 이하. 다밴드라고 풀면 홍수형 실패(하드교훈 d) 재발.

---

## 5. 조건 다양화 방법 + 연결≠엣지 함정 회피

### 5.1 다양화 4축 (변이 연산자 재사용)

| 축 | 구현 | 비고 |
|---|---|---|
| Atom 라이브러리화 | `atom_library.py`에 엔진 실재/합성가능 atom만 등록 | 미실재는 §10 F절에서 차단 |
| few-shot 샘플 주입 | p5 프롬프트에 시드+v5 구조 제시(§4.4) | 숫자는 슬롯 |
| 변이/교배 연산자 | `tmap/mutator.py`: 임계 완화/강화, 시간/시총/갭률 구간 분리, AND/OR 추가, 가중치 변경 | 교배 자식도 재백테 게이트 필수 |
| 구간 분리 | branches의 time/cap 밴드 분할 | 맹점 1·2 인프라 위 자동, 단 §4.2 하드캡 적용 |

### 5.2 ★함정 회피 — "OR 연결만으로 엣지는 안 생긴다" (하드교훈 d)

검증 결론: 앵커 고정은 baseline 바닥만 보장할 뿐, **탐색 밴드가 엣지를 추가한다는 증거가 전무**하다(14~28세대 + v5가 반증). refine_gate는 희석 밴드를 **제거**할 수 있어도 **생성**할 수는 없다. 따라서 통계적으로 가장 가능성 높은 결과는 "탐색밴드 전멸 → 앵커 단독 elite 확정"이며, 시스템은 이를 **정상 결과로 수용**한다. 4단계 게이트로 코드에 박는다:

1. **앵커 고정** — 모든 genome은 검증된 밴드(THETA 09:00~05 소형주 cap≤2500, 또는 T2C3 09:05~15 대형주 burst4.0 cap≥4000억)를 `branches[0]`로 **고정 포함**하고 잠근다. `tmap/mutator.py`에 `ANCHOR_BANDS` 동결 리스트 (mutator 변형 금지).
2. **탐색 밴드만 추가** — 신규 밴드는 `branches[1]`로만 (1개, §4.2 하드캡).
3. **genome 단위 기여도 측정** — autopsy가 trade log에서 **genome(템플릿) 전체** 기대값을 OOS에서 측정 (flag/밴드 단위 Lift는 §3.3대로 격하).
4. **재백테 게이트로 희석 밴드 제거** — `refine_gate.py`: 후보 밴드를 **넣은 genome vs 뺀 genome**을 둘 다 재백테. 넣었을 때 종합점수가 **앵커 단독보다 유의하게 개선되지 않으면 폐기**(하드교훈 a). H사례(+1.07M→-1.15M)가 이 게이트가 잡아야 할 패턴.

### 5.3 종합점수 — 게이트 vs 순위 분리 (검증 반영)

- **게이트(곱셈적·hard, 통과/탈락)**: PF≥1.25, 매매성능지수≥1.25, MDD≤4%, 최소표본 200건, 워크포워드 통과≥3구간, train/검증비≥0.7. 이 값들을 `controller/contract.py` 또는 `fitness`에 상수화 (self.vars[40]~[49]).
- **순위(통과자 정렬)**: 가중합은 **게이밍 취약**(한 항 극대화로 페널티 상쇄 — v5 "합산은 품질 분별자가 아님"과 같은 실패 모드)이므로 순위는 **OOS 절대수익 단일 기준** 또는 lexicographic(게이트 통과자 중 OOS profit 순)으로 한다.
- **가중합은 보고용으로만**:

```
보고용 종합점수 = 0.25×연간수익률_z + 0.20×매매성능지수_z + 0.15×기대값_z
              + 0.10×승률_z − 0.20×MDD_z − 0.05×거래과다 − 0.05×복잡도
```
> 위 가중합은 비용을 다시 빼지 않는다(백테 net, §3.2). 거래과다·복잡도 페널티만 적용.

---

## 6. 전체 DB 발굴 자동화 설계 (엔진 무수정)

### 6.1 파이프라인

| 단계 | 도구 | 산출물 | 비고 |
|---|---|---|---|
| [1] genome 생성 | `gen_template_hypothesis.py --write` (branches 스키마) | `templates/llmgen_*.json` | 앵커 밴드 고정 주입은 `mutator.py` 후처리 |
| [2] 병렬 백테 | `tmap_sweep.py --template ... --max-points N` | manifest + summary | 32엔진(하드교훈 f) |
| [3] trade log | `controller/export.py` 포맷 | `trade_log_<run>.csv` | **B_COLUMNS 14 고정 스칼라뿐 — 플래그 컬럼 없음**(§3.3) |
| [4] genome 기여도 분석 | `autopsy/analyze.py` + `segment.py` | `attribution.json` | **genome 단위만**(flag 단위 격하) |
| [5] 변이/승격/폐기 | `tmap/mutator.py` + `tmap/refine_gate.py` | 후보 밴드 채택/폐기 | ★재백테 게이트 |
| [6] walk-forward | `tmap_walkforward.py` + `fitness/holdout.py` | `elite_archive.csv` 승격 | 통과구간수≥3 + OOS 기본 ON |
| 루프백 | autopsy 교훈 → 다음 프롬프트 | — | `tmap_autopsy_loop.py` 오케스트레이터 |

### 6.2 자산별 재사용/연결 (전부 실존 확인)

| 자산 | 현 역할 | 재사용 방식 |
|---|---|---|
| `controller/loop.py` (2353줄) | GA closed-loop(시드 경로) | 변이/승격 **패턴만 차용**. tmap 루프는 얇은 `tmap_autopsy_loop.py`로 분리 (복잡도 미유입) |
| `autopsy/analyze.py`·`segment.py` | trade log segment 부검 | **genome 단위** 기대값 산출. flag/band 컬럼 부재로 flag Lift는 불가(§3.3) |
| `fitness/holdout.py` | OOS 분리 | 기본 ON 반전. **[정직] docstring상 gate 배선은 US-005 미완 → "토글 반전"은 주장보다 큰 작업** |
| `scripts/tmap_walkforward.py` (216줄) | 기간분할 WF | `select_theta`(line 49)·`apply_washout`(line 85). **[경고] 1슬롯 정책 전용 — 다밴드 미평가**(§9 리스크) |
| `scripts/tmap_sweep.py` (239줄) | 좌표 스윕(32엔진) | `coordinate_points`/`grid_points` 재사용. **1-D/2-D 전용, 다밴드는 스윕축 아님**(§4.2 하드캡) |
| `scripts/claude_candidate_batch_eval.py` (141줄) | 후보 배치 평가 | refine_gate "넣은 vs 뺀" 재백테 배치 실행기 |
| `tmap/template.py:render` | identity 보증 렌더 | branches 비면 현행(무손상), 채우면 render_branches |

### 6.3 데이터 경계 (§2.5 재확인)

- tick 09:00~09:30 고정(92800 클립 별도 이슈). min 11개월·2022 OOS 없음 → 전반/후반 105일 분할 검증.
- **신규 비상관 니치는 신규 데이터 도착 후**. 현 데이터에서 1차 가치는 "신규 알파 발굴"이 아니라 **"검증된 앵커의 다밴드 정직 확장 + 사후착시 차단"**이다.

---

## 7. 비용-인지·OOS 규율

| 규율 | 생성 설계제약 (사전 차단) | 평가 게이트 (사후 검증) |
|---|---|---|
| 비용 인지 | take floor 0.30 — 익절폭 < 왕복비용+슬리피지 후보 거부(`validate_hypothesis` 신규) | 점수에서 비용 재차감 금지(백테 net, 이중계산 방지) |
| 과빈도 | 밴드당 AND ≤10, 일평균 거래수 상한 slot 메타 | 거래과다 페널티(보고용)·홍수형 거래수 게이트 |
| OOS | — | **holdout 기본 ON** + WF 통과구간≥3 + 2022/2026 OOS 통과 시에만 채택 |
| 선택 동력 | — | 채택 판정을 `train 점수`가 아니라 `min(train, OOS)` 또는 WF 통과구간수로 (하드교훈 g — 인샘플 선택 차단) |
| 슬리피지 | — | 점수에서 빼지 않고 V5 슬리피지 틱 + 페이퍼/소액 실전으로만 |

> **[정직 경고]** holdout 기본 ON은 분할 경계 제공(`holdout.py`)만으로 끝나지 않는다. gate 적용·점수 배선이 미완(US-005)이므로 P3에서 별도 구현 공수가 든다.

---

## 8. 단계별 로드맵 (각 단계 백테 게이트)

| Phase | 산출물 | 통과조건 (백테 검증) | 실패 시 행동 |
|---|---|---|---|
| **P-1 (★첫 실험, 신규)** | 2앵커 합본 OOS 비교 (§9) | 2밴드 OOS profit ≥ (THETA OOS + T2C3 OOS) × 0.9 | 미만이면 render_branches가 거래 간섭 → **인프라 설계 재검**, P0 진행 금지 |
| **P0** 렌더러 다밴드 | `template.py:Branch/render_branches` + 단위테스트 | **identity 게이트**: `seed_902905` branches 재표현 == 기존 평면 렌더(바이트 동일). 기존 36개 llmgen 템플릿 무손상 | branches 경로 격리, 평면 회귀 0 보장까지 머지 금지 |
| **P1** atom_library + 비용가드 | `atom_library.py` + `validate_hypothesis` 확장(take floor) | 실재/합성가능 atom만 등록. take<0.30 거부 테스트 | 미실재 atom은 §10 F절대로 제외 |
| **P2** 재백테 게이트 | `tmap/refine_gate.py` + `claude_candidate_batch_eval` 배선 | **반전 테스트**: H사례 포켓을 게이트에 넣으면 "폐기" 판정 재현(+1.07M 사후 vs -1.15M 재백테) | 게이트가 반전 못 잡으면 무효 — P3 금지 |
| **P3** 다밴드 sweep + WF + holdout ON | `tmap_autopsy_loop.py` + `holdout.py` gate 배선(US-005 공수) + WF `select_theta` 다밴드 평가 개정 | 앵커 단독 재현 + 탐색밴드 추가가 **WF 3구간 + 2022/2026 OOS 통과 시에만** 채택 | 탐색밴드 전멸이면 앵커 단독 elite 확정(**정상 결과**) |
| **P4** 부검 환류 폐루프 | autopsy(genome 단위)→mutator→refine_gate→sweep 자동 1회전 | 사람 개입 없이 완주 + attribution.json·elite_archive.csv 생성 | loop.py 패턴으로 종료조건/runlock 보강 |
| **P5** elite archive 운영 | `elite_archive.csv` + 승격/폐기 정책 | self.vars[40]~[49] 게이트값으로 승격 판정 재현 | 정책 임계 조정(데이터 산출물, 승인 불요) |

> **순서 변경(검증 반영)**: 초안의 첫 단계 P0(identity 바이트 동일)는 새 정보를 0 만든다. **P-1을 먼저** 둔다 — 두 검증된 앵커가 한 genome에서 서로를 안 잡아먹는지가 인프라 전체의 생사를 가르는 미측정 가정이기 때문이다.

---

## 9. 정직한 리스크 + 첫 실험

### 9.1 리스크 등급 (검증 판정 반영)

| # | 리스크 | 등급 | 완화책 |
|---|---|---|---|
| 1 | 연결 ≠ 엣지 | **치명적** | 목표 재포지셔닝(엣지 발굴 → 앵커 정직 운영). 탐색밴드 전멸을 정상 결과로 수용. 신규 알파 미약속 |
| 2 | 과적합/자유도 폭발 | **높음** | 밴드 ≤2·flag ≤3·윈도우 ≤3 하드캡. WF `select_theta` 다밴드 평가 동시 개정(P3). PBO/CSCV·Deflated Sharpe는 [승인필요] 선결 권고 |
| 3 | 선택편향/in-sample Lift | **치명적** | flag 단위 Lift 포기(엔진 의존). genome 단위 attribution + OOS 채택 게이트. flag 채택은 OOS 표본 부족으로 금지 |
| 4 | 다목적 점수 게이밍 | **중간** | 게이트(hard) vs 순위(OOS 절대수익) 분리. 가중합은 보고용(§5.3) |
| 5 | 엔진 어휘 미스매치 | **낮음** | §10 F절 — 코드와 정합. take floor만 신규 구현 |
| 6 | 계산비용/차원폭발 | **높음** | §4.2 하드캡. grid_points 너머 스윕 금지. 밴드별 atom 재계산 최소화 |
| 7 | 데이터 경계 정직성 | **구조적 한계** | "고빈도 우상향"은 이 데이터에서 불가능 — 목표에서 제외. 빈도↑는 신규 데이터 도착 후로 명시 연기. 절대수익은 D 운영규모화(사이징)로만 |

### 9.2 ★첫 실험 (가장 저비용으로 가장 큰 불확실성 제거)

> **앵커 2밴드 genome — THETA(09:00~05 소형주 cap≤2500) `branches[0]` + T2C3(09:05~15 대형주 burst4.0 cap≥4000억) `branches[1]` — 을 render_branches로 조립해, OOS 2022 + 2026에서 "2밴드 합본"이 "THETA 단독"과 "T2C3 단독"의 단순 합 대비 열화/개선 여부만 측정한다.**

| 항목 | 내용 |
|---|---|
| 신규 atom | **0개**. 명예의 전당 2앵커의 검증된 식만 사용 → 생성·가드·신규코드 리스크 없음 |
| 검증 기준 | 2밴드 OOS profit ≥ (THETA OOS + T2C3 OOS) × 0.9 → "다밴드 렌더가 알파 미파괴" 입증, branches 인프라 GO. 미만이면 render_branches 합성이 거래 간섭(같은 종목·시각 동시 발화 시 엔진 단일 포지션 처리, 하드교훈 c)을 일으킨다는 뜻 → **인프라 설계 재검** |
| 왜 최대 불확실성 제거 | 청사진 전체가 "branches OR 결합이 정직하다"에 의존. 그런데 **두 검증된 앵커조차 한 genome에서 OR로 묶었을 때 per-stock 단일포지션 엔진에서 서로를 안 잡아먹는지 아무도 측정한 적이 없다.** 이게 깨지면 P0 identity 테스트는 통과해도 다밴드 실전은 무의미 |
| 비용 | 32엔진 OOS 2회(73s×2 + eval) — 반나절 |

### 9.3 정직한 총평

**(a) 1-shot 대비 진짜 개선:** ① refine_gate 반전 테스트 강제(H사례 차단)는 하드교훈 a를 코드로 박는 옳은 방어. ② holdout 기본 ON + WF 채택은 인샘플 선택 문제(하드교훈 g) 정조준. ③ 엔진 무수정 + §10 F절 어휘 정합성은 현실적.

**(b) 여전히 엣지를 보장 못 함:** ① 다밴드 OR가 엣지를 만든다는 근거 0 — v5 묘비가 반증. ② flag별 Lift를 OOS로 계산할 길 없음(B_COLUMNS에 플래그 컬럼 부재 + autopsy train 전용) → genome 단위로 격하. **이 청사진은 방어(착시 차단) 시스템으로는 진짜 개선이지만, 공격(엣지 발굴) 시스템이 아니다.**

**(c) 한 줄 결론:** 목표를 "2앵커 정직 운영 + 게이트"로 낮추고, attribution을 genome 단위로 격하하고, P-1(2앵커 합본 OOS)을 첫 실험으로 삼으면 — 살릴 가치가 있다.

---

## 10. 부록

### 10.1 orderflow v5.0 합성 atom 라이브러리 (atom_library.py 등록 후보)

화이트리스트 primitive로 인라인 합성. `build_v5_composite_template.py` 라인 근거.

| atom 이름 | 합성식 (요지) | 근거 라인 | 플래그 |
|---|---|---|---|
| 매수공격비_5초 | `누적초당매수수량(5)/누적초당매도수량(5)` (가드 포함) | v5 41~49 | — |
| 거래대금폭발배수_N | `초당거래대금/초당거래대금평균(N,1)` | v5 41~49 | — |
| 체결강도상승배수_N | `체결강도/체결강도평균(N,1)` | v5 41~49 | — |
| 상단1호가소화율 | `(매도잔량1N(1)-매도잔량1)/매도잔량1N(1)*100` | v5 50~56 | — |
| 상단5호가소화율 | 5호가 합 소화율 | v5 50~56 | — |
| 하단1호가붕괴율 | `(매수잔량1N(1)-매수잔량1)/매수잔량1N(1)*100` | v5 50~56 | — |
| 오호가매수비율 / 총호가매수비율 | 5단/총 잔량비 | v5 50~56 | — |
| VI근접 | `VI가격>0 and 현재가>=VI가격-VI호가단위*3` | v5 57 | — |
| 시가등락율 (갭) | `(시가-전일종가)/전일종가*100` | v5 10 | `accuracy:"degraded"` (전일종가 부재) |
| 스프레드틱 | `(매도호가1-매수호가1)/호가단위` | v5 9 | `accuracy:"degraded"` (절대 호가레벨 제거) |

> 비용 상수: `MIN_TAKE_FLOOR = 0.30` (왕복 0.21% + 슬리피지 마진).

### 10.2 F01~F20 요약 (build_v5 / v5.0 리포트 — 구조만, 숫자는 슬롯화)

| Flag | 의미 | 시간대 | 복합점수 가중 |
|---|---|---|---|
| F01 시가갭즉발 | 갭 + 시가+2틱 돌파 + 공격비 | 09:00:05~40 | 4 |
| F02 무갭시가돌파 | 무갭 + 시가대비 상승 + 5초 최고가 | 09:00:05~02:00 | 4 |
| F03 강갭눌림회복 | 강갭 + 저점+3틱 회복 | 09:00:20~02:00 | 3 |
| F04 매도흡수재돌파 | 매도흡수 후 10초 최고가 + 거래대금2배 | 09:00:30~05:00 | 4 |
| F05 거래대금고가돌파 | 30초 최고가 + 거래폭발 | 09:02~10:00 | 4 |
| F06 체결강도호가압력 | 체결강도 상승 + 호가총잔량비 | 09:02~15:00 | 3 |
| F07 횡보후발화 | 횡보감지 + 발화 | 09:05~20:00 | 3 |
| F08 라운드피겨소화 | 정수대 + 소화율 | 09:02~15:00 | 2 |
| F09 VI근접강세 | VI근접 + 체결강도 | — | 2 |
| F10 대형주추세 | 대형주 + 이평60 + 거래폭발 | 09:05~25:00 | 3 |
| F11 전일동시간비폭발 | 전일동시간비 + 전일비각도 | — | 2 |
| F12 회전율초반가속 | 회전율 + 거래대금각도 | — | 2 |
| F13 최고매수금액방어 | 최고매수>매도금액 | — | 2 |
| F14 매도벽소화돌파 | 1·5호가 소화율 | — | 2 |
| F15 하단매수잔량방어 | 붕괴율 낮음 + 매수비율 | — | 1 |
| F16 양봉성거래대금폭발 | 양봉 + 폭발배수 | — | 2 |
| F17 저가미갱신반등 | 저가미갱신 + 반등 | — | 2 |
| F18 시가상단재진입 | 시가 아래→위 재진입 | 09:02~15:00 | 2 |
| F19 이평20지지재돌파 | 이평20 지지 + 재돌파 | 09:05~25:00 | 2 |
| F20 오더플로우지속 | 1·5·10초 공격비 지속 | — | 2 |

> **★주의**: 위 F01~F20을 복합점수 합산으로 묶은 것이 곧 build_v5이고 -1.11억으로 죽었다(§2.3). 본 시스템은 이 표를 **합산 신호원이 아니라 atom_library 등록 후보 목록**으로만 쓴다. 신규 genome은 §4.2 하드캡(밴드 ≤2, flag ≤3)으로 묶고 앵커를 `branches[0]`에 고정한다.

### 10.3 엔진 미실재 atom 목록 (genome 생성에서 정적 차단)

| atom | 상태 | 처리 |
|---|---|---|
| 세력이탈점수 / 방어실패점수 | 엔진 부재 | **if-누적 스코어로만** sell_code 블록 템플릿 제공. atom 아님. 매도식 윈도우 집계 ≤8회 |
| 허수호가(스푸핑) | 취소주문 데이터 부재 | **구현 불가. atom_library 미등록, 프롬프트 금지어 추가** |
| 스프레드틱(절대 호가레벨) | `build_v5:9` 제거 공시 | 매도/매수호가1 근사만, `accuracy:"degraded"` |
| 고가/저가미갱신지속틱수 | 무한 역스캔 타임아웃 | `_engine_cost_errors`·p5(line 24)가 이미 차단. 유지 |

이미 강제 중: `_CALLABLE_WHITELIST`(line 148)·`_FUNC_REQUIRED_NAMES`(line 136)·`_engine_cost_errors`(line 201). **추가할 것: (a) 합성 atom 화이트리스트 확장(10.1), (b) 스푸핑/스프레드 금지어, (c) take floor 비용가드.**

### 10.4 [승인필요] 엔진 .py 수정 수반 항목

| # | 항목 | 사유 | 권고 |
|---|---|---|---|
| 1 | 횡단면 랭킹 하네스 | per-stock if-Buy 모델이라 순위변수 주입은 `trade/base_strategy.py` 개조 필요(하드교훈 c) | **범위 밖.** 본 청사진은 단일밴드/단일종목 한계 전제 |
| 2 | flag-level attribution 컬럼 | `back_static.py`의 `TRADE_RESULT_B_COLUMNS`에 플래그 발화/band_id 컬럼 추가 필요 | **격하 권고** — genome 단위 attribution으로 회피. flag Lift가 꼭 필요할 때만 승인 |
| 3 | 세력이탈/방어실패 엔진 내장화 | if-누적 스코어로 충분 | **개조 안 함 권고** |
| 4 | `bt_universe_end_time=92800` 하드클립 | 09:30 너머 데이터 활용 시 엔진/유니버스 설정 변경 가능 | 확인 후 승인 |
| 5 | PBO/CSCV·Deflated Sharpe | 6/5 해부가 "감사 최우선이나 미구현"으로 못박음 | 자유도 증가(P3) 선결 조건으로 권고 |

> **엔진 무수정 보증**: P0~P5 전 구간에서 `trade/base_strategy.py`는 손대지 않는다. 위 [승인필요] 항목은 전부 별도 승인 게이트.

---

## 부록 Z. 핵심 파일 경로 (절대경로)

**검증·확장 대상:**
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\tmap\template.py` (렌더러 — 39행 buy_code / 76행 render / 112행 coordinate_points / 169행 grid_points)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\scripts\gen_template_hypothesis.py` (136행 _FUNC_REQUIRED_NAMES / 148행 _CALLABLE_WHITELIST / 201행 _engine_cost_errors / 237행 validate_hypothesis / 308~312행 슬롯값 하한 검사 부재)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\brain\prompts\p5_template_hypothesis.md`
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\tmap\templates\seed_902905.json` (앵커 3밴드 출처)
- `C:\System_Trading\STOM\STOM_V.wt-dev\.omo\evidence\tmap-walkforward\build_v5_composite_template.py` (다밴드 완성형 — 41~122 합성, 197~242 렌더, **★묘비**)
- `C:\System_Trading\STOM\STOM_V.wt-dev\.omo\evidence\tmap-walkforward\llm_context_failure_lessons.md` (15~16행 v5 verdict -1.11억)

**재사용(배선만):**
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\scripts\tmap_sweep.py` (239줄)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\scripts\tmap_walkforward.py` (216줄, select_theta:49 / apply_washout:85 — 1슬롯 전용)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\fitness\holdout.py` (gate 배선 US-005 미완)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\scripts\claude_candidate_batch_eval.py` (141줄)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\autopsy\analyze.py` (441줄, B_COLUMNS 14 고정·is_holdout ValueError) / `segment.py` (603줄)
- `C:\System_Trading\STOM\STOM_V.wt-dev\ai_strategy_loop\controller\loop.py` (2353줄, GA 패턴 차용원)

**신규 생성 대상:**
- `ai_strategy_loop\tmap\atom_library.py` (Atom/Block — 10.1/10.3 등록)
- `ai_strategy_loop\tmap\mutator.py` (변이/교배 + ANCHOR_BANDS 동결)
- `ai_strategy_loop\tmap\refine_gate.py` (★재백테 게이트 — 하드교훈 a)
- `ai_strategy_loop\scripts\tmap_autopsy_loop.py` (얇은 폐루프 오케스트레이터)
- `ai_strategy_loop\tmap\templates\elite_archive.csv` (승격 저장소 — self.vars[40]~[49])
