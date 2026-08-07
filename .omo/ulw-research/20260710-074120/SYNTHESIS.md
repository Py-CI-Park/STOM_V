---
title: "STOM AI 조건식 루프: 실패 원인, 개발 역사와 재설계 종합 감사"
subtitle: "2026년 7월 10일, 현재 checkout과 형제 브랜치 교차감사"
lang: ko-KR
toc: true
toc-depth: 3
number-sections: true
geometry: margin=24mm
header-includes:
  - |
    <style>
      :root { color-scheme: light; --ink:#172033; --muted:#5d6778; --line:#d8deea; --paper:#ffffff; --soft:#f4f7fb; --accent:#2457d6; --bad:#9b1c31; --warn:#8a5200; --good:#17633b; }
      html { background:#eef2f7; }
      body { max-width:1180px; margin:0 auto; padding:48px 56px 88px; color:var(--ink); background:var(--paper); font-family:"Pretendard","Noto Sans KR","Malgun Gothic",system-ui,sans-serif; line-height:1.72; }
      h1,h2,h3 { line-height:1.28; letter-spacing:-.025em; word-break:keep-all; overflow-wrap:normal; text-wrap:balance; }
      h1 { font-size:2.25rem; margin-bottom:.3rem; }
      h2 { margin-top:2.8rem; padding-top:.65rem; border-top:2px solid var(--ink); }
      h3 { margin-top:2rem; color:#263a64; }
      p,li { word-break:keep-all; overflow-wrap:anywhere; }
      blockquote { margin:1.2rem 0; padding:.8rem 1rem; border-left:4px solid var(--accent); background:var(--soft); color:#293650; }
      table { display:block; width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch; border-collapse:collapse; margin:1rem 0 1.5rem; font-size:.92rem; }
      th,td { padding:.65rem .72rem; border:1px solid var(--line); vertical-align:top; white-space:nowrap; word-break:keep-all; overflow-wrap:normal; }
      th { background:#edf2fa; text-align:left; }
      code { padding:.1rem .28rem; border-radius:4px; background:#eef1f5; font-family:"Cascadia Mono",Consolas,monospace; font-size:.9em; }
      pre code { display:block; padding:1rem; overflow-x:auto; }
      a { color:var(--accent); }
      .subtitle { color:var(--muted); }
      @media (max-width:760px) { body { padding:28px 20px 60px; } h1 { font-size:1.75rem; } table { font-size:.84rem; } }
      @media print { html { background:white; } body { max-width:none; padding:0; } a { color:inherit; } }
    </style>
---

# 결론부터

최신 v2 실험의 실패는 **“좋은 전략을 만들었지만 통과 기준이 너무 엄격해서”가 아니다.** 7개 정상 실행 조합 모두 손익이 음수였고, 거래당 수익률 중앙값·MFE/MAE가 함께 나빴다. 확정 가능한 실패 단위는 **음의 실현 기대값을 낸 진입과 청산의 결합체**다. 낮은 구조 다양성과 수치 임계값 계보 부재는 확인됐고, 일부 body는 과발화했다. 다만 같은 진입에 여러 청산을 적용한 실험이 없으므로 “진입 엣지 부재가 단독 주원인”이라고는 아직 말할 수 없다.

더 근본적으로는 최신 `lattice v2`가 원래 목표였던 자율 AI loop의 산출물이 아니다. 이는 32개 메타 후보를 사람이 정한 축과 템플릿으로 8개 정적 본문으로 줄여 일괄 실행한 **별도 batch 연구 경로**였다. 구현돼 있던 분석 카드, context pack, 원칙 gate, 가설·반사실·quantile feedback, holdout 같은 학습 장치 대부분은 이 실행에서 꺼져 있었거나 다른 실행 경로에만 연결돼 있었다. 따라서 이 결과는 “AI가 반복 학습했는데도 실패”라기보다 **학습 루프를 우회한 얕은 정적 탐색이 실패**한 것으로 해석해야 한다.

명예의 전당(HOF)의 인간 19개와의 격차도 두 층으로 나눠야 한다.

1. **화면·DB 기록상 큰 지표 격차가 있다.** 장기 `AILOOP` 기록은 연환산 약 18~40%, MDD 약 12~20% 수준인 반면, 화면의 인간 참조군은 연환산 134~262%, MDD 1.9~6.75%, 일평균 10.6~23.2회다. 하지만 동일 실험 protocol이 아니므로 이를 곧바로 인간 개발 시스템과 AI 개발 시스템의 실제 알파 격차로 일반화할 수 없다.
2. **현재 대시보드는 공정한 대회가 아니다.** 인간 쪽은 선별된 우승작 19개이고 실패한 시도 수·코드·검증 이력이 없으며, AI 쪽은 서로 다른 기간·자본·프로파일의 반복 실험을 섞는다. 이름 접두사로 출처를 판정해 생성·변형 전략 다수를 `seed`로 잘못 표시한다. 이 화면은 영감을 주는 참조판이지 인간 대 AI의 과학적 성능 판정기가 아니다.

따라서 다음 행동은 조건식을 더 많이 찍는 것이 아니다. 현재 checkout 핸드오프가 정한 대로 v2를 폐기하고, 저장소 전체의 48초 늦은 형제 브랜치 핸드오프가 남긴 alpha-lab 부정 증거도 함께 보존해야 한다. 이후 **하나의 실행 원장, 증거 기반 수치 생성, typed STOM AST, 행동 기반 품질-다양성 탐색, 진입/청산 분리 실험, 봉인된 검증과 공정 HOF**를 설계해야 한다.

## 판정 요약

| 질문 | 판정 | 근거 수준 |
|---|---|---|
| 최신 v2는 왜 실패했나? | 진입과 청산이 결합된 음수 실현 기대값과 낮은 탐색 다양성. 일부 과발화 | 결합 실패 확인, 개별 인과 미분리 |
| gate가 너무 엄격했나? | 아니다. gate 이전에 7/7 손익 음수 | 배제됨 |
| 몇 개의 큰 손실 때문인가? | 아니다. 중앙값도 음수이고 손실이 넓게 분산 | 배제됨 |
| 조건식은 데이터 기반인가? | 계열·서사 선택은 데이터 informed, 숫자는 data-derived 증거 부족 | 확인됨 |
| 조건식은 창의적인가? | 문법상 다르지만 행동·구조 다양성은 낮음 | 확인됨 |
| 청산만 고치면 되는가? | 아직 모른다. 공통 청산이 악화시켰지만 진입 자체도 불리해 보임 | 분리 실험 필요 |
| AI loop 전체가 실패했나? | 아니다. 최신 v2는 자율 loop가 아닌 batch 경로 | 확인됨 |
| 인간 HOF를 못 이긴 이유는? | 표시 지표 격차 + 불공정/비재현 benchmark가 동시에 존재 | 지표 확인, 시스템 알파 격차 미확정 |

# 1. 감사 범위와 증거 원칙

## 1.1 확인한 핵심 자료

- 현재 checkout에서 도달 가능한 최신 핸드오프: `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md` (`564879fe`, 22:05:41)
- 저장소 전체 시각상 최신 형제 브랜치 핸드오프: commit `585051e`, `docs/research/condition_research/plans/2026-07-09_alpha_lab_ai_agent_handoff_initial_five_docs.md` (22:06:29)
- v2 종결 판정: `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md`
- v3 설계 전용 계획: `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md`
- 원래 북극성·과거 구현: `docs/AGENT_HANDOFF.md`, 2026-07-02/03 구현 핸드오프
- 576 lattice·Plan D 분석: `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`
- v2 조건식·axis spec·원시 결과 JSON/CSV
- `controller.loop`, `brain.generator`, `controller.ga`, `condition_discovery`, `cli.research_loop`, `autopsy.analyze`, dashboard HOF 및 export 경로
- `utility/ai_agent/strategy.txt`, `utility/ai_agent/rules.txt`의 STOM 변수·생성 규칙
- 최종 HOF 재현 receipt는 SQLite URI `mode=ro`로 직접 조회했다. 전략 추가·export·백테스트·명시적 DB write는 수행하지 않았다.

## 1.2 주장 등급

- **확인**: 코드·JSON·CSV·DB 행으로 직접 재현된 사실.
- **강한 추론**: 여러 독립 증거가 같은 방향이지만 인과 분리 실험은 없는 결론.
- **미해결**: 현재 자료만으로 진입/청산 또는 모델/시장 원인을 분리할 수 없는 주장.

## 1.3 중요한 제한

- 7개 조건식의 결과를 합산한 90,737건은 서로 독립된 전략 실행의 거래 수 합계다. 하나의 포트폴리오 거래로 해석하면 안 된다.
- HOF 인간 19개는 원코드·실패 이력·동일 엔진 재실행 증거가 없다. 화면 수치의 재현성을 확인하지 못했다.
- alpha-lab과 v2를 합치면 2025-01~2026-02가 이미 알려진 감사 증거다. 앞으로 이 구간을 “완전 미사용 blind OOS”라고 부를 수 없다.
- MFE/MAE는 진입이 불리하다는 강한 신호지만, 고정 진입-다중 청산 ablation 전에는 청산의 인과 기여를 숫자로 확정할 수 없다.
- 초기 감사에서 dashboard HOF projection을 한 번 직접 호출할 때 기본 `LoopState`가 열렸다. export나 명시적 write는 호출하지 않았지만, 사전 byte hash가 없어 import/schema-open이 보호 DB의 mtime·WAL·schema에 아무 영향도 주지 않았다고 단정하지 않는다. 이 위험을 확인한 뒤 모든 DB 재검증은 direct `mode=ro`로만 수행했다.

# 2. 두 최신 핸드오프의 정확한&nbsp;의미

## 2.1 현재 checkout에서 도달 가능한 최신 핸드오프

현재 브랜치 `loop/process-research-pipeline`의 2026-07-09 핸드오프 상태는 다음과 같다.

- `lattice v2 body` 분기는 **종결**됐다.
- 결과 판정은 8개 중 7개 정상, 1개 오류, 생존 0, `no_go` 8이다.
- Plan D로 이어 가지 않는다.
- 다음 허용 작업은 **v3 design-only** 문서 설계뿐이다.
- DB insert, replay/OOS, 새 body 실행, portfolio, export는 금지돼 있다.

이 제한은 형식적 보류가 아니다. v2의 구조를 조금씩 변형해도 얻을 정보가 적다는 실험 경제성 판단이다. 7개 정상 조합은 모두 대폭 손실했고, 일부는 과발화했으며, repair를 계속하면 이미 본 결과에 맞춘 사후 최적화만 늘어난다.

## 2.2 저장소 전체에서 48초 늦은 형제 브랜치 핸드오프

`git log --all` 기준으로는 형제 브랜치 `research/alpha-lab-idea5-foundation-20260707`의 commit `585051e`가 22:06:29에 작성돼 48초 더 늦다. 두 commit은 merge-base `f5ddc248` 이후 갈라진 sibling이므로 어느 한쪽이 다른 쪽을 대체하지 않는다. 따라서 “가장 최근”은 다음처럼 구분해야 한다.

| 범위 | commit | 핵심 결론 |
|---|---|---|
| 현재 checkout reachable 최신 | `564879fe` | lattice v2 폐기, v3 design-only만 허용 |
| 저장소 전체 timestamp 최신 | `585051e` | alpha-lab 5아이디어 실패·재사용 자산을 docs-only로 동결 |

형제 핸드오프의 추가 결론은 다음과 같다.

- data-first 단독 매수식 채굴 v1/v2/v3는 종결됐고 v3 양의 EV 채택은 `0/107`이었다.
- 이벤트 연구 42,363건·138 cells에서 FDR survivor는 0이었다.
- 미시구조 layer는 346 samples로 봉인 최소 2,000에 미달해 성공/실패 모두 미확정이다.
- `hard_stop -5 + time_stop 300` 전역 청산 교체는 engine 확인에서 기각됐다.
- adaptive timing/regime rotation은 실패했고, 남은 자산은 `RR8_12`, `RR8_0`, `RR8_21`, `GPTAUTH_G8`의 고정 1/4 정적 등가중이다. 알려진 감사창에서 profit 약 2,608,362원, MDD 약 493,591원, Calmar 약 5.28이지만 단일 신규 조건식도 live-ready 증거도 아니다.
- 2025-01~2026-02는 이미 exposed/known evidence다.

두 핸드오프는 안전 결론에서 일치한다. 둘 다 문서·설계 전용이며 source/DB/engine/backtest/strategy registration/export/live 실행을 승인하지 않는다. 이 checkout의 V3K gate도 3/6이며 Gate 4가 환경 증거 부재로 막혀 있으므로, 형제 브랜치의 “감독형 후보” 표현은 현재 checkout의 배포 권한이 아니다.

# 3. AI loop를 처음 만든&nbsp;목적

원래 목표는 단순한 “LLM 전략 생성기”가 아니었다.

> LLM이 STOM 매수·매도 조건식을 제안하고, 공식 STOM 백테스트가 평가하고, 거래 autopsy가 실패 이유를 설명하고, 다음 세대가 그 증거를 소비하여 스스로 개선하는 닫힌 반복계.

비교 북극성은 인간이 만든 `Tick_B/S_902_905_Update_2`와 HOF 화면의 19개 전략이었다. 목표 지표는 대략 일평균 10~23회, 보유 6~12개, MDD 1.9~6.75%, 인간 참조군 이상의 성과였다. 다만 이는 최종 북극성이지 초기 hard gate로 그대로 쓰면 안 된다. 엣지가 없는 상태에서 거래 횟수부터 올리면 최신 v2처럼 손실 속도만 빨라진다.

AI loop가 해결하려 했던 문제는 네 가지였다.

1. 사람이 만든 복잡한 시장 가설을 STOM 문법으로 안전하게 표현한다.
2. 공식 엔진으로 동일 조건에서 반복 평가한다.
3. 단순 총수익이 아니라 구간·비용·MDD·거래 행동으로 실패를 해부한다.
4. 실패 지식을 다음 제안에 실제로 반영하고, 검증된 승자만 승격한다.

# 4. 개발 과정 히스토리

## 4.1 기반 구축기

초기 T0~T4 단계에서 공식 backtest 연결, 전략 passport, 결과 정규화, dashboard, warm refinement와 기본 gate가 마련됐다. 이 시점의 솔직한 한계는 “전 기능 ON + 다년 full-universe + 고정 OOS” 검증이 끝나지 않았다는 것이었다. 기능은 default-OFF였다.

## 4.2 2026-07-02~03: 분석 인프라&nbsp;확대

- replay freeze 및 slippage 검증
- 576 seed lattice
- trade ledger, ablation, Analysis Card
- axis ledger, LLM candidate/context pack
- principle 문서와 여러 feedback 옵션
- segment/holdout/quantile/counterfactual/feature importance 기능

그러나 구현 핸드오프가 이미 지적했듯 병목은 validator가 아니라 **분석 결과가 다음 후보 생성으로 실제 연결되는 구간**이었다. cold LLM 88회 이상에서 OOS 유망 후보가 0이었고, 성공에 가까웠던 것은 인간 seed 기반의 zero-LLM hill climb뿐이었으며 3-tick slippage에서 무너졌다.

## 4.3 평행 연구선: alpha-lab v1~v5

형제 브랜치의 alpha-lab은 생성기를 더 돌리는 대신 offline data-first discovery를 시도했다. v1~v3 단독 매수 규칙 채굴, 이벤트 연구, 미시구조 layer, 전역 청산 교체, adaptive regime이 차례로 실패하거나 미확정이 됐다. 남은 best-known 내부 자산은 4개 기존 챔피언의 원문을 고정 1/4로 묶은 정적 등가중이다. 이는 새로운 조건식 생성 성공이 아니라 **복잡한 적응보다 단순 다각화가 낫다는 제한된 감사 결과**다.

이 평행 연구선은 `docs/AGENT_HANDOFF.md`의 오래된 “adaptive timing이 가장 배포 가능” 서술을 후속 증거가 supersede했음을 보여 준다. 원래 핸드오프는 개발 당시의 역사 자료로 읽고, 현재 판정은 alpha-lab v4의 adaptive/regime 실패와 static equal-weight 생존을 우선해야 한다.

## 4.4 2026-07-08: lattice와 Plan D

- tick/min 각 288개, 총 576개를 평가했다.
- 576개 중 최종 교집합 생존자는 0이었다.
- repair composite는 16개 선택, 15개 실행 가능 수준까지 좁혔다.
- Plan D의 `R2-05`는 일부 긍정 결과를 냈지만, 선택에 사용한 기간이 “OOS-style” 평가에도 포함돼 진정한 blind 검증이 아니었다.

## 4.5 2026-07-08~09: v2 정적 본문&nbsp;분기

32개 metadata 후보를 8개 STOM 본문으로 수동 축약하고 batch로 실행했다. 이 commit은 문서·artifact 중심이며 재사용 가능한 수치 fitting generator를 추가하지 않았다. 7개가 정상 실행됐지만 전부 손실이라 분기를 닫고 v3 설계만 남겼다.

## 4.6 지금의 상태

현재 state는 `provider=batch`, run은 `lat_lattice_v2_body8_min_warm64_20260708`, 상태는 idle이다. 즉 dashboard 서비스와 데이터 기록은 존재하지만, 최신 결과를 만든 주체는 `controller.loop`의 자율 세대 반복이 아니다.

# 5. 지금 실제로 존재하는 세 가지 프로세스

```text
경로 A — 자율 controller loop
provider → 전략 생성 → 정적/DB gate → 공식 backtest → 평가/저장 → 다음 세대

경로 B — CLI research loop
분석 → Analysis Card/context pack/candidate pack → LLM 또는 deterministic 후보 → 연구 실행

경로 C — lattice/batch artifact
axis spec·수동 선별 → 정적 STOM body → 제한 batch backtest → closeout 문서
```

문제는 세 경로가 같은 학습 원장과 후보 계약을 공유하지 않는다는 점이다.

- 경로 A는 많은 고급 flag를 전달하지만 `principle_gate_enabled`는 generator에 끝까지 연결되지 않는다.
- 경로 B는 context/candidate pack의 실제 소비 경로가 있지만 controller와 별도다.
- 경로 C는 최신 v2를 만들었지만 autopsy와 학습 feedback이 모두 꺼진 정적 batch다.
- promotion-review 설정도 provider 호출 전 0세대 hard stop으로 강제되지 않은 실행 흔적이 있다.
- GA 경로는 단순 elite/등급 선택과 LLM crossover/mutation이며, richer feedback 인자를 대부분 우회하고 다년 winner 선정도 미연결이다.

따라서 “기능이 구현돼 있다”와 “이번 실험에서 그 기능이 학습에 작동했다”를 구분해야 한다. 현재는 전자가 많고 후자가 적다.

# 6. 최신 v2 조건식은 어떻게 생성됐나

## 6.1 생성 규칙

axis spec은 다음과 같은 범주 축을 정했다.

- 시간대 regime
- coverage/risk class
- component pool
- sell profile
- lineage/repair 계보

후보 설명은 과거 failure map과 lineage를 인용했다. 이 수준에서는 데이터에 근거한 문제 선택이다. 하지만 `분당거래대금평균(30) × 0.70` 같은 정확한 수치가 어느 train window, 표본 수, 분위수, 효과 크기, 신뢰구간에서 나왔는지 기록하는 field가 없다. 해당 상수들은 정적 artifact commit에서 처음 나타나며, 이를 추정한 fitting code는 찾지 못했다.

따라서 판정은 다음과 같다.

- **계열·가설 선택**: data-informed
- **숫자 임계값**: reproducible data-derived라고 부를 증거 부족
- **최종 본문 선택**: 사람이 정한 제한 탐색과 정적 템플릿의 영향이 큼

## 6.2 조건식 구조

8개 매수식은 모두 대체로 다음 형태다.

```python
매수 = True
if not 관심종목:
    매수 = False
elif not 시간조건:
    매수 = False
elif not 등락률조건:
    매수 = False
elif not 거래대금·체결강도·이동평균조건:
    매수 = False
```

사용 변수의 합집합은 관심종목, 시간, 등락률, 당일/분당 거래대금, 분당 평균 대비 거래대금, 체결강도, 현재가와 고가·저가·이동평균 관계 등에 집중됐다. `strategy.txt`가 제공하는 L1~L5 호가·잔량, 총매수/매도잔량, VI, 시가총액, 세밀한 체결 흐름과 복합 regime 조건의 상당수는 쓰이지 않았다.

청산은 더 단순하다.

- 상한가/특수 상태
- 고정 손절
- 고정 익절
- 보유 시간
- 장 후반 정리

수치만 조금 다를 뿐 논리 skeleton은 사실상 하나다. 8개 중 5개는 매도 본문 hash까지 완전히 같다.

## 6.3 다양성 정량 결과

| 항목 | v2 | 인간 gold seed 참고 |
|---|---:|---:|
| 매수 exact unique | 8/8 | 1개 기준 |
| 숫자 정규화 매수 skeleton | 6 | 복합 분기 1개 |
| 매도 skeleton | 1 | 동적 MFE/trailing·regime 분기 |
| 평균 매수 줄 수 | 18.25 | 128 |
| 평균 매수 `if` 수 | 8.12 | 44 |
| 평균 매수 boolean op | 0 | 7 |
| 평균 매수 unique name | 11.25 | 34 |
| 평균 매수 AST depth(모듈 root 포함) | 13.88 | 30 |
| 매도 줄 수 | 약 14 | 47 |

인간 gold seed가 길어서 좋은 것은 아니다. 중요한 차이는 **조건부 구조**다. 인간 seed는 시간·시총·VI·가격 위치·거래 흐름·거래대금·호가를 regime별로 다르게 결합하고, 청산도 MFE와 추세 상태를 이용한다. v2는 서로 다른 설명을 붙였지만 실행 행동은 비슷했다. body06과 body08의 매수 line Jaccard는 0.917이고 body08은 상단 가격 제한 하나가 추가된 정도다. AST 정규화 방식과 입력 hash는 `v2_structural_audit_receipt_20260710.md`에 고정했다.

## 6.4 창의성 판정

“문자열이 서로 다르다”를 창의성으로 보면 8개는 다르다. 그러나 탐색에서 필요한 창의성은 **다른 시장 상황에서 다른 신호를 내는 행동 다양성**이다.

그 기준에서 v2는 낮다.

- 동일한 부정 filter chain
- 좁은 변수군
- 1개 청산 skeleton
- near-clone 매수식
- semantic signature나 regime activation을 이용한 diversity gate 부재

즉 문장·이름의 다양성은 있었지만 가설 공간의 다양성은 부족했다.

# 7. 최신 실험의 원시 결과

## 7.1 전략별 결과

| body | 손익(원) | 보고 MDD | 거래 수 | 일평균 | 판정 |
|---:|---:|---:|---:|---:|---|
| 01 | -514,545,798 | 312.19 | 21,987 | 103.2 | no_go |
| 02 | -373,908,892 | 188.20 | 12,981 | 60.9 | no_go |
| 03 | -288,376,184 | 207.91 | 11,249 | 52.8 | no_go |
| 04 | -106,616,341 | 127.28 | 5,015 | 23.5 | no_go |
| 05 | -881,171,389 | 441.67 | 30,653 | 143.9 | no_go |
| 06 | -103,427,022 | 90.64 | 4,487 | 21.1 | no_go |
| 07 | 지표 없음 | 지표 없음 | 오류 | 오류 | tick-origin control을 min으로 실행 |
| 08 | -101,728,684 | 89.63 | 4,365 | 20.5 | no_go |

7개 정상 실행의 전략별 평균 손익은 약 -3.385억 원, 중앙값은 -2.884억 원이다. 보고 MDD 평균은 208.2, 중앙값은 188.2이며 cap 35 대비 약 2.56~12.62배다. 일평균은 평균 60.84회, 중앙값 52.8회다.

## 7.2 거래 단위 결과

| body | 손실 거래 비율 | 거래 수익률 평균 | 거래 수익률 중앙값 | MFE 중앙값 | MAE 중앙값 | `MFE > abs(MAE)` |
|---:|---:|---:|---:|---:|---:|---:|
| 01 | 63.9% | -0.470% | -0.68% | 0.71% | -1.59% | 36.87% |
| 02 | 70.8% | -0.578% | -0.56% | 0.31% | -1.14% | 29.13% |
| 03 | 66.1% | -0.514% | -1.07% | 0.90% | -1.99% | 37.44% |
| 04 | 68.1% | -0.428% | -0.48% | 0.28% | -1.02% | 30.67% |
| 05 | 66.6% | -0.577% | -0.78% | 0.62% | -1.66% | 34.60% |
| 06 | 65.9% | -0.463% | -0.58% | 0.54% | -1.34% | 34.19% |
| 08 | 66.2% | -0.468% | -0.57% | 0.51% | -1.31% | 33.65% |

전체 body에서 MFE 중앙값은 약 0.28~0.90%, MAE 중앙값은 약 -1.02~-1.99%였고, `MFE > |MAE|`인 거래는 29.1~37.4%뿐이었다. **손실 거래 중 손실액 기준 최악 1%**가 gross loss에서 차지하는 비중도 약 2.6~3.4%여서, 실패는 몇 건의 tail loss가 아니라 넓은 거래에 퍼져 있다. 전체 거래 수의 1%를 tail 건수 산정 기준으로 잡으면 약 3.74~4.53%다.

## 7.3 이 수치가 배제하는 가설

- **gate가 너무 엄격했다**: 배제. 7개 모두 gate 이전 총손익 음수다.
- **거래 빈도가 부족했다**: 배제. 일평균 20.5~143.9회다.
- **한두 번의 대형 손실 탓이다**: 배제. 중앙값 음수, 손실 분산.
- **보고서의 sell threshold parsing 오류 탓이다**: 배제. label 문제였고 실제 식·결과는 바뀌지 않는다.
- **백테스트 엔진 전체 오류다**: 강하게 약화. 같은 엔진·기간 계열에서 Plan D R2-05는 양수 결과가 있었다. 다만 fill realism의 한계는 별도다.

# 8. 성과를 못 낸 원인 — 우선순위별

## 8.1 Critical: 실험 정체성이 분리됐다

최신 v2는 autonomous loop가 아니라 batch artifact다. autopsy false, holdout false, 고급 feedback false였고 다음 세대가 결과를 소비하는 반복이 없었다. 따라서 “닫힌 학습 loop”를 평가하려던 목적과 실제 실행이 달랐다.

## 8.2 Critical: 결합 시스템의 음수 기대값

7개 정상 조합은 모두 거래 평균·중앙값과 총손익이 음수였다. body01/02/03/05는 일평균 52.8~143.9회로 뚜렷한 과발화였고, body04/06/08은 20.5~23.5회로 인간 목표 상단 부근이었다. 따라서 **과발화는 일부 손실을 증폭했지만 7개 전체 실패의 단독 원인은 아니다.** 현재 확인 가능한 원인은 각 진입과 공통 청산 또는 변형 청산이 결합된 시스템의 음수 실현 기대값이다.

## 8.3 Critical: 탐색 다양성 붕괴

숫자와 설명은 달라도 매수는 얕은 filter chain, 매도는 동일 skeleton이었다. 이런 집단은 8개를 평가해도 사실상 같은 가설을 여러 번 평가한다. exact hash dedup만으로는 이 문제를 잡지 못한다. 이는 **탐색&nbsp;정보량 감소라는 확인된 문제**이지만, 낮은 다양성 자체가 손익 부호를 만들었다는 toggle 인과 증거는 아니다.

## 8.4 High: 수치 임계값의 계보가&nbsp;없다

정확한 상수의 train window, 표본 수, 분위수, 효과 곡선, 불확실성, source hash가 없다. 결과가 나빠도 어느 수치를 어떻게 고쳐야 할지 학습할 수 없고, 결과가 좋아도 재현 가능한 발견인지 알 수 없다.

## 8.5 High: 구현된 지능이 기본 OFF 또는 경로 단절

segment feedback, holdout, principle gate, quantile/counterfactual feedback, feature importance, exit feedback, hypothesis 기능 대부분이 opt-in/default-OFF다. 최신 batch는 이를 쓰지 않았다. `principle_gate_enabled`는 generator 인자에는 있으나 controller 전달이 빠져 있다. “기능 수”가 “학습 폐루프의 작동률”을 가렸다.

## 8.6 High: 깨끗한 final blind 평가가 없다

Plan D의 선택 구간이 다시 OOS-style 평가에 쓰였다. 576개와 repair/v2도 같은 역사 구간을 반복 관찰했다. 이제 해당 구간의 양수 결과는 연구·검증 참고이지 최종 일반화 증거가 아니다.

## 8.7 High: 목표 함수와 인간 기준이 불일치한다

현재 기본 gate는 대략 MDD 35~40, 일평균 0.5 이상으로 인간 참조군의 MDD 1.9~6.75, 일평균 10~23과 멀다. 반대로 빈도만 인간 수준으로 밀어 올리면 최신 v2처럼 손실이 폭증한다. 순서는 `비용 후 양의 기대값 → 구간 안정성 → 노출/빈도 확대`여야 한다.

## 8.8 Medium-High: autopsy의 관측 공간이 좁고 선택 편향됐다

현재 trade result autopsy는 약 14개 `B_*` 진입 변수 중심이며, 실행된 거래만 본다. L1~L5 세부 호가, signed flow, VI, spread, full opportunity set이 빠진다. “왜 선택한 거래가 실패했나”는 일부 보지만 “선택하지 않은 기회와 비교해 무엇이 달랐나”는 보지 못한다.

## 8.9 Medium-High: 진입과 청산을 동시에 바꿨다

공통 고정 청산은 손실을 증폭했을 가능성이 높다. 그러나 MFE/MAE도 진입 직후 불리한 움직임을 시사한다. 현재 설계는 진입과 청산이 함께 변해 어느 쪽의 기여인지 분리할 수 없다.

## 8.10 Medium: 현재 GA는 품질-다양성 탐색이 아니다

상위 grade와 elite를 중심으로 crossover/mutation하고 최근 AST 중복을 막는 수준이다. 행동 archive, niche, regime별 elite, novelty, fold별 lexicase가 없다. 풍부한 controller feedback도 GA의 `_gen_one`이 대부분 전달하지 않는다.

## 8.11 High: 승격·export의 증거 결속이 약하다

최종 승인 API는 네 개 전략 이름이 비어 있지 않으면 production DB writer를 호출할 수 있다. 현재 winner의 run id, generation, artifact hash, holdout/slippage gate, 사용자 승인 증거와 이름을 불변으로 묶지 않는다. 이는 성과 문제와 별개로 운영상 중대한 위험이다.

# 9. 인간 HOF와 AI가 다른 이유

## 9.1 화면과 DB 기록에서 보이는 격차

| 지표 | 인간 19개 화면 | 장기 AILOOP 기록 예시 |
|---|---:|---:|
| 연환산 수익률 | 134.17~262.05%, 중앙 204.92% | 약 17.7~40.3% |
| MDD | 1.9~6.75%, 중앙 3.8% | 약 12.2~19.8% |
| 일평균 거래 | 10.6~23.2, 중앙 16.9 | 약 0.3~2.3 |
| 거래 수 | 2,618~5,786, 중앙 4,149 | 장기 AI는 더 희소 |

이는 **현재 저장된 기록의 지표 격차**다. 3년 `multiseed_train_20260611`의 대표 `AILOOP` 행은 연환산 21.43~40.27%, MDD 12.19~19.84%, 일평균 0.3~0.4회였고, 약 1년 full-period replay 행은 연환산 17.78%, MDD 15.14%, 일평균 2.3회였다. 높은 빈도와 낮은 MDD를 함께 달성하지 못한 기록은 분명하지만, 동일 trial budget·기간·비용·원코드 재실행이 아니므로 인간 대 AI 개발 시스템의 실제 품질 격차는 아직 미확정이다.

## 9.2 하지만 HOF가 공정하지 않은 이유

dashboard의 기본 반환 cap은 30이다. 별도 read-only uncapped 감사에서는 DB SHA-256 `935cd891...b51d` 시점에 HOF 조건을 만족한 1,578개 행이 있었고, 현재 이름 규칙상 `seed` 1,520개, `ai` 58개로 분류됐다. 실제 prefix는 `GATE` 889, `TMAP` 319, `LAT` 182, `AILOOP` 58 등이었다. `AILOOP`가 아니면 모두 seed라는 판정 때문에 generated/mutated 결과가 seed로 오표시된다. 필터·DB hash·장기 예시 run id는 `hof_audit_receipt_20260710.md`에 고정했다.

또한 다음이 통제되지 않는다.

- 인간은 선별 우승작 19개이며 전체 시도 분모가 없다. AI 측도 `gate_passed`·흑자 행만 남지만 서로 다른 연구 run과 중복 replay가 섞여 selection process가 다르다.
- 동일 날짜 범위·기간 길이·자본·보유 수·timeframe·slippage 여부가 아님
- 인간 쪽 전체 시도 수와 실패율이 없음
- artifact hash dedup이 없어 같은 전략의 반복 실행이 여러 행일 수 있음
- 0.25년 미만은 일부 경고하지만 missing period는 오히려 unreliable 표시가 빠질 수 있음
- 인간 #7은 표시 기간 약 2년과 `days=241`·연환산 계산이 일치하지 않는 이상 징후가 있음

따라서 현 HOF는 “우리가 어느 수준을 동경하는가”는 보여 주지만 “같은 예산의 인간 개발 프로세스와 AI 개발 프로세스 중 누가 더 우수한가”는 답하지 못한다.

## 9.3 공정한 비교 방법

비교 대상은 최종 champion 하나가 아니라 **개발 시스템 전체**여야 한다.

- human-only, automation-only, human+AI 세 arm
- 동일 데이터 freeze, 엔진, 비용, 자본, timeframe, 노출 제한
- 동일 wall-clock/백테스트 횟수/LLM·인간 시간 budget
- 모든 제출과 실패를 append-only trial ledger에 기록
- 여러 독립 episode로 반복
- 개발 D, validation V, sealed historical T, prospective paper F 분리
- exploratory/frozen/blind/paper/live/independent-reproduction evidence badge

여러 전략을 본 뒤 최고를 고르는 selection bias는 [White의 Reality Check](https://doi.org/10.1111/1468-0262.00152), [Hansen의 SPA](https://doi.org/10.1198/073500105000000063), [PBO](https://doi.org/10.21314/JCF.2016.322), [Deflated Sharpe Ratio](https://doi.org/10.3905/jpm.2014.40.5.094) 같은 보정과 전체 trial 원장이 필요하다.

# 10. 해결 아키텍처

## 10.1 1단계: 실행 정체성과 증거 원장을 하나로 만든다

`controller`, `cli research`, `lattice/batch`가 모두 같은 `CandidatePassport`와 `RunLedger`를 기록해야 한다.

필수 field:

- `run_id`, `candidate_id`, `parent_ids`, `authoring_mode`
- AST hash, source hash, semantic behavior hash
- 데이터 fingerprint, train/validation/final window
- threshold provenance: feature, estimator, quantile, sample count, effect, uncertainty
- engine/profile/capital/cost/slippage/holdings/timeframe
- 전체 trial 번호와 검색 budget
- analysis card/context pack/principle version hash
- gate 결과, rejection reason, approval/export evidence

lineage는 [W3C PROV-O](https://www.w3.org/TR/prov-o/)처럼 불변 entity/activity 관계로 남기면 서로 다른 실행 경로도 추적 가능하다.

## 10.2 2단계: runtime gate를 실제로 강제한다

- promotion-review는 provider를 부르기 전에 0세대로 종료한다.
- `principle_gate_enabled`를 controller → generator까지 연결하고 receipt를 남긴다.
- 고급 feedback은 “flag가 켜짐”이 아니라 실제 prompt/AST proposal이 해당 artifact를 소비했는지 hash로 증명한다.
- export는 임의 전략 이름 대신 `run_id + winner generation + artifact hash + frozen evidence bundle + explicit approval`을 요구한다.

## 10.3 3단계: 문자열 대신 typed STOM AST를 생성한다

노드 예:

- `BoolCondition`, `Price`, `Percent`, `Volume`, `Lookback`, `DecisionTime`
- `FeatureAvailableAt(t)`를 가진 causal/temporal type
- regime branch, entry trigger, risk guard, exit policy를 별도 subtree로 분리

LLM은 AST proposal·mutation을 맡고 deterministic compiler와 validator가 STOM code를 만든다. 이는 [Strongly Typed GP](https://doi.org/10.1162/evco.1995.3.2.199)와 [Grammatical Evolution](https://doi.org/10.1109/4235.942529)의 장점을 STOM 문법에 적용하는 방식이다.

## 10.4 4단계: 수치를 train data에서 생성한다

실행된 거래만 보지 말고 모든 eligible 시점의 **full opportunity grid**를 만든다.

각 임계값은 다음 절차로 생성한다.

1. 종목·동일 시각대 기준 rolling normalization
2. train window 안에서 robust quantile band 계산
3. forward return과 MFE/MAE response curve 추정
4. symbol-day group bootstrap으로 불확실성 계산
5. 최소 표본·효과·비용 후 기대값 gate
6. source hash와 함께 상수 provenance 저장

이렇게 해야 “0.70을 0.65로 바꿀까?”가 아니라 “0.70은 train의 65분위이며 표본 N, 비용 후 효과 E, CI가 이렇다”로 학습할 수 있다.

## 10.5 5단계: 행동 기반 quality-diversity 탐색

문자열·AST exact hash에 더해 causal probe set에서 다음 semantic signature를 만든다.

- entry signal bitset
- 시간대·시총·유동성·변동성 regime activation vector
- fold별 return vector
- turnover, median hold, exposure, complexity

3~5개 축의 sparse [MAP-Elites](https://arxiv.org/abs/1504.04909) archive를 유지하고 각 niche에 robust elite와 exploratory slot을 둔다. [Novelty Search](https://doi.org/10.1162/EVCO_a_00025)처럼 행동 차이를 보상하되, 수익을 버리는 순수 novelty가 되지 않도록 quality floor를 둔다. LLM+deterministic evaluator+program archive의 역할 분리는 [FunSearch](https://www.nature.com/articles/s41586-023-06924-6)와 유사하지만 금융에서는 chronology와 비용 gate가 추가돼야 한다.

## 10.6 6단계: 진입과 청산을 분리한다

1. 모든 entry 후보에 동일한 2~3개 고정 exit matrix를 적용한다.
2. 비용 후 entry event edge가 양수인 family만 남긴다.
3. entry를 freeze하고 exit만 최적화한다.
4. 마지막에 진입과 청산의 제한된 factorial을 실행한다.

이 순서면 “좋은 진입을 나쁜 청산이 망쳤는가”와 “진입 자체가 나쁜가”를 구분할 수 있다.

## 10.7 7단계: 검증을 D/V/T/F로 분리한다

- **D — discovery**: feature/threshold/구조 탐색
- **V — validation**: 소수 모델 비교와 calibration
- **T — sealed historical**: 한 번만 여는 최종 역사 검증
- **F — future prospective paper**: freeze 이후 새 데이터로 확인

현재 사용한 역사 구간은 T 자격을 잃었다. 기존 데이터를 walk-forward D/V로는 쓸 수 있지만 최종 주장은 새 untouched history 또는 prospective F가 필요하다. 반복 holdout 열람 문제는 [Reusable Holdout](https://doi.org/10.1126/science.aaa9375)류 원칙을 참고하되, 실제 운영에서는 접근 권한·횟수를 원장으로 강제해야 한다.

## 10.8 8단계: 목적 함수를 Pareto frontier로 바꾼다

단일 score 대신 다음을 동시에 본다.

- 비용 후 net return / trade expectancy
- MDD와 worst fold
- 일평균 거래·exposure·turnover·capacity
- regime별 안정성
- slippage 0~3 민감도
- 구조 복잡도와 semantic novelty

초기 승격 순서는 `양의 기대값 → worst-fold 안정성 → 비용/perturbation 강건성 → 빈도·capacity`다.

## 10.9 9단계: HOF를 evidence registry로 바꾼다

- 이름 prefix가 아니라 provenance field로 `human`, `AI`, `hybrid`, `seed-derived` 구분
- artifact hash + run profile dedup
- 기간·자본·timeframe·cost가 같은 cohort만 비교
- 탐색 trial 수와 selection budget 표시
- evidence badge와 기간 신뢰도 block
- 인간 참조가 재현 불가하면 `curated reference / non-reproducible`로 명시
- champion 한 개 외에 full frontier와 failed-trial denominator 표시

# 11. 데이터로 만들 수 있는 새 조건식 아이디어

아래는 즉시 backtest할 “정답 식”이 아니라, full opportunity grid에서 먼저 검증할 가설 family다.

## 11.1 동일 시각대 상대 거래 흐름 surprise

- 현재 종목의 동일 시각 rolling median 대비 분당 거래대금·체결강도 surprise
- 단순 절대 threshold가 아니라 time-of-day z/quantile
- 가격 상승과 공격적 매수 흐름이 함께 있을 때와 divergence일 때 분리

## 11.2 호가 불균형 + 체결 확인

- 1호가 및 L1~L5 가중 잔량 imbalance
- spread가 넓지 않고 실제 체결 흐름이 같은 방향일 때만 entry
- snapshot imbalance만으로는 queue position/취소를 알 수 없으므로 tick 진단·latency sensitivity 필수

## 11.3 유동성 흡수/flow-price response

- 강한 매수 체결에도 가격이 못 오르면 absorption/실패 신호
- 동일 flow에서 가격 반응이 평소보다 크면 thin-book breakout 후보
- 체결 흐름과 가격 변화의 조건부 반응을 사용

## 11.4 opening·VI regime event&nbsp;study

- 09:00~09:05, 이후 opening digestion, VI 전후를 별도 regime으로 둔다.
- gap·거래대금 surprise·호가 회복 속도의 조합을 학습한다.
- 한 개 글로벌 식이 아니라 regime별 subtree를 사용한다.

## 11.5 시총·유동성 조건부 모멘텀

- 같은 거래대금 배수라도 소형/대형 시총에서 의미가 다르다.
- cap bucket × time bucket × volatility bucket별 threshold를 train에서 추정한다.

Order Flow Imbalance의 이론적 배경은 [Cont, Kukanov, Stoikov](https://arxiv.org/abs/1011.6402)를 참고할 수 있다. 다만 현재 STOM snapshot 변수만으로 진짜 event-level OFI, queue position, passive fill, hidden liquidity를 측정했다고 주장해서는 안 된다. 현 백테스트 fill은 L1~L5 잔량을 훑지만 주문 latency·queue·cancel은 모델링하지 않는다.

# 12. 미승인 미래 설계안: V3-0 Evidence-First

아래는 원인 분석에서 도출한 **미승인 미래 아이디어**다. 현재 핸드오프가 허용하는 것은 순차적인 v3 design-only 문서 작성뿐이며, 이 보고서는 후보 본문·source 수정·DB·backtest·OOS·portfolio·export·live를 승인하지 않는다. v3 계획의 **A3 promotion-review hard-stop** 같은 코드 변경도 별도 사용자 승인 대상이다. V3K gate 4~6 권한과는 무관하다.

## 12.1 실험 예산

- 4개 hypothesis family
- family별 train quantile 3개: 총 12 entry
- 고정 exit 2개: 총 24 조합
- negative control 3종: 시간 이동, 방향 반전, 동일 빈도 matched random
- 총 trial budget과 중간 열람 횟수를 사전 등록

288개 격자를 다시 만들지 않는 이유는 새로운 정보 없이 multiple testing만 늘기 때문이다.

## 12.2 단계

1. alpha-lab과 v2가 본 2025-01~2026-02 전체를 exposed development 데이터로 명시한다.
2. 내부 chronological walk-forward D/V fold를 만든다. final blind라고 부르지 않는다.
3. full opportunity grid와 threshold provenance schema를 먼저 만든다.
4. 별도 승인된 미래 단계에서만 event study의 비용 후 양수 family를 AST 후보로 컴파일한다.
5. 별도 사전등록·승인 후에만 syntax/temporal/duplicate gate 통과 후보를 제한 official backtest로 보낸다.
6. entry 고정-exit matrix로 진입 edge를 확인한 뒤 exit 연구를 연다.
7. winner를 freeze하고 2026-03 이후의 미사용 신규 데이터 또는 실제 freeze 이후 prospective paper F에서 확인한다.

조건식 생성 입력은 당시 의사결정 시점에 사용 가능한 `B_*`로 제한하고 `S_*`, `R_*`, 결과·label 변수를 금지한다. `strategy.txt`는 문법 참고이며 runtime truth 자체가 아니므로 typed AST compiler는 실제 engine variable scope와 parity validator를 최종 기준으로 삼아야 한다. min은 primary discovery, tick은 diagnostic/stress lane으로 분리한다.

## 12.3 사전 stop rule

- chronological fold 중앙과 최악 fold가 모두 음수
- slippage 2단계에서 기대값 소멸
- 임계값 ±10% perturbation으로 부호 반전
- semantic duplicate rate 30% 초과
- control과 유의한 차이가 없음
- 최소 표본/유동성/capacity 기준 미달

하나라도 충족하면 family를 더 변형하지 않고 폐기한다.

# 13. 승인 후에만 적용할 구현 우선순위

이 절은 변경 요청이 아니라 설계 backlog다. 현재 checkout의 source나 runtime을 수정할 권한을 부여하지 않는다.

## P0 — 재실험 전에 반드시

1. v2 branch 종결 유지, v3 design-only 승인 문서
2. 공통 RunLedger/CandidatePassport schema
3. authoring mode와 artifact/data/engine hash
4. promotion hard stop 및 export evidence binding
5. HOF provenance 분류·dedup·cohort 비교 설계

## P1 — 첫 v3 연구 전에

1. typed AST + deterministic compiler
2. full opportunity grid
3. threshold provenance와 uncertainty
4. entry/exit factorial protocol
5. semantic signature와 sparse MAP-Elites archive

## P2 — 제한 연구 후

1. surrogate triage
2. lexicase/island evolution
3. prospective paper shadow
4. capacity/latency 민감도 확대
5. 인간-only/AI-only/hybrid 공정 benchmark episode

# 14. 성공 기준

“인간 HOF를 이겼다”는 한 번의 높은 수익률로 선언하면 안 된다. 최소한 다음을 함께 만족해야 한다.

- 완전한 trial denominator와 검색 budget 공개
- 같은 엔진·기간·자본·cost·노출 cohort
- walk-forward worst fold 양수 또는 사전 정의 허용 범위
- slippage·threshold perturbation·regime에서 안정
- final untouched/prospective evidence
- artifact hash로 재현 가능
- MDD·빈도·capacity를 포함한 Pareto 우위
- 독립 재실행 또는 frozen paper 검증

# 15. 최종 판단

현재 AI loop의 실패는 “AI가 인간처럼 창의적이지 않다”라는 한 문장으로 설명되지 않는다. 더 정확한 진단은 다음과 같다.

1. 원래 목표는 증거를 소비하는 자율 폐루프였지만 최신 실험은 그 루프를 우회했다.
2. 데이터는 가설 family를 선택하는 데 쓰였지만 정확한 threshold를 추정·기록하는 데 충분히 쓰이지 않았다.
3. 후보 수는 많았지만 행동 공간은 좁았고, 동일한 청산과 near-clone 진입이 반복됐다.
4. 4개 body의 과발화가 손실을 증폭했지만, 목표 상단 빈도의 3개도 실패했다. 현재 원인 단위는 진입과 청산이 결합된 음수 실현 기대값이다.
5. 이미 구현된 분석 기능은 대부분 OFF/분리돼 결과가 다음 세대를 바꾸지 못했다.
6. blind 검증과 trial ledger가 약해 양수 결과도 일반화 증거가 되기 어려웠다.
7. 평행 alpha-lab도 단독 규칙 채굴·전역 청산·adaptive regime의 실패를 확인했고, 남은 것은 고정 1/4 정적 앙상블뿐이다.
8. HOF는 목표 수준을 보여 주지만 공정·재현 가능한 인간 대 AI benchmark는 아니다.

좋은 소식은 실패가 정보가 없지는 않다는 점이다. v2는 “이 단순 filter-chain + 고정 청산 + 숫자 미계보 + 빈도 우선” 방향을 명확히 폐기할 근거를 줬다. 다음 세대는 더 큰 LLM이나 더 많은 후보보다 **실험 정체성, 관측 데이터, 구조적 탐색, 검증 거버넌스**를 먼저 고쳐야 한다.

# 부록 A. 주요 내부 근거 위치

- `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md`
- sibling commit `585051e`: `docs/research/condition_research/plans/2026-07-09_alpha_lab_ai_agent_handoff_initial_five_docs.md`
- `.omo/ulw-research/20260710-074120/hof_audit_receipt_20260710.md`
- `.omo/ulw-research/20260710-074120/v2_structural_audit_receipt_20260710.md`
- `docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md`
- `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md`
- `docs/AGENT_HANDOFF.md`
- `docs/update_log/2026-07-02_ai_loop_phase_implementation_record.md`
- `docs/update_log/2026-07-03_ai_loop_full_implementation_session_handoff.md`
- `docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md`
- `docs/research/condition_research/generated_conditions/lattice_v2_body_static_dryrun_20260708/`
- `docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/`
- `ai_strategy_loop/controller/loop.py`
- `ai_strategy_loop/controller/ga.py`
- `ai_strategy_loop/brain/generator.py`
- `ai_strategy_loop/brain/condition_discovery.py`
- `ai_strategy_loop/autopsy/analyze.py`
- `ai_strategy_loop/dashboard/app.py`
- `ai_strategy_loop/controller/export.py`
- `cli/research_loop.py`
- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

# 부록 B. 인과적으로 아직 남은 질문

- 동일 entry에 여러 exit를 적용했을 때 손실 중 청산 기여분은 얼마인가?
- full opportunity grid에서 v2 신호가 무신호·matched random보다 실제로 나쁜가?
- L1~L5와 체결 흐름을 포함하면 엣지가 개선되는가, 아니면 fill realism에서 사라지는가?
- 인간 gold seed의 우위는 구조, threshold, exposure, 데이터 구간 중 어디에서 오는가?
- 동일 trial budget의 human-only, AI-only, hybrid 중 어느 프로세스가 더 빠르게 frontier를 개선하는가?

이 질문들은 다음 설계가 답해야 하며, 현재 증거로 미리 결론 내리면 안 된다.
