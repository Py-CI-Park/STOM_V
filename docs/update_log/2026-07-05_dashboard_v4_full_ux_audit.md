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

## 5. 남은 마이너 개선(후속, 우선순위 낮음)

1. **비-Live 탭의 run 제어 컨텍스트** — 진행도/설정·시작/정지가 Backtest/Replay/Lab 등에도 노출.
   RUN 셀렉터는 데이터 스코프라 유지하되, 진행도/설정·시작은 Live 에서만 강조하는 방안 검토.
2. **Workbench HoF 테이블 길이** — 상단 요약 카드 + 접이식/가상 스크롤 검토.
3. **관찰성 라이브 데이터** — Research 거버넌스(Branch Tree 등)는 라이브 연구 중에만 채워짐
   (아카이브는 대기). wt-dev 백엔드 emit 은 채택 완료 상태 → 이 브랜치에서 실연구 시 채워짐(E 시나리오).

## 6. 결론

조건식을 **어떻게** 찾고(생성→백테→채점→부검→개선), **왜** 통과/기각되는지(게이트·부검·PROMOTE
체크리스트·결정 원장), 그리고 **AI가 무엇을 봤는지**(Context pack)까지 화면으로 추적 가능하다.
사용성 결함 2건 수정 후 대시보드는 "체계적으로 조건식 찾는 프로세스를 이해·확인" 목적에 부합한다.
