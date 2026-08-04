# QSP7 G-0 핸드오프 — 손실 영역 탐구 엔진 착수

> 작성일: 2026-08-03 (다음 세션 기준일 2026-08-04)
> 저장소: `C:/System_Trading/STOM/STOM_V.wt-dev`
> 브랜치: **`feature/qsp7-g0-loss-region-engine-20260803`** (base `loop/process-research-pipeline`)
> 문서 역할: **대화 맥락 없이도 G-0 개발을 그대로 시작**할 수 있는 최상위 인계 문서
> 구현 사양: [2026-08-03_qsp7_g0_loss_region_engine_design.md](./2026-08-03_qsp7_g0_loss_region_engine_design.md) ← **반드시 먼저 읽을 것**
> 안전 경계: 운영 DB 쓰기·실거래 반영·전체청산 이후 시세·OOS 재학습·후보 자동 채택 금지

---

## 0. 🧭 30초 요약

| 항목 | 내용 |
|---|---|
| 지금까지 | 플랫폼 P0~P6 완성(화면 16) → R1(매도 축, 채택 0) → R2(매수 필터 축, **adoptable 2건**) |
| 지금 할 일 | **G-0: 손실 영역 탐구 엔진** — 조건식 문법을 1종 → 6종으로 넓히고, 세대 반복으로 누적 개선 |
| 왜 | 현재 생성기는 `변수 ≥ 상수` 한 줄만 만든다. 사용자가 쓰는 문법 8종 중 1종. 골짜기·다중밴드 손실은 **표현 자체가 불가** |
| 첫 작업 | ~~`G-0a`~~ ✅ **완료** → 다음은 `G-0b` 패턴 카드 + 구간 생성기 |
| 레인 우선순위 | **tick 먼저**(최신 2년 · **엔진 64 · 런 1회 11분 기준**) → min 나중 |
| **평가 방식** | **v2: 최신 2년 단일 연속 런 + CSV 날짜 분할** (후보당 백테 2회 → **1회**) |
| 기간 | 3.5~4일 (엔진 1.5일 + v2 배선 0.5일 + 화면 1일 + **세대 루프 약 3시간 7분** + 보고 0.5일) |
| 기대/한계 | 홀드아웃 건당 −5,241 → **−4,400원대(약 15% 손실 축소)**. **흑자 전환은 안 된다** |

---

## 1. 📌 현재 상태 스냅샷

### 1.1 Git

| 항목 | 값 |
|---|---|
| 작업 브랜치 | `feature/qsp7-g0-loss-region-engine-20260803` |
| 병합 대상 | `loop/process-research-pipeline` (게이트 통과 후 ff-merge) |
| 최근 커밋 | `3197a0ad` 설계서 재검토 · `189974e0` 설계서 초안 |
| loop 최신 | `f5f42138` (R2 라운드까지 병합 완료) |
| origin | **push 미완** — `origin/loop/...` = `73cfafab`, 로컬이 122+ 커밋 앞섬 |
| 주의 | GitKraken 실행 중이면 `index.lock` 충돌. 0바이트·git.exe 부재 확인 후 삭제하고 진행 |

### 1.2 검증 기준선 (이 수치가 회귀 판정 기준)

| 검증 | 마지막 값 |
|---|---|
| QSP7 집중 테스트 | **1,023 passed** (2026-08-04 실측·6분 28초) — 이전 기재값 "146" 은 오기였다 |
| 전체 `tests/unit/` | 18 failed / 6,7xx passed — **18건은 전부 기존 실패**(limitation_ledger 2026-08-03 고정) |
| nonrelease verifier | PASS |
| runtime JSX | **113 JSX / 563 files PASS** |
| 번들 | `app.js v=59373a0a` · `trade-path.css?v=20260803c` |

### 1.3 준비된 연구 자산 (재사용 — 재생성 불필요)

| 자산 | 값 |
|---|---|
| **tick 최신 2년 통합 CSV (v2 기준·오프라인 분석용)** | `stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260803234054.csv` · **86,390건 · 475일 · −452,783,575원 · 건당 −5,241원** · CLI 런(엔진 64, 523초) — **대시보드 job 아님**, G-1에서 재생성 필요 |
| tick 설계 control (v1 참고) | job `20260803_193432_..._72661` · 120,118건 · 2022-04~2024-03 |
| tick 표본밖 control (v1 참고) | job `20260803_193437_..._77265` · 82,290건 · 2024-04~2026-02 |
| min 설계 control | job `20260803_191118_..._78453` · 5,109건 · −37,544,661원 |
| min OOS control | job `20260803_191126_..._86231` · 1,550건 · −8,945,721원 |
| min 경로 분석 | `tp-58491917e7144717` (sidecar 보존 — 재분석 불필요) |
| min R2 채택가능 후보 | `QSP7_min_필터_등락율각도_20260803_090bc7` (OOS +2.82M/+1,848원·건) |
| **레인 manifest (v2로 갱신 필요)** | tick: **평가 20240304~20260227**(475일) · 분할 20250825 · 세션 090000~092800<br>min: **평가 20250407~20260227**(213일) · 분할 20251201 · 세션 090000~152800 |

> ⚠️ `ai_strategy_loop/dashboard/lane_manifest.py` 의 tick 구간은 아직 **v1 값(2022-04-01~2024-03-31 / 2024-04-01~2026-02-27)**이다. **G-0d에서 v2 구간으로 갱신**해야 한다(문서 `lane_manifest_tick.md` 동시 수정).

---

## 2. 🎯 G-0가 푸는 문제 (한 장 요약)

### 2.1 현재 한계

```python
# 지금 생성기가 만들 수 있는 유일한 형태
elif not (회전율 >= 5.67):
    매수 = False
```

### 2.2 사용자가 실제로 쓰는 문법 (직접 작성 조건식 128줄에서 확인)

양측 범위 · 변수 대 변수 배수 · 양측 배수 범위 · 비율(가속도) · 이전값 대비 · 일중 위치 · 계층(시간밴드×시총) — **8종 중 1종만 지원**.

### 2.3 실측 근거 (tick 120,118건)

| 발견 | 수치 |
|---|---|
| 시간대×시총 20칸 | **전부 손실**(−3,750 ~ −6,829원) → 이 축으로는 못 자름 |
| 상위 12개 변수 | **설계 최악 분위 = 표본밖 최악 12/12** → 제거가 표본 밖으로 전이됨 |
| 체결강도 형태 | **다중 밴드**(D1 + D3~D7 나쁨) — 단측으로 표현 불가 |
| 형태 정확도의 값 | 골짜기로 잘못 잡으면 +310원, **다중 밴드로 정확히 잡으면 +682원(2.2배)** |
| 단측의 대가 | 같은 효과를 단측으로 내려면 **거래 74% 소멸**(유지율 26%) |
| 수렴 곡선 | 세대별 추가 개선 +392 → +194 → +76 → +98 (**크게 후 체감**) |

---

## 3. 🔨 G-0 작업 순서

| 단계 | 산출물 | 완료 게이트 | 예상 |
|---|---|---|---|
| ~~**G-0a**~~ ✅ | `ai_strategy_loop/autopsy/loss_profile.py` + 테스트 27건 — **완료(2026-08-04)**<br>결과·실데이터 검증·결함 4건: [2026-08-04_qsp7_g0a_loss_profile_evidence.md](./2026-08-04_qsp7_g0a_loss_profile_evidence.md) | ✅ 게이트 4종 통과 · 2D 포켓 5건 검출 | 완료 |
| **G-0b** | `ai_strategy_loop/revision/pattern_cards.py`<br>`ai_strategy_loop/revision/region_proposer.py` | 사용자 문법 8종 카드 추출(임계값 미저장) · 복합 절 1~4개 생성 · intent gate(삽입 절 외 diff 0) | 1일 |
| **G-0c** | 페이지 17~21 + 8b/11 강화 + API 6종 | JSX PASS · 한국어 안내 · 예산 게이지 · 재유입 편향 배지 · 시각화 명세 준수 | 1일 |
| **G-0d** | **평가 프로토콜 v2 배선** — pair `period` 인자 · gate 2-job 모드 · lane_manifest v2 구간 갱신 · "홀드아웃" 명칭 통일 | 기존 4-job 모드 회귀 없음 · 두 구간 합계 = 전체(검산) | 0.5일 |
| **G-1** | tick 기준선 1회(대시보드) + 1세대 후보 3~4개 | 홀드아웃 동반 개선 · 예산 준수 | **11분 + 44분 = 55분** |
| **G-2~G-4** | tick 2~4세대 | 〃 | **세대당 ~44분** |
| **G-5** | `rounds/G_tick_20260804.md` + 문서·원장 갱신 | 실패 포함 전량 기록 | 0.5일 |

### 3.1 G-0a 상세 (첫 작업 — 여기서 시작)

**입력**: 설계 CSV + 홀드아웃 CSV, 변수 목록(B_* 31 + 카탈로그 파생)
**핵심 규칙**
1. 10분위 경계는 **설계에서만** 산출 → 홀드아웃에 동일 경계 적용(누출 금지)
2. 분위당 최소 표본 `max(100, 전체×0.5%)` — tick 500 / min 100
3. 형태 판정 **순서**: `multi_band` → `valley` → `tail_*` → `monotone_*` → `flat`
   - **multi_band를 먼저 검사한다**(초안 오류 재발 방지)
4. 홀드아웃에서 최악 구간이 하위 40% 안이면 `confirmed`, 아니면 `unstable`(후보 제외)
5. 2D: 상관 |r|<0.6 쌍만 · 칸당 최소 50건 · Welch t + BH-FDR(q≤0.10) · 인접 병합 · 직사각형 근사 손실 30% 상한

**출력 스키마**는 설계서 §4.1 참조.

---

## 4. 🛡️ 절대 어길 수 없는 규율

| # | 규율 |
|---:|---|
| 1 | 설계·홀드아웃 **양쪽에서 손실**인 구간만 제거 |
| 2 | 고립 1칸 금지 — **인접 2칸 이상 연속**만 |
| 3 | 임계는 **분위 격자 위에서만** — 임의 미세조정 금지 |
| 4 | 누적 유지율 **40% 하한**(설계·표본밖 중 낮은 쪽) · 1세대 ≤25%p, 이후 ≤12%p |
| 5 | 총손익이 아니라 **건당 엣지**가 최종 판정 |
| 6 | 시뮬레이터 추정은 **재유입 미반영** — 순위용, 공식 pair가 정본 |
| 7 | 한 라운드 **한 축**(매수 축이면 매도식 고정) |
| 8 | 채택은 **사람 승인** — gate `adoptable`은 승인 요청일 뿐 |
| 9 | 실패·0건·미지원을 **숨기지 않고 기록** |
| 10 | **연속 런은 자본이 이어진다** — "OOS"가 아니라 **"홀드아웃"**으로 부르고, 판정은 **건당 손익 중심**으로 한다 |
| 11 | **엔진 64 유지.** 프로세스 생성 155초는 64개 최초 기동 비용이다. 일정은 **런 1회 11분(보수값)**으로 계산한다 |

> ⚠️ 과거 실패 기록: **"깊이1.5 양측범위 → 표본외 −11%(부호 반전)"**. 양측 범위는 강력한 만큼 위험하다. 위 9개 규율은 그 재발 방지책이다.

---

## 5. ✅ 재개 직후 확인 명령

```powershell
Set-Location -LiteralPath 'C:\System_Trading\STOM\STOM_V.wt-dev'
git branch --show-current          # feature/qsp7-g0-loss-region-engine-20260803
git log -3 --oneline
git status --short -- ai_strategy_loop tests docs

python -m pytest tests/unit/autopsy tests/unit/dashboard tests/unit/test_sell_proposer.py `
  tests/unit/test_buy_filter_proposer.py tests/unit/test_hier_flat_adapter.py `
  tests/unit/test_variable_catalog.py tests/unit/test_trade_path_pipeline.py -q   # 기대 1,023+ passed (약 6분 30초)

python scripts/verify_nonrelease_sync.py
node ai_strategy_loop/dashboard/webui-build/build-app.mjs
node ai_strategy_loop/dashboard/webui-build/runtime-jsx-check.mjs                  # 기대 113/563 PASS
```

대시보드가 필요할 때(전략 등록까지 하려면 env 필수):

```powershell
$env:STOM_DASHBOARD_ALLOW_STRATEGY_WRITE=1
python -m ai_strategy_loop --host 127.0.0.1 --port 8771
# http://127.0.0.1:8771/?tab=backtest
```

---

## 6. 📚 읽는 순서

| 순서 | 문서 | 목적 |
|---:|---|---|
| 1 | **이 문서** | 어디서 무엇부터 |
| 2 | `2026-08-03_qsp7_g0_loss_region_engine_design.md` | **구현 사양(필수)** |
| 3 | `2026-08-03_qsp7_master_execution_plan.md` | 전체 실행 정본·페이지 설계·점수 |
| 4 | `rounds/R2_min_buyfilter_20260803.md` | 직전 라운드 결과와 교훈 |
| 5 | `rounds/R1_min_20260803.md` | 매도 축 실패 기록(반면교사) |
| 6 | `2026-08-03_qsp7_execution_midpoint_check.md` | 실행 이력·자산 목록 |
| 7 | `limitation_ledger.md` | 한계·기존 실패 18건 |
| 조건식 문법 | `utility/ai_agent/strategy.txt`, `rules.txt` | 생성 문법 근거 |
| 사람 조건식 | strategy DB `Tick_B_902_905_Study_2` | 패턴 카드 원본 |

---

## 7. 🤖 재개 마스터 프롬프트

```text
STOM QSP7 G-0(손실 영역 탐구 엔진) 개발을 이어서 진행하세요.

저장소·브랜치:
- 경로: C:/System_Trading/STOM/STOM_V.wt-dev
- 브랜치: feature/qsp7-g0-loss-region-engine-20260803 (base: loop/process-research-pipeline)
- 다른 위치라면 같은 브랜치를 찾아 절대경로를 다시 확인하세요.

먼저 읽을 것(순서대로):
1. docs/research/quant_scoring_pipeline/HANDOFF_2026-08-04_QSP7_G0_손실영역엔진.md
2. docs/research/quant_scoring_pipeline/2026-08-03_qsp7_g0_loss_region_engine_design.md  ← 구현 사양
3. docs/research/quant_scoring_pipeline/2026-08-03_qsp7_master_execution_plan.md
4. docs/research/quant_scoring_pipeline/rounds/R2_min_buyfilter_20260803.md
5. 조건식 생성 작업이면 utility/ai_agent/strategy.txt 와 rules.txt 를 반드시 읽으세요.
6. git branch/HEAD/scoped status 와 8770·8771 listener 를 실제로 확인하고 문서의 런타임
   상태를 그대로 믿지 마세요.

무엇을 만드는가:
공식 백테스트 결과에서 "지속적으로 손실이 나는 영역"을 사람이 쓰는 조건식 문법
(단측·양측 범위·다중 밴드·배수·비율·이전값 대비·2D 조합)으로 정확히 표현해 제거하고,
그 결과를 다음 세대 기준선으로 삼아 반복하며, 개선이 체감해 수렴하면 멈추는 엔진입니다.

평가 프로토콜 v2 (반드시 이 방식으로):
- 설계/OOS 분리 런이 아니라 **최신 2년 연속 1회 런 + CSV 날짜 분할**로 평가합니다.
  · tick 평가구간 20240304~20260227(475거래일), 분할 경계 20250825
    (설계 20240304~20250822 / 홀드아웃 20250825~20260227)
  · min 평가구간 20250407~20260227(213거래일), 분할 경계 20251201
- 후보당 백테스트는 1회입니다(기존 2회에서 절반).
- 엔진은 64를 유지합니다. 프로세스 생성 155초는 64개 엔진 최초 기동 비용입니다.
  일정은 보수값 **런 1회 11분**으로 계산합니다(실측 8분 43초 + 기동 편차·큐·기록 여유).
- 연속 런은 자본이 이어지므로 "OOS"가 아니라 "홀드아웃"으로 부르고,
  판정은 총손익이 아니라 건당 손익 중심으로 합니다.

작업 순서:
- G-0a: ai_strategy_loop/autopsy/loss_profile.py
  (10분위·형태 6종·홀드아웃 검증·2D 포켓·Welch t + BH-FDR·파레토)
  * 형태 판정 순서는 multi_band 를 valley 보다 먼저 검사합니다(초안 오류 재발 방지).
- G-0b: ai_strategy_loop/revision/pattern_cards.py + region_proposer.py
  (사용자 조건식에서 골격만 추출, 임계값은 저장 금지 / 복합 절 1~4개 생성 / intent gate)
- G-0c: 페이지 17~21 신설 + 8b·11 강화 + API 6종
  * 시각화는 설계서 §6.1 명세를 따르고, 자본곡선·언더워터·히트맵은
    기존 /bt/analysis/* (t_start/t_end 지원)과 bt-equity-charts.jsx 등을 재사용합니다.
- G-0d: 평가 프로토콜 v2 배선
  * official-pair 에 period 인자, promotion-gate 에 2-job 모드 추가(4-job 모드는 유지)
  * lane_manifest.py 의 tick 구간을 v2(20240304~20260227, 분할 20250825)로 갱신하고
    docs 의 lane_manifest_tick.md 도 함께 수정
- G-1: 대시보드로 tick 기준선 1회 실행(11분) → 1세대 후보 3~4개(각 1회 런, 44분)
- G-2~G-4: 2~4세대 (세대당 약 44분, 루프 전체 약 3시간 7분)
- G-5: rounds/G_tick_*.md 보고서 + 문서·원장 갱신

절대 규율:
- 설계·홀드아웃 양쪽 손실 구간만 제거, 고립 1칸 금지(연속 2칸 이상)
- 임계는 분위 격자 위에서만, 임의 미세조정 금지
- 누적 유지율 40% 하한(설계·홀드아웃 중 낮은 쪽), 1세대 25%p·이후 12%p 배분
- 판정은 총손익이 아니라 건당 엣지 + 유지율
- 제거 시뮬레이터 추정은 재유입 미반영이므로 순위용으로만 사용
- 한 라운드 한 축(매수 축이면 매도식 고정)
- 채택은 사람 승인 사항. gate adoptable 은 승인 요청일 뿐
- 실패·0건·미지원 결과를 숨기지 말 것

재사용할 자산(재생성 금지):
- tick 최신 2년 통합 CSV(오프라인 분석용):
  backtest/csv/stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260803234054.csv
  (86,390건·475일·-452,783,575원·건당 -5,241원) — 단 대시보드 job 이 아니므로
  pair/gate 용 기준선은 G-1 에서 대시보드로 1회 재생성합니다.
- min 설계 job 20260803_191118_..._78453 / OOS job 20260803_191126_..._86231
- min 분석 tp-58491917e7144717 (sidecar 복원)
- 기존 엔진: autopsy/recovery_insight.py, revision/buy_filter_proposer.py,
  hier_ast.parse_leaves_flexible, dashboard/trade_path_official_api.py(axis 모드),
  /bt/analysis/* 8종(기간 필터 지원), bt-equity-charts.jsx·chart-primitives.jsx

완료 규칙:
- 각 단계는 테스트를 먼저 쓰고 실패를 확인한 뒤 최소 구현합니다.
- 단계마다 QSP7 집중 테스트(기대 146+), verifier, runtime JSX 를 통과시키고
  한국어 제목으로 작게 커밋합니다.
- 페이즈 게이트에서 loop/process-research-pipeline 로 ff-merge 합니다.
- 관측/자문/공식 결과를 각각 별도 표로 보고하고, 미증명·차단·0건을 숨기지 않습니다.

첫 응답에서 반드시 안내할 것:
1. 현재 브랜치와 HEAD
2. QSP7 범위 파일의 clean/dirty 상태
3. 검증 3종 결과(집중 테스트·verifier·JSX)
4. G-0a 착수 계획과 완료 게이트
5. 예상 시간
```

---

## 8. 🚧 사용자 결정 대기

| # | 항목 | 상태 |
|---:|---|---|
| 1 | **origin push / PR** | 로컬이 origin 대비 122+ 커밋 앞섬. push 시도가 권한 정책에 차단됨 — 사용자가 직접 `git push -u origin loop/process-research-pipeline` 실행하거나 권한 허용 필요 |
| 2 | **R2 채택 승인** | `QSP7_min_필터_등락율각도_20260803_090bc7` — gate `adoptable`, 운영 반영 여부는 사용자 결정 |
| 3 | min 2세대 | tick G-0 완료 후 동일 엔진으로 진행 |
| 4 | GitKraken | 개발 중 종료 권장(세션 중 lock 충돌 6회) |
