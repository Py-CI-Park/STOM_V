# 2026-07-17 대시보드 V4 전수검사 — 왜 V4가 안 떴나, 유사 누락, 크롬 느림 원인

## 0. 요약 (한 줄)

"갑자기 V4가 안 뜬" 것은 **셸이 사라진 게 아니라, 최근 연구 대시보드 개선이 V4 그래프
셸이 아닌 legacy 셸에만 배선**됐고 기본 라우팅이 legacy였기 때문. 전수 대조 결과 실누락은
History 트리+A/B 시각화 **1건**이었고 해소·검증 완료. 크롬 느림은 **정적자산 캐시헤더 부재
(매 로드 2.3MB 재다운로드)** + **`/runs`(3MB) 로드당 3회 과호출(9MB)** 두 원인으로 규명·수정.

`performance_proved=false` 유지(성능=로딩/파이프라인 안전, 전략 알파 주장 아님).

## 1. 근본 원인 — 작업이 어느 셸에 실렸나 (git 증거)

대시보드는 **셸 3종이 단일 컴파일 번들(`bundle/app.js`)을 공유**한다:
- `index.html` → `App`(legacy, 구 "V2" 계보) — `app.jsx`
- `v4.html` → `DashboardV4Shell`(graph-first, PR #105 `8ded51f8`, 7/12 병합) — `dashboard-v4-shell.jsx` + `v4-*.jsx`
- `remodel/` → V3 리모델(별도 렌더러)

PR #105 이후 대시보드 커밋을 파일 단위로 대조하면 **배선 대상이 갈렸다**:

| 커밋 | 기능 | 배선된 셸 | 문제 |
|---|---|---|---|
| `80d102f6` | v4.1 조건식 History API·트리 패널 | **app.jsx (legacy)** | V4 셸 미배선 |
| `0eafbbf8` | A/B 쌍대비교·셀 히트맵·홀드아웃 퍼널 | **app.jsx (legacy)** | V4 셸 미배선 |
| `210749b6` | 반복 세대 사이클 다이어그램 | v4-research.jsx (V4) | 정상 |

`80d102f6`/`0eafbbf8`가 만든 컴포넌트(`history-condition-tree.jsx`,`history-viz.jsx`)는 공유
번들에 컴파일돼 **존재는 했지만 legacy 셸의 렌더 트리에서만 마운트**됐다. 그래서:
- `/ui/evolution`(구 기본=legacy)로 열면 신기능이 보였고,
- `/ui/v4`(graph 셸)로 열면 신기능이 **없었다**.

즉 "V4에 개발하라"는 지시와 달리, **연구 시각화 2건이 legacy 셸에 실렸다**. 이름이 "v4.1
History"라 혼동을 키웠으나 실제 배선은 legacy였다. 사이클 다이어그램만 V4에 올바로 갔다.

추가로 기본 라우팅 자체가 legacy(v2)였다(`_dashboard_version_from_request` 기본 반환 `v2`).
런처 `stom_dashboard.bat`는 `/ui`를 여는데, `/ui`가 legacy를 서빙 → "V4가 안 뜬" 체감.

## 2. 유사 누락 전수 대조 (셸 간 컴포넌트 집합 차이)

`app.jsx` 렌더 태그(62) vs V4 트리 태그(65) 집합 차이를 계산. legacy에만 있고 V4가
직접 참조 안 하던 컴포넌트:

```
App, EvolutionSubtabNav, TabNav, RunSelector, SunMoonIcon, IdleState,
ResearchSuiteCards, FitnessChart, LabPage, ProPage
```

분류:
- **셸 크롬/내비**(App/TabNav/EvolutionSubtabNav/RunSelector/SunMoonIcon/IdleState/
  ResearchSuiteCards): V4가 좌측 레일·컨트롤바·온보딩으로 대체 — 기능 누락 아님.
- **FitnessChart**: V4는 상위호환 `V4HeroChart`(대형 canvas)로 대체 — 누락 아님.
- **LabPage/ProPage**: 독립 페이지 래퍼. V4는 하부 패널을 직접 마운트해 동등 —
  `V4Lab`=ResearchHeatmapPanel+ResearchLabPanel+ResearchWikiPanel,
  `V4Workbench`=ResearchProPanel+RunComparePanel+HallOfFamePanel+HofInventoryGate.

역방향(V4에만 있는 것): V4HeroChart·LoopCycleDiagram·EnginePanel·HoldoutPanel 등 V4 전용
추가. **실질 연구 콘텐츠 누락은 History 트리+A/B 시각화 1건뿐**이었고 `990136c4`에서 해소.

결론: 이번 수정 이후 **V4 셸이 legacy 셸의 모든 연구/분석 패널을 마운트**한다(+ V4 전용).

## 3. 크롬 로딩 느림 — 원인 규명 (실측)

첫 로드 리소스 타이밍(127.0.0.1:8770, 헤드리스 크롬 실측):

| 자산 | 크기 | 캐시 | 비고 |
|---|---|---|---|
| bundle/app.js | 1,953 KB | **NETWORK** | 매 로드 재다운로드 |
| vendor-*·css·stom-ui | ~430 KB | **NETWORK** | 매 로드 재다운로드 |
| **정적 소계** | **2.33 MB** | 캐시 미적용 | Cache-Control 부재 |
| /runs | 3,075 KB | NETWORK | **1 로드에 3회** = 9.2MB |

### 원인 A — 정적자산 Cache-Control 부재
`/ui`가 Starlette `StaticFiles`로 마운트(`app.py`)되는데 기본값은 `Cache-Control` 미부여
(ETag만). `?v=<hash>` 지문(내용 주소화)을 쓰면서도 서버가 캐시 지시를 안 줘, 크롬이 매
내비게이션마다 2.33MB를 재검증/재다운로드. **지문 캐시버스팅의 이점이 완전히 무력화**.

### 원인 B — `/runs` 과호출
`app.jsx`·`dashboard-v4-shell.jsx` 양쪽의 run 목록 useEffect deps가
`[baseUrl, isDemo, liveState.run_id, liveState.status]`였다. WS 상태 하이드레이션(연결 시
run_id "" → 실값, status → running)마다 effect 재실행 → **3MB `/runs`를 3회 재요청(9MB)**.
아카이브 목록은 런이 **종료**될 때만 새 항목이 생기는데도 매 상태 틱에 재조회.

## 4. 조치

### 4-A 서버 캐시헤더 (`app.py` `_FingerprintedStaticFiles`)
`StaticFiles` 서브클래스로 응답 후처리:
- `?v=` 지문 + `.js`/`.css` → `Cache-Control: public, max-age=31536000, immutable`
- `.html` 및 지문 없는 요청 → `no-store`(셸 HTML 캐시 오염 방지)

내용 변경 시 build가 `?v=` 해시를 갱신하고 HTML은 `no-store`라 stale 위험 없음.

### 4-B `/runs` 디듀프 (양쪽 셸 동일 규약)
deps에서 `liveState.run_id/status` 제거. `active→inactive`(런 종료) 전이에서만 `runsEpoch`를
올려 재조회. 결과: 로드당 3회+ → 1회(유휴)/최대 2회(실행 중 완료 반영).

### 4-C 라우팅·라벨 (선행 커밋 `6c4017c2`·`990136c4`)
기본 셸을 V4 graph-first로 승격, legacy는 `?dashboard_version=legacy`로만 1회 열림.
History 트리+A/B 시각화를 `V4History` 탭에 포팅. 런처 주석 갱신.

## 5. 검증 (실측 전후)

| 항목 | 전 | 후 |
|---|---|---|
| 정적자산(warm reload) | 2.33MB NETWORK 매 로드 | **7/7 디스크 캐시, 0KB** |
| /runs 호출/로드 | 3회 (9.2MB) | 2회(실행 중)·1회(유휴) |
| 캐시 헤더 계약 | 없음 | 신규 테스트 5건 |
| 셸 파리티 | History/A-B가 legacy 전용 | V4 완전 마운트 |

- 대시보드+history 회귀 **1,291 통과**(신규 캐시 5·경로매핑 1 포함), 번들 표준 재빌드.
- 라이브 헤더 매트릭스: 지문 자산 `immutable`, 셸 HTML `no-store`, `/ui/*` `v4-ops`.
- 실브라우저: warm reload 정적 0KB·전 자산 DISK-CACHE, V4 History 탭 신기능 렌더 확인.

## 6. 재발 방지 권고

1. **셸 배선 회귀 테스트**: "legacy 셸이 마운트하는 연구 패널은 V4 셸도 마운트한다"를
   소스 대조로 단정하는 테스트 추가(집합 차이 = 셸 크롬 화이트리스트 이내).
2. 신규 대시보드 기능은 **V4(`v4-*.jsx`) 우선 배선**을 원칙화(legacy는 동결 유지·보수만).
3. (후속·선택) `/runs` 3MB 페이로드 경량화: 셀렉터엔 id/label/started_at/gate_passed_count만
   필요 — 요약 엔드포인트 분리 시 로드당 3MB→수십 KB. 계약 영향 검토 후 별도 진행.
