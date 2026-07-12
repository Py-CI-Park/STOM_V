# 2026-07-05 V4 대시보드 전수 UX/UI 감사 (8뷰 × 실데이터 판독)

> 방법: wt-dev 실데이터(8791) + winner run `human_fullperiod_seed_replay_20260628` 선택 상태로
> 8뷰 전부 캡처 후 **직접 판독**. 증거: `.omo/evidence/dashboard-v4-audit-20260705/`(before) +
> `/after/`(수정 후). 감사 축: ① 조작 편의(사용성) ② 정보·인사이트 ③ 조건식 찾는 프로세스
> 이해·확인 ④ 시각 통일성·중복.

## 1. 종합 판정

**대시보드는 사용자의 목적(조건식 찾는 프로세스를 이해·확인하고 인사이트를 얻는 것)에 부합하게
개발돼 있다.** 프로세스 가시성·정보 밀도·검증 체계가 강점이고, 이번 감사에서 발견한 **사용성 결함
2건(RUN 셀렉터·Lab 위키 에러)을 즉시 수정**했다. **종합 ~90/100.**

## 2. 뷰별 감사 (실데이터 판독)

| 뷰 | 점수 | 강점(확인) | 이슈 |
|---|---:|---|---|
| **Research Live** | 92 | workflow strip(생성→백테→채점→부검) + process-research 권한 · **V4HeroChart** g0~g3 fitness 곡선(gate선·best/현재 마커) · **BEST=WINNER 1.804 + ✓게이트 + 매수/매도명 + 연구 산출물 승인·Export**(human gate 명확) · 스탯행 · 접이식 분석(세대표·백테상세·GenAnalytics·부검/계보/홀드아웃·설정/비용) · 관찰성 rail | 조건식 발굴 거버넌스(Research Pack/Branch Tree)는 **라이브 전용** → 아카이브 run 은 "대기" 표기(설계상 정상, 메시지 有) |
| **Backtest** | 90 | 모드(백테/최적화/WFO/스킵)·매수매도 조건식·기간·엔진수·실행 · 조건식 편집(매수/매도 에디터)·결과 분석 · connected | 상단 run 제어(진행도/설정·시작)가 backtest 와 무관(마이너 컨텍스트 부정합) |
| **Replay** | 90 | 빠른시작(최근거래일/최대상승일)·재생 속도(1x~초고속)·시간단위/날짜/조건식/종목/시장미니맵 · **keep-alive 실증(탭 이탈·복귀 재생 지속)** | — |
| **History** | 88 | RESEARCH RECORDS 17캠페인(후보·Best PnL·MDD·Artifacts)·SELECTED+TOP CANDIDATES·Run Compare·과거 재열람·Evidence Owner Matrix·Governed Research Index(필터/타임라인) | Governed Index 는 이 데이터서버에서 빈 상태(데이터 의존, 안내 메시지 有) |
| **Lab** | 88 | 대형 Edge Ratio 히트맵(시간대×시총·글로벌 지표·등락률 구간)·탐색/변수중요도/상관/조합/검증 서브탭 | ~~위키 타임아웃 에러 상시 노출~~ → **수정: 접이식 처리** |
| **Workbench** | 84 | HoF 프로 테이블(수백 행 점수·수익·MDD)·RunCompare·계약 게이트 | 테이블이 매우 길다(스캔성 저하) — cap(150) 은 있으나 긴 스크롤(후속) |
| **Audit** | 92 | **정보 밀도 최고**: Evidence Owner Matrix · PROMOTE 체크리스트(상태·근거) · 레짐·부활 · V6 포트폴리오 · **append-only 결정 원장(promote/complement/hold/reject + 기록)** | — |
| **Context** | 85 | AI State Context(run/gen/전략명/graded/verdict/forbidden)·context_pack 4섹션·copy AI state — 프로세스 투명성 | 실 pack 로드는 라이브/run 의존 |

## 3. 감사 축별 점수

| 축 | 점수 | 근거 |
|---|---:|---|
| 조작 편의(사용성) | 90 | RUN 셀렉터 강조 수정으로 아카이브 조회 접근성 개선. 레일·딥링크·keep-alive·온보딩 |
| 정보·인사이트 | 92 | Audit(체크리스트·원장)·Lab(edge 히트맵)·Context(pack)·History(캠페인/후보) |
| 프로세스 이해·확인 | 90 | workflow strip → BEST=WINNER 게이트 → Audit PROMOTE 체크리스트로 "생성→검증→승인" 흐름이 화면으로 읽힘 |
| 시각 통일성·중복 | 90 | 토큰·칩·패널·레일 일관 · Home 중복 제거·History 단독 소유·Vdt 중복 회피 |

## 4. 이번 감사에서 수정한 사용성 결함 2건

| 결함 | 원인 | 수정 |
|---|---|---|
| **RUN 셀렉터가 작고 잘리고 묻힘**(사용자 신고) | 폭 190px·11px·우측 끝 크램프 | `연구 RUN` 라벨 + `.v4-runsel-select` min-width 220·13px(full 이름) + **아카이브 시 앰버 강조(is-archive) + 상태 칩(아카이브/LIVE) + ✓게이트 프리픽스** — 재캡처로 확인(`after/research_runsel.png`) |
| **Lab RESEARCH WIKI 빨간 에러 상시 노출** | 감사 커버리지 보강 때 위키를 상시 패널로 추가 → 느린 fetch 타임아웃(TimeoutError)이 항상 표시 | V2 처럼 **접이식(`<details>` 기본 접힘)** 처리 — 재캡처로 에러 미노출 확인(`after/lab_wiki_collapsed.png`) |

검증: 빌드 0에러(app.js `f72a8d20`), jsdom 하네스 V1~V7 allPass, 8791 실데이터 461 run 로드.

## 5. 마이너 개선 3건 — 처리 완료(2026-07-05 후속)

증거: `.omo/evidence/dashboard-v4-audit-20260705/followup/`. 빌드 `app.js=b808f9f9` ·
하네스 V1~V7 allPass · pytest 25 passed · 브랜치 게이트 exit 0.

1. **비-Live 탭의 run 제어 컨텍스트 정리 — 완료.** `V4RunControls` 를 탭 컨텍스트 인지형으로
   재작성(`isLive` prop). Live 탭: 풀 컨트롤(진행도·RUN 셀렉터·정지·설정·시작). 비-Live 탭:
   RUN 셀렉터(데이터 스코프)만 유지, **진행도/설정·시작 숨김**. 연구 진행 중이면 앰버
   "⚡ 연구 진행 N/M · Live ↗" 링크(클릭 시 Live 이동) + 안전 정지만 노출 → 어디서든 상태
   인지·중단 가능. 스크린샷 판독: `followup/backtest_dark.png`(링크·정지 노출·진행도/시작 숨김),
   `followup/research_dark.png`(Live 풀 컨트롤).
2. **Workbench HoF 테이블 길이 — 완료.** 감사 지적 대상은 ResearchProPanel 의 "명예의 전당 프로"
   테이블(수백 행). 공유 컴포넌트 JS 는 무수정하고, **v4.css 워크벤치 스코프에서 `:has(> table.rp-table)`
   + `.hof-scroll` 로 각 테이블 스크롤 래퍼를 max-height 560px 경계 처리 + thead sticky**. DOM 실측:
   프로 HoF `clientHeight 558 / scrollHeight 1197`, 성과 HoF `558 / 1473` → 영역 내 스크롤 확정.
   긴 테이블이 더 이상 페이지를 통째로 밀지 않아 뒤 계약 게이트가 위로 올라온다.
3. **라이브 관찰성 데이터 — 실측으로 원인·경로 확정(유료 실행 불요).** wt-dev 백엔드가 라이브
   연구 중(chunk06, gen 12→16/24)임을 확인하고, V4 코어(workflow strip·hero fitness·현재세대·
   Best/Winner 게이트)가 **라이브로 정상 관찰**됨을 판독(`followup/research_dark.png`). 승인 게이트
   E2E 는 아카이브 run 에서 실증(BEST=WINNER·승인/Export), 라이브 run 은 "게이트 통과 대기" 정상.
   단, **거버넌스 패널(Branch Tree/Research Pack/Candidate Pack/Promotion Blockers)의 라이브
   데이터는 읽기 전용 미러(8791)로는 안 뜬다** — `page_data.condition_discovery.research_observability`
   는 wt-dev 루프가 **발행 시점에 프로세스 내부에서 만드는 라이브 투영**(`controller/loop.py:1039-1091`)
   이라, 디스크 상태만 읽는 별도 미러 서버에는 실리지 않는다(검증: `/status` + 라이브 WS 프레임 4개
   모두 page_data 빈 상태). 패널은 에러 없이 "실시간 데이터 대기" 폴백. **해소 경로: V4 가 루프
   자체 프로세스에서 same-origin 으로 서빙되면 자동 표시**(= wt-dev 레인 채택 시). 미러로는 안
   보이므로 신규 유료 실연구는 불요.

## 5.5 History 탭 정리 2건 (2026-07-05 후속 — 사용자 질문 기인)

사용자가 History 탭의 "EVIDENCE WORKSPACE · OWNER MATRIX / PHASE 2 INVENTORY GATE"와
빈 "Governed Research Index"가 왜 필요한지·중복인지 물음. 실측 결과 2건 처리.

1. **OWNER MATRIX / PHASE 2 INVENTORY GATE 헤더 숨김(V4 스코프).** 이 헤더는 Phase-9 SPA
   통합 시 **중복 방지용 개발 스캐폴딩**(`dashboard-inventory.jsx` 주석: "pre-edit inventory
   gate")이지 사용자 기능이 아니다. V4 좌측 레일이 페이지 역할을 대신하므로
   `.v4-root .evidence-workspace-head { display:none }` 으로 V4 에서만 숨김(V2 경로 무영향).
   "STOM 히스토리" 제목·RESEARCH RECORDS·Governed Index 본문은 유지. 판독: `followup/history_loading.png`.
2. **Governed Research Index 빈 상태 = 실은 느린 로딩(원인 확정·수정).** `/research_index` 는
   비어있지 않다 — HTTP 200 에 **2863 레코드(2.2MB)를 반환하지만 응답에 ~10.9s**(campaign/doc/
   update_log/registry 교차 집계). 프론트가 로딩 중에도 "No records" 빈-상태를 그려 "비었다"로
   오해됨. `research-index.jsx` 의 두 빈-상태를 `!loading` 으로 가드하고, `loading && records=0`
   에 "거버넌스 인덱스 로딩 중(대용량 · 최대 ~20초)" 블록 추가(공유 컴포넌트의 실제 UX 버그라
   V2 에도 안전한 개선). 브라우저 실측: t=6s 로딩 블록·"No records" 미표시 → ~18s 후 rows 2863 채워짐.

또한 **v4.css `?v=` 를 20260704a→20260705b 로 범프**(build-app.mjs 가 v4.css 는 버전 처리하지
않아, 이번 세션의 CSS 변경들이 사용자 브라우저 캐시에 안 잡히던 문제 해소 — 하드리프레시 불요).

## 5.6 전수 재감사 (2026-07-05 — 후속 수정 후 8뷰 재판독)

후속 수정(§5·§5.5) 반영 상태에서 8뷰를 실데이터(8791, 라이브 연구 chunk12 진행 중)로
재캡처·직접 판독. 증거: `.omo/evidence/dashboard-v4-audit-20260705/reaudit/`.
**회귀 0건 · 신규 결함 0건.** 코드 변경 없이 검증만 수행(마지막 커밋 `15ab109f` 기준).

| 뷰 | 점수 | 재판독 확인 | 수정 반영 |
|---|---:|---|---|
| Research Live | 92 | 풀 컨트롤·workflow strip·V4HeroChart·현재세대·Best/Winner 게이트·거버넌스 "대기" | #1 Live 풀 컨트롤 |
| Backtest | 90 | 모드·매수매도 에디터·검증/저장 | #1 진행도·설정·시작 숨김, 라이브 링크+RUN+정지 |
| Replay | 90 | 실데이터(213일 DB·실 종목 등락률·미니맵)·keep-alive | #1 |
| History | 90↑ | RESEARCH RECORDS(17캠페인) 맨 위·Compare/RESULTDETAIL | OWNER MATRIX·INVENTORY GATE 헤더 제거·Governed Index 로딩 정상 |
| Lab | 88 | Edge Ratio 히트맵(0.395·327건·승률26%)·6서브탭·해석 카드 | 위키 접이식(에러 없음) |
| Workbench | 86↑ | 히트맵·명예의전당 프로(실 후보) | #2 HoF 경계 스크롤(무한 확장 안 함) |
| Audit | 92 | 안전 strip·PROMOTE 체크리스트(게이트 판정·근거)·OOS 신뢰구간·결정 원장 | — |
| Context | 88↑ | AI State(run/gen/전략/verdict=REJECT/forbidden)·context_pack 4섹션 **라이브** | — |

**종합 ~90/100.** 핵심 확인: (1) #1 run 제어 정리는 **7개 비-Live 탭 전부 일관**(진행도·설정·시작
숨김 + 앰버 "⚡ 연구 진행 N/24 · Live↗" 링크 + RUN 셀렉터 + 안전 정지). (2) #2 HoF 경계
스크롤·헤더 숨김·위키 접이식·Governed Index 로딩 모두 해당 탭 반영. (3) 8탭 동일 topbar+controlbar
구조로 시각 통일·중복 렌더 없음. (4) 생성→백테→채점→부검(Live) → PROMOTE 체크리스트·결정
원장(Audit) → AI 컨텍스트(Context, verdict=REJECT_CANDIDATE·forbidden_actions 라이브)까지
프로세스가 화면으로 연결. 한계는 §5 #3과 동일(거버넌스 라이브 데이터는 미러 미표시 — Context
Pack 은 persisted state 라 라이브로 뜸, 대조 확인).

## 5.7 로드맵 Phase 1 자율 개발 (2026-07-05 — ralph 루프)

성숙도 로드맵(Artifact)의 순수 프론트 폴리시 3건을 ralph 지속 루프로 구현·검증. 정찰 결과
외부 차단 항목(B2 백엔드배선·B3 미러·C7 비용·A1 채택)은 근거와 함께 제외(prd.deferred).

| 스토리 | 구현 | 검증 |
|---|---|---|
| **C4** HeroChart 초기상태 | `v4-charts.jsx` `_v4DrawHero` 재구성 — 그리드+gate 프레임을 항상 그리고, 세대<2 는 '데이터 축적 중'(1세대는 앰버 마커+값) 상태 표시. 세대≥2 경로 무수정 | 픽스처 0/1/3세대 캡처 판독(roadmap/hero_*.png) — 프레임+gate+안내, 3세대 정상 곡선 |
| **C5** Governed Index 로딩 | `research-index.jsx` elapsed 상태+1초 틱 → 두 로딩 블록에 '(경과 Ns)'+'보통 ~11초' | 브라우저 t=5s '경과 4s'·No records 미표시 → 로드 후 rows 2863 |
| **C6** 라이트 테마 | 코드 무변경(이상 없음) | 8뷰 라이트 캡처(roadmap/light/*.png)·livelink 픽스처(라이트 --amber #b27200 대비 우수) — 결함 0 |

검증 체인: 빌드 0에러(app.js=4d530d29) · 하네스 V1~V7 allPass · **architect 리뷰 APPROVED**(AC 라인별
검증, 무회귀·타이머 누수 없음) · deslop 무편집 · 회귀 재검증 green. 증거:
`.omo/evidence/dashboard-v4-audit-20260705/roadmap/`.

남은 로드맵: B2·B3(백엔드/미러) · C7(비용 승인) · A1(채택) — 사용자 결정/승인 대기.

## 6. 결론

조건식을 **어떻게** 찾고(생성→백테→채점→부검→개선), **왜** 통과/기각되는지(게이트·부검·PROMOTE
체크리스트·결정 원장), 그리고 **AI가 무엇을 봤는지**(Context pack)까지 화면으로 추적 가능하다.
사용성 결함 2건 수정 후 대시보드는 "체계적으로 조건식 찾는 프로세스를 이해·확인" 목적에 부합한다.
