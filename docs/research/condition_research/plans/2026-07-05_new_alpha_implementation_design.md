# 신규 알파 구현 설계서 — 규칙 채굴·이벤트 스터디 실행 설계 (2026-07-05)

> 상위 문서: `2026-07-04_new_alpha_research_program.md` (패러다임 심사·우선순위·봉인 판정). 본 문서는 그 실행 설계서다 — "실제로 가능한가"를 실측으로 판정하고, 알고리즘·코드 구조·대시보드 반영을 구현 가능한 수준까지 상세화한다.
> 성격: research-only. 모든 산출 조건식은 기존 게이트 체인(스모크→train→OOS→슬리피지 tick2)을 무특혜 통과해야 한다.

---

## 1부. 실현 가능성 실측 판정: **가능 — 신규 발명이 아니라 조립 문제**

### 1.1 데이터 실측 (2026-07-05 재검증)

| 항목 | 실측값 | 설계 함의 |
|---|---|---|
| tick 저장 컬럼 | **54컬럼 실명 확인** (stock_tick_20240603.db PRAGMA): index, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, **VI해제시간, VI가격, VI호가단위**, 초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, **매도호가5~1, 매수호가1~5, 매도잔량5~1, 매수잔량1~5**, 매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 | 라벨(진입 매도호가1/청산 매수호가1)·미시구조 피처(잔량 불균형·스프레드)·**E1 VI 해제 사건이 전부 저장 컬럼으로 계산 가능** — 엔진 재계산 파생 19항 없이 v1 완결 (반-C20 논거 성립 범위 내) |
| moneytop | index + 거래대금순위 (초당 point-in-time 유니버스) | "그 초에 관측된 종목만 표본화" — 유니버스 소급 불가(갭4) 자연 해결 |
| 규모 | 952일 × 평균 ~77종목 × ~1,675행/일 ≈ **1.2억 행 / 62GB** | 일별 DB 순회 스트리밍으로 1회 빌드 수 시간~1일 (§3.1) |
| 소프트웨어 | sklearn 1.8.0 ✅ / pandas 3.0.2 ✅ / **pyarrow ❌ 미설치** | 결정 지점 D-1 (§7): v1은 numpy .npz 샤드로 무설치 시작 가능 |
| 대시보드 | FastAPI(`dashboard/app.py` create_app, /ui/* 라우트) + 프론트 번들 체계(lab/pro/verdict.html) | additive 라우트 `/ui/alpha-lab` + `/api/alpha/*`로 무충돌 확장 (§6) |

### 1.2 재사용 인프라 (전부 커밋 완료 상태)

read-only sqlite URI 패턴·INSERT-only 등재기(`scripts/register_chart_sulsa_conditions.py` 선례), 공식 warm64 프로파일+청크 백테 프로토콜(`claude_candidate_batch_eval`, P5 실증), krx 호가단위·슬리피지(`fitness/slippage_profiles.py`), 거래 원장/분석 카드/축 원장(autopsy·controller), provenance 원장 패턴, 사전등록·n_trials 규율 문서. **새로 만드는 것은 라벨 빌더·채굴기·사건 감지기·번역기 4개 층뿐이다.**

---

## 2부. 공통 아키텍처

### 2.1 패키지 구조 (새 워크트리 `STOM_V.wt-alpha`, 브랜치 `research/alpha-lab-20260704`)

```
alpha_lab/
  __init__.py
  registry.py          # 사전등록 봉인(JSON+sha256 커밋) + n_trials 원장(JSONL append-only)
  dataset/
    reader.py          # read-only sqlite 스트리머: 일별 DB → moneytop 필터 → 종목테이블 54컬럼 순회
    labels.py          # L1 고정지평 / L2 트리플배리어 라벨 (전향 전용, tick2+수수료 차감)
    cache.py           # float32 샤드 캐시 (v1: npz / v2: parquet — D-1)
  mining/
    trees.py           # DecisionTree/HistGBM 학습, 리프 경로 추출 (seed 고정)
    stats.py           # lift·support + 일 블록 부트스트랩 CI + BH-FDR q<0.05
  events/
    detectors.py       # E1~E5 인과 상태기계 감지기 (t 시점 판정에 t 이하 데이터만)
    outcomes.py        # 전방 결과 측정 + 층화 셀 집계 (격자 축 재사용)
  translate/
    idioms.py          # 피처→STOM 변수 사전 (v1 = 저장 54컬럼 한정)
    codegen.py         # 리프/사건 → 조건식 생성 + compile·금지토큰·스코프·원리게이트 검증
  bridge/
    registrar.py       # loop_strategies INSERT-only 등재 (ALP_ 접두, 백업·멱등·충돌보고)
    receipts.py        # provenance·영수증 (chart_sulsa 원장 스키마 확장)
cli/alpha_dataset.py  cli/alpha_mine.py  cli/alpha_events.py  cli/alpha_translate.py
tests/unit/test_alpha_dataset.py ... (모듈당 1파일, 합성 데이터 + 실DB 1일 스모크)
```

### 2.2 공통 코딩 규칙

파일 800줄·함수 50줄·print 금지·DB는 `file:...?mode=ro` URI 전용·전략 DB는 INSERT-only(백업 선행)·모든 난수 seed 고정 인자·시계 값은 호출자 주입. 사전등록 봉인 파일(`alpha_lab_preregistration_v1.json`)의 sha256을 커밋에 남긴 뒤에만 채굴 실행 — 봉인 이후 임계값·피처 목록·사건 정의 변경은 새 n_trials로만 가능.

---

## 3부. P1 규칙 채굴 — 알고리즘 상세

### 3.1 라벨 빌더 (`dataset/labels.py`)

```
for day_db in stock_tick_YYYYMMDD.db (발견창):            # read-only
  for code in tables(day_db) if code != 'moneytop':
    df = read_54cols(code)                                # 초당 1행, 09:00:01~09:30:00
    for t0 in grid(df.index, stride=5초):
      if not in_moneytop(code, t0): skip                  # point-in-time 유니버스
      entry = 매도호가1[t0 + 1초]                          # 결측 초 → 표본 제외(정직)
      if t0 > 09:30:00 - h_max: skip                      # 절단 방지
      for h in (60, 180, 300):
        exit_ = 매수호가1[t0 + h]
        net = (exit_ - entry)/entry - slip(tick2, krx단위) - 수수료세금
        L1[h] = (net >= +0.01)
      L2 = triple_barrier(TP+3%, SL-2%, 300초, 매수호가1 경로)  # 먼저 닿는 쪽
      emit(t0행 54컬럼 스냅샷 + 파생피처 + L1/L2)  →  float32 샤드
```

- 진입/청산을 **반대편 호가**로 잡아 스프레드 비용을 라벨에 내재화 — CSS_V7을 죽인 "라벨-체결 갭"의 1차 방어. 최종 방어는 ρ 게이트(상위 문서 §3.2, 3분지 봉인).
- MVP 표본: 2023년 30일 + 2024년 30일(계절 매칭) ≈ 150만 행. 본 빌드: 2022-03~2024-12 ≈ 2,400만 행(stride 5초), 검증 2025-01~2026-02는 **봉인** — 채굴에 절대 미사용.

### 3.2 피처 v1 화이트리스트 (저장 컬럼 + 같은 초 내 사칙연산만 — 롤링 금지)

원시 15: 등락율, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 당일거래대금, 고저평균대비등락율, 저가대비고가등락율, 라운드피겨위5호가이내, 관심종목.
동일 초 파생 10 (lookahead 불가능 — 같은 행 안에서만 계산): 잔량불균형=(매수잔량합-매도잔량합)/(합), 스프레드율=(매도호가1-매수호가1)/현재가, 매수벽비율=매수잔량1/매수총잔량, 매도소진율=초당매도수량/매도잔량1, 순매수수량비=초당매수수량/max(초당매도수량,1), 고가대비위치=(현재가-저가)/max(고가-저가,ε), 시가대비율=현재가/시가-1, VI거리율=현재가/VI가격-1, 최고매수가대비=현재가/최고매수가격-1, 당일매수매도비=당일매수금액/max(당일매도금액,1).
**총 25개 — 사전등록에서 전수 열거·봉인.** 엔진 재계산 파생 19항(이동평균 계열 등)은 v2로 이월(패리티 재계산기 비용 포함 — 상위 문서 정정 반영).

### 3.3 채굴 (`mining/trees.py`)

- 분할: 일 단위 블록. purge 1일 + embargo 1일 (라벨 지평 300초 << 1일이라 보수적).
- 모델: DecisionTree(depth≤4, min_samples_leaf≥2,000, seed 고정) × 피처 서브셋 K개(seed 열거) + HistGBM 1개(피처 중요도 참고용 — 규칙 추출은 트리만).
- 리프→규칙: 루트→리프 경로의 (피처, 부등호, 임계값) conjunction. **채택 기준(봉인)**: 리프 lift ≥1.5, support ≥2,000, 발견창 내 전 연도(2022/2023/2024) 각각 lift>1.
- 통계: 일 블록 부트스트랩(일 단위 재표집 1,000회)으로 lift CI 산출 — stride 5초 중첩 라벨의 유효 표본 과대평가 방어(심사 지적 반영). 전 리프 수를 n_trials 원장에 합산. BH-FDR q<0.05.

### 3.4 번역 (`translate/codegen.py`)

리프 `{체결강도>127.3 ∧ 잔량불균형>0.18 ∧ 시분초<90600}` → idioms 사전으로 STOM 매수식 생성(잔량불균형은 저장 컬럼 조합식으로 전개). 매도식은 생성하지 않고 **검증 완료 hard-stop 계열 고정**(수익률 하드스톱 + force_exit 92900). 생성 후 compile → 금지토큰 → 변수 스코프 → 원리 게이트(advisory) 통과 필수. 임계값은 소수 1자리 반올림 봉인(임계값 미세조정 = 새 n_trials).

### 3.5 엔진 확인·게이트 (기존 인프라 그대로)

`bridge/registrar.py`로 `ALP_RM_` 접두 안전명 INSERT-only 등재 → `claude_candidate_batch_eval` + 공식 warm64 프로파일(betting "5"/avg_time 30) 훈련 창 재현 10규칙 → **ρ 3분지 게이트**(≥0.5 진행 / 0.2~0.5 보류·번역 결함 1회 재판정 / <0.2 포기) → 생존 시 OOS 봉인창 1회 → 통과 규칙은 축 원장·passport 등재 후 기존 힐클라임 시드로 환류.

### 3.6 MVP-1 산출물 경로

`docs/research/condition_research/research_runs/alpha_lab_20260705/` 아래: preregistration(sha 봉인), dataset_build_receipt, mining_report(리프 전수+채택), translation_receipt, rho_gate_verdict. 실패해도 전부 커밋(실패도 자산).

---

## 4부. P2 이벤트 스터디 — 알고리즘 상세

### 4.1 사건족 조작 정의 (저장 컬럼 실명 기준 — 사전등록에서 봉인)

| 사건 | 조작 정의 (인과 — t 이하 데이터만) | 근거 컬럼 |
|---|---|---|
| E1 VI 해제 재개 | `VI해제시간`이 당일 최초로 유효값 전이 + 해제 후 첫 `초당거래대금>0` 행 | **저장 컬럼 직접** (기존 D-3 결정 지점 해소 — 추정 불필요) |
| E2 당일 신고가 돌파 | `현재가 ≥ 고가` 이면서 직전 초 `고가` 대비 갱신 | 고가(당일 러닝) |
| E3 거래대금 서지 | `초당거래대금 ≥ k × 당일거래대금/경과초` (k 봉인, 롤링 없이 저장 컬럼만) | 초당·당일거래대금 |
| E4 갭 상승 개장 | `전일비` 기반 시가 갭 구간 (09:00:01~09:00:30 진입 한정) | 전일비, 시가 |
| E5 라운드피겨 이탈 | `라운드피겨위5호가이내` 1→0 전이 (직전 1초 참조 — 인과 명시) | 라운드피겨위5호가이내 |

각 사건에 **불응기(refractory) 종목당 120초** — 동일 랠리 중복 계상(의사반복) 방지. 사건족·k·불응기 전부 사전등록 봉인.

### 4.2 측정·통계 (`events/outcomes.py`, `mining/stats.py` 공유)

진입 t0+1초 `매도호가1`, 지평 60/180/300초 `매수호가1` 청산, tick2 차감 — P1과 동일 비용 모형(비교 가능성). 층화: 시총 4 × 시간밴드 6 × 등락율 3 (격자 축 정의 재사용). 셀 최소 표본 **min_n≥200 봉인**. 셀별 EV·일 블록 부트스트랩 CI → BH-FDR q<0.05 → **이중 플라시보**(무작위 시각 매칭 표본 + 사건 +60초 시프트 표본과 유의 분리). 발견 2022-03~2024-12 / 검증 2025-01~2026-02 봉인, FDR 생존 셀만 각 1회.

### 4.3 번역·패리티

생존 셀 → "사건 감지 + 층화 조건" 조건식 생성. **오프라인 감지기 ↔ 조건식 per-tick 평가 일치율 ≥95% 게이트** — 상태 전이형(E1/E5)이 STOM N-함수로 표현 불가하면 그 사건족은 정직 탈락(CSS_V7 번역 갭 재발 방지). E4는 `전일비` 저장 컬럼이라 역산 트릭 불요.

---

## 5부. 코드 작성 방향 — 구현 순서와 테스트

| 순서 | 모듈 | 테스트 (합성 + 실DB 1일 스모크) | 규모 |
|---|---|---|---|
| 1 | registry.py (봉인·원장) | 봉인 sha 결정성, 봉인 후 변경 거부, n_trials 합산 | S |
| 2 | dataset/reader.py + labels.py | 합성 1일 DB로 라벨 수기 검증(진입·청산 호가, 절단, 결측 skip, moneytop 필터), 트리플배리어 먼저 닿는 쪽 | M |
| 3 | dataset/cache.py | npz 왕복·float32·샤드 결정성 | S |
| 4 | mining/trees.py + stats.py | 심어둔 패턴(체결강도>k에서만 양성) 회수, 블록 부트스트랩 CI 커버리지, FDR 경계 | M |
| 5 | translate/ | 리프→코드 왕복, 25피처 전수 번역 가능성, compile·게이트 통과, 임계 반올림 봉인 | M |
| 6 | events/ | 각 사건 합성 시나리오 감지/불응기/인과성(미래 참조 시 실패하는 테스트), E1 실DB 1일 검출 수 | M |
| 7 | bridge/ | register_chart_sulsa 테스트 패턴 재사용(INSERT-only·멱등·충돌) | S |
| 8 | CLI 4종 | tmp_path 산출·영수증 스키마 | S |

양성 대조 필수 2건: (a) 채굴기에 rr8_12 진입 절을 규칙으로 강제 주입 → 양의 lift 검출 확인, (b) 사건 감지기에 합성 "확실 사건" 주입 → 셀 EV 회수. 실패 시 파이프라인 결함이므로 진행 중단.

## 6부. 대시보드 반영 계획 (FastAPI additive — 기존 화면 무접촉)

### 6.1 백엔드 (`dashboard/app.py` 또는 신규 `dashboard/alpha_api.py` 라우터 include)

| 엔드포인트 | 내용 | 데이터 원천 (읽기 전용 JSON) |
|---|---|---|
| GET /api/alpha/status | 사전등록 봉인 상태·n_trials 카운터·현재 단계 | registry 원장 |
| GET /api/alpha/dataset | 빌드 진행(일/종목 커버리지, 라벨 양성률 분포) | dataset_build_receipt |
| GET /api/alpha/rules | 규칙 리더보드(리프별 lift/support/CI/FDR q/연도 재현/번역·엔진 상태) | mining_report + translation_receipt |
| GET /api/alpha/events | 사건족×층화 셀 히트맵 데이터(EV·CI·플라시보 델타·FDR 생존) | event_cells_report |
| GET /api/alpha/funnel | 퍼널: 발견→FDR 생존→번역→등재→엔진 확인→ρ/OOS 게이트 단계별 수 | 전 영수증 집계 |
| GET /ui/alpha-lab | 신규 화면 | — |

구현 규칙: 파일 기반 read-only 서빙(대시보드가 연구 산출물을 소유하지 않음), 기존 라우트·번들 무수정, TestClient 단위테스트 동반 (기존 dashboard 테스트 패턴).

### 6.2 프론트 패널 5종 (`frontend/alpha.html` 신규 — lab.html 패턴 복제)

① 상태 헤더(봉인 sha·n_trials·단계 배지), ② 규칙 리더보드 테이블(정렬·lift CI 바), ③ 사건 셀 히트맵(기존 rp-heatmap.jsx 패턴 재사용 — 시간밴드×시총, 색=EV), ④ 퍼널 차트(단계별 생존 수 — "정직한 깔때기"가 핵심 메시지), ⑤ ρ 게이트/OOS 판정 카드(3분지 결과·근거 수치). 구현 순서: API→테이블→히트맵 (차트 라이브러리 신규 도입 없이 기존 번들 관례 준수).

## 7부. 결정 지점·일정·리스크

| # | 결정 지점 | 권고 |
|---|---|---|
| D-1 | 캐시 포맷: pyarrow 설치(표준·압축 우수) vs npz(무설치) | **v1 npz로 즉시 시작**(의존성 0), 본 빌드 전 pyarrow 설치 승인 요청 |
| D-2 | 파생 19항(이동평균 계열) 피처 편입 | v2로 이월 — avg_list 동결 패리티 재계산기 비용을 치를 가치가 v1 결과로 입증된 후 |
| ~~D-3~~ | ~~VI 사건 감지 방법~~ | **해소** — VI해제시간·VI가격 저장 컬럼 실증 (본 문서 §1.1) |
| D-4 | 착수 시점 | warm64 스윕(G010) 종료 후 워크트리 생성 → MVP-1·MVP-2 병행(동일 reader 공유). 대시보드 최소판은 백테 불요라 즉시 가능 |

일정 추정: 모듈 1~5(규칙 채굴 경로) 3~4일 + MVP-1 실험 3일 / 모듈 6(이벤트) 2일 + MVP-2 실험 3일(병행) / 대시보드 최소판 2~3일. **총 약 1.5~2주에 두 MVP 판정 도달.**

핵심 리스크 재확인: ① 라벨-체결 갭(ρ 게이트가 방어선 — 실패 시 CSS_V7 재판으로 포기), ② stride 중첩의 유효 표본 과대평가(일 블록 부트스트랩 의무), ③ 다중검정(n_trials 전수 합산 + FDR q<0.05 단일 봉인), ④ 격자 프로그램과 발견 중복(동일 화이트리스트 축 임계 발견 시 축 원장 대조 후 중복 표기).
