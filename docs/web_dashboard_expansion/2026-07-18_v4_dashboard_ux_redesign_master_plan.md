# V4 대시보드 UX·UI·프로세스 재설계 마스터 플랜 (2026-07-18)

> 지위: **계획·문서만**. 구현은 사장님 승인 후 `feature/dashboard-hodo-20260717`(또는 후속 브랜치)에서 단계별 진행.
> 목적 원문(사장님): **실제 대시보드로 연구를 개선·확인하고, 실시간 연구·데이터를 시각화해 더 좋은 브레인스토밍으로 조건식을 찾는다.**
> 원칙: 현재 기능·데이터 계약 보존(단일 발행기·`performance_proved=false`·읽기 전용 조회), 안전 경계 불변, 단계별 가역 커밋.

---

## 0. 이 문서의 사용법
- §2 = **사장님 요청 전수 기록**(누락 없이·중복 통합·추적 ID `R##`).
- §3 = 현재 구조 이해. §4 = 핵심 진단. §5 = 재설계 방향(IA·레이아웃·탭별).
- §6 = HTML 리포팅·Wiki 체계(양식 포함). §7 = 알파랩 P4 연계. §8 = 단계별 구현 로드맵·검증.

---

## 1. 현재 대시보드 구조 (재설계 출발점)

정본 `/ui` = V4 graph-first 셸(좌측 레일 9탭). 각 탭 마운트 실체:

| 탭 | 컴포넌트 | 내용 |
|---|---|---|
| **Live**(research) | V4ResearchLive | PhaseTimeline·V4HeroChart(fitness)·EquityOverlay·EnginePanel·BacktestDetail·GuiParity·GenerationAnalytics·가정/부검/계보/메타/홀드아웃·ConditionDiscovery·Population·반복사이클 다이어그램 |
| **Backtest** | V4Backtest | BacktestTab(전략 실행·결과 리포트) |
| **Replay** | V4Replay | 캔들 리플레이·신호 로그 |
| **History** | V4History | ResearchRecordsPanel·조건식 History 트리·A/B 쌍대비교·셀 히트맵·홀드아웃 퍼널·ResearchIndexPage |
| **Lab** | V4Lab | ResearchHeatmapPanel·ResearchLabPanel(Edge/상관/변수)·ResearchWikiPanel |
| **Bench**(workbench) | V4Workbench | ResearchProPanel·RunComparePanel·HallOfFamePanel·HofInventoryGate |
| **Audit** | V4Audit | AuditDecisionTrace(/decisions)·VerdictPanel·안전 타일 6종 |
| **Alpha** | V4Alpha | 알파랩 관찰(임시·비-P4) |
| **Context** | AIContextPanel | 모델에 전달된 컨텍스트 팩(복사용) |

상단: 브랜드("조건식 AI 연구 터미널")·버전(`V4 · … · contract vN`)·안전 strip·BASE·Conn/Status·테마. 좌측 레일 상단 로고 + 탭 아이콘.

---

## 2. 사장님 요청 전수 기록 (누락 없이 · 중복 통합)

### 2.1 전역(Cross-cutting)
| ID | 요청 | 실현성 | 비고 |
|---|---|---|---|
| R01 | **Audit 탭 불필요 검토** — 왜 있나/왜 필요한가 (3회 반복) | ✅ | §5.1: 결정 감사 원장. 현 연구 흐름엔 미사용 → 제거/축소 권장 |
| R02 | 오른쪽 패널 펼쳐서 확대 + 글자 크기 증가 | ✅ | §5.3 타이포·밀도 |
| R03 | "조건식 AI 연구 터미널" 아래 **버전 글자 크게 + 하이라이트/효과** | ✅ | §5.3 버전 배지 |
| R04 | 좌측 상단 탭 확대·글자 잘 보이게 + **대시보드 version 더 크게·애니메이션/버튼화** | ✅ | §5.3 |
| R05 | **연구 결과 보고서 시스템**(결과 보고서 탭 기능) — 사람이 개발·검토 편하게 | ✅ | §6 HTML 리포팅 |
| R06 | **울트라와이드(3440×1440) 전체 UX/UI 재배치** | ✅ | §5.2 레이아웃 |
| R07 | 그래프가 너무 큰 사이드로 들어감(3440에서 실측) — 폭 제어 | ✅ | §5.2 |
| R08 | 각 탭 **상단 제목·버튼 글자 크기 확대** | ✅ | §5.3 |
| R09 | **연결 끊김·재연결중 반복 표시**(깜빡임) 문제 (2회) | ✅ | §5.6 연결 UX |
| R10 | 실제 연구 프로세스가 **단계별로 진행되는 것을 사용자와 함께 확인**(단계별 활성화) | ✅ | §5.4 프로세스 스테퍼 |
| R11 | 지금까지 연구 문서를 **Wiki로 체계 정리·관리**(현 내용 보존·유사 포맷) + **연구보고서 양식**(목적/일자/원인/결과/분석/결론) + **문서 포맷**(제목/목차/내용/결론/히스토리/관련문서/관련커밋) | ✅ | §6 Wiki·양식 |
| R12 | **HTML 보고 시스템** — 전체 연구 및 각 연구 스텝 상세 전부 HTML, 탭 이동·확인 | ✅ | §6 (알파랩 reporting 재사용) |

### 2.2 Live 탭
| ID | 요청 | 실현성 |
|---|---|---|
| R20 | 전체 모니터 사이즈 고려 **재배치 — 한 화면에 많은 정보**(눈으로 확인하며 배치) | ✅ |
| R21 | 단계별 실제 시간 / 차단 사유 / 최신 로그가 **글만 있어 UX 이상** → 시각화 | ✅ |
| R22 | process 반복 세대 사이클·현재 세대가 상단·우측에 퍼짐 → **정리 + 애니메이션·체계적 처리** | ✅ |
| R23 | **각 진행 프로세스마다 탭 존재, 프로세스 진행 시 탭 자동 전환, 각 탭별 시각화 정리** | ✅ |
| R24 | 상단에 **백테스트 엔진 상태·시스템 상황**을 전체 대시보드처럼 정리(상태 바) | ✅ |
| R25 | **백테스트 단계엔 사용 조건식이 잘 보이고**, 분석 과정엔 분석 내용·결과 시각화 | ✅ |
| R26 | 불필요 프로세스 정리·병합, live 중간 프로세스에 통합(버튼·내용 과다) | ✅ |
| R27 | 기본 설정/게이트/채점 기준은 **각 단계 정보 클릭 시 표시**(깔끔 정리) | ✅ |

### 2.3 History 탭
| ID | 요청 | 실현성 |
|---|---|---|
| R30 | live 다음 History로 **연구를 체계적으로 관리·열람 고도화** | ✅ |
| R31 | **연구 리스트 → 클릭 시 상세 연구의 모든 정보**(데이터 아키텍처 반영한 연구 히스토리 구축) | ✅ |
| R32 | "연결 끊김 · 표시된 기록은 마지막 응답…" **깜빡임 문제** | ✅ (R09와 동일 원인) |

### 2.4 Lab / Bench(Workbench) 탭
| ID | 요청 | 실현성 |
|---|---|---|
| R40 | **Lab 기능은 Live의 백테스트 분석 결과 프로세스로 이동**(결과 보이는 곳) | ✅ |
| R41 | Lab 안 **시간대·시가총액 구분이 워크벤치와 중복** → 통합 | ✅ |
| R42 | **워크벤치는 '명예의 전당'만 포함**하도록 기능 변경 | ✅ |
| R43 | 워크벤치 **탭 제목 변경** — 인간 + 지금까지 개발·연구 성과가 함께 체계적으로 보이게 | ✅ |

### 2.5 Backtest 탭 (사장님 결정 D2 확정)
| ID | 요청 | 실현성 |
|---|---|---|
| R28 | **Backtest 탭 독립 유지** — python GUI로 하던 백테스트를 **대시보드에서도 실행**하고, **결과를 강력하게 시각화**로 확인 | ✅ (백테 실행 /bt/* 잡·시뮬 기반 존재, 시각화 강화 필요) |

### 2.6 Audit / Alpha / Context 탭
| ID | 요청 | 실현성 |
|---|---|---|
| R50 | **Audit 불필요** — 왜 필요/왜 있나 (R01과 동일) | ✅ |
| R51 | **Alpha랩은 위 연구(P4 카탈로그)대로 추후 함께 고려**해 반영 | ✅ | §7 |
| R52 | **Context 가독성 나쁨·존재 이유 불명** → 재검토 | ✅ | §5.1 |

> **누락 점검**: R01/R50(audit) 및 R09/R32(연결 깜빡임)은 중복 요청으로 통합 기록. 그 외 29개 고유 요청 모두 개별 ID 부여. 실현성 전 항목 ✅(가능). (검토 §4 반영: 31행 → 중복 2쌍 통합 후 29 고유)

---

## 3. 요청의 근본 테마 (중복 요청이 가리키는 것)
사장님 코멘트를 관통하는 5개 축:
1. **정보 밀도·가독성** (R02·R03·R04·R08·R20·R21) — 글자 작고, 텍스트만 나열, 한 화면 정보량 부족.
2. **울트라와이드 활용** (R06·R07·R20) — 3440×1440에서 그래프가 좁은 사이드로 몰림, 폭 낭비.
3. **프로세스 가시화·동행** (R10·R22·R23·R24·R25·R26·R27) — 연구 단계가 텍스트로만, 사용자와 함께 단계별로 진행·확인이 안 됨.
4. **IA(정보 구조) 정리** (R01·R40·R41·R42·R43·R51·R52) — 탭 중복(Lab↔Bench)·불필요(Audit·Context)·미완(Alpha).
5. **연구 지식 관리** (R05·R11·R12·R30·R31) — 연구 이력·보고서·문서를 체계적으로 정리·열람.

---

## 4. 핵심 진단 (현 구조의 문제)
| 문제 | 근거 | 영향 |
|---|---|---|
| 텍스트-only 패널 | Live의 "단계별 시간/차단사유/최신로그"가 나열 텍스트 | 브레인스토밍에 안 쓰임 |
| 탭 중복 | Lab(히트맵 time×시총) ↔ Bench(RunCompare·HoF) 겹침 | 혼란·중복 유지비 |
| 미사용 거버넌스 UI | Audit(결정 감사 원장) — 현 연구엔 승급 결정 없음 | 공간 낭비 |
| 저맥락 유틸 | Context(컨텍스트 팩 복사) — 디버그용, 연구용 아님 | 존재 이유 불명(R52) |
| 고정폭 레이아웃 | 좁은 컬럼·작은 폰트 → 울트라와이드에서 여백 과다 | 정보 밀도 저하 |
| 연결 UX 거침 | WS 지수백오프 `reconnecting` 라벨이 즉시·반복 표기 | 깜빡임(R09) |
| 프로세스 비가시 | Generate→Backtest→Score→Autopsy→Iterate가 카드로만 흩어짐 | 단계 동행 불가(R10) |

---

## 5. 재설계 방향

### 5.1 IA 재편 (탭 구조 — 사장님 결정 D1 확정: 9탭 → 6탭)
| 현재 | 조치 | 근거 |
|---|---|---|
| Live | **유지·강화**(프로세스 스테퍼 중심 재설계) | R20~R27 |
| Backtest | **독립 유지·강화**(D2) — 대시보드에서 백테스트 실행(python GUI 백테 기능) + **결과 강력 시각화** | R25·R28 |
| Replay | 유지(신호 맥락 조사) | — |
| History | **강화**(연구 리스트→상세, 데이터 아키텍처) | R30·R31 |
| Lab | **해체·이전** → 백테스트 분석 결과는 Live 분석 스텝으로, Edge/변수 분석은 History 상세로 | R40·R41 |
| Bench | **명예의 전당 전용**으로 축소 + **탭명 변경**(예: "성과·전당" / "Hall of Fame") | R42·R43 |
| Audit | **탭 제거하되 거버넌스는 이전**(§10-1) — 결정 원장·freeze/verdict·export 경계를 History/Reports Governance 섹션으로 이전, 삭제 아님 | R01·R50 |
| Context | **제거 또는 개발자 메뉴로 격하**(연구용 아님) | R52 |
| Alpha | **P4 카탈로그로 승격**(추후, §7) | R51 |

→ **확정 최종 탭: Live · Backtest · Replay · History · 성과(전당) · Reports** · [Alpha/P4 추후]. (Audit·Context·Lab 제거, **Backtest 독립 유지·강화**)

- **Audit 왜 있었나(정정·검토 반영)**: `final_approval→export_winner` human-approval/export 경계 + `/decisions` append-only 결정 원장 + `/record_decision` 기록이 **실재하는 거버넌스**다. "빈 원장"은 오진단 — **탭 내비게이션은 없애되 결정/freeze/verdict/export 기능은 새 위치(History/Reports Governance 또는 전역 drawer)로 완전 이전**하고 candidate/evidence 바인딩·capability·export 경계 동일 유지를 보안·파리티 테스트로 증명해야 한다(§10-1).
- **Context 왜 있었나(답변)**: LLM에 넣은 컨텍스트를 복사·검증하는 디버그 도구. 연구·브레인스토밍 흐름과 무관 → 개발자 토글로 격하.

### 5.2 울트라와이드(3440×1440) 레이아웃 (R06·R07·R20)
- **컬럼 그리드 상한 제거·확장**: 현 `max-width`/좁은 컬럼 제약을 울트라와이드 브레이크포인트(`≥3000px`)에서 3–4 컬럼 워크스페이스로 재배치.
- **그래프 폭 정책**: fitness/equity 등 주요 차트는 사이드 고정이 아니라 **중앙 확장 영역**(뷰포트 폭 비례, 최소/최대 폭 토큰)으로. "좁은 사이드로 몰림" 해소.
- **밀도 프리셋**: `--v4-density`(compact/comfortable) — 한 화면 정보량 ↑(R20).
- **반응형 검증**: 1440p·1080p·3440×1440 3종에서 육안+스크린샷 게이트.

### 5.3 타이포·버전 배지·탭 강조 (R02·R03·R04·R08)
- **타이포 스케일 상향**: 본문/라벨/제목 토큰 1단계씩 확대, 각 탭 상단 **뷰 타이틀 대형화**.
- **버전 배지**: "조건식 AI 연구 터미널" 아래 버전을 **큰 하이라이트 배지(버튼형)** 로 — 클릭 시 버전/커밋/변경점 팝오버, 미세 애니메이션(pulse).
- **좌측 레일**: 탭 라벨 확대·활성 탭 강조(색·굵기·인디케이터).

### 5.4 Live 탭 — 프로세스 스테퍼 중심 재설계 (R10·R21~R27)
핵심: **"연구가 지금 어느 단계인지, 사용자와 함께 단계별로 보며 진행"**.
- **상단 시스템 상태 바**(전체 대시보드형·R24): run 상태·현재 세대·백테스트 엔진(warm 엔진 수·진행률)·경과.
- **프로세스 스테퍼**(R10·R22·R23): Generate → Backtest → Score → Autopsy → Iterate 를 **가로 스테퍼**로. 단계 진행 시 **자동 하이라이트·애니메이션**, 클릭 시 그 단계 상세 뷰로 이동(단계=서브탭, 자동 전환·R23).
  - Generate: 생성된 조건식·프롬프트.
  - Backtest: **사용 조건식 크게**(R25) + 진행률·엔진 상태.
  - Score: 게이트/채점 결과(통과/탈락 사유).
  - Autopsy: 패배구간 부검 시각화.
  - Iterate: 다음 세대 반영.
- **텍스트-only 제거**(R21): "단계별 시간(generate 50.9s…)"은 **가로 막대/도넛**으로, "차단 사유"는 **체크리스트 배지**로, "최신 로그"는 접이식 타임라인으로.
- **정보 접기**(R26·R27): 기본 설정·게이트·채점 기준은 상시 노출 대신 **각 단계 배지 클릭 → 팝오버**. 버튼·카드 과다 정리, 중복 프로세스 뷰 통합.
- **Lab 흡수**(R40): 백테스트 분석 결과(히트맵·Edge)를 이 Live "분석(Autopsy/Score)" 스텝 안에 배치.

### 5.5 History 탭 — 연구 히스토리 아키텍처 (R30·R31)
- **연구 리스트**(좌) → **상세**(우) 마스터-디테일. 리스트: series·쌍/팔·gate·일자·판정 배지(현 History v4.1 확장).
- 상세: 그 연구의 **모든 정보** — 세대·조건식·평가·부검·홀드아웃·A/B·셀 히트맵·사전등록/결과 문서 링크·관련 커밋. (데이터: `condition_history_v1` + loop_runs.db + 문서 링크, 읽기 전용)
- Lab의 Edge/변수 분석을 History 상세의 "분석" 섹션으로 이전(R41 중복 해소).

### 5.6 연결 UX 안정화 (R09·R32)
- **재연결 라벨 디바운스**: `reconnecting`을 즉시 표기하지 않고 **grace(예: 2초·2회 실패) 후** 표기 → 짧은 WS 재핸드셰이크의 깜빡임 제거.
- **상태 3단 정리**: 연결됨(초록)·재연결 시도중(회색, grace 후)·데모(주황). 마지막 응답 시각 병기.
- **근본 원인 조사**: WS가 실제로 자주 끊기는지(서버 keepalive·프록시) 점검 — 끊김이 잦으면 ping/pong 주기·타임아웃 조정.

---

## 6. HTML 리포팅 · Wiki 체계 (R05·R11·R12·R30)

### 6.1 리포팅 시스템 (알파랩 `reporting/` 재사용·일반화)
- 이미 `alpha_lab/reporting/`(허브→상세→탭 HTML)이 있음 → **조건식 연구용으로 일반화**해 "Reports 탭"에서 열람.
- **Reports 탭**: 전체 연구 허브 → 연구별 상세 HTML → 스텝별 탭. "결과 보고서(예시) 기능"으로 각 연구 결과를 사람이 개발·검토(R05·R12).
- 정적 HTML 생성 + 대시보드에서 iframe/링크 열람(읽기 전용).

### 6.2 연구 보고서 표준 양식 (R11 — 사장님 제시 반영)
```
# <연구 제목>
- 목적:
- 일자: (착수 / 완료)
- 배경·원인: (왜 이 연구를 했나)
- 방법: (설계·사전등록·데이터·게이트)
- 결과: (수치·표·그래프)
- 분석: (무엇을 관찰했나)
- 결론: (판정 — 채택/기각/미결, performance_proved)
- 후속·관련: (다음 단계·관련 연구)
- 이력: (관련 커밋 SHA·문서 링크)
```

### 6.3 문서(Wiki) 표준 포맷 (R11 — 현 내용 보존·유사화)
```
# <문서 제목>
> 목차(TOC)
## 내용
## 결론
## 히스토리 (변경 이력)
## 관련 문서
## 관련 커밋·작업
```
- **현 문서 보존 원칙**: 기존 `docs/research/**`·`docs/update_log/**` 내용을 **바꾸지 않고**, 위 포맷의 **인덱스/프론트매터를 덧붙이는 방식**으로 Wiki화(파괴적 재작성 금지).
- Wiki 진입: History/Reports 탭에서 문서 검색·태그·연대기·관련링크 그래프로 열람.

---

## 7. 알파랩 P4 카탈로그 연계 (R51)
- 별도 문서 `2026-07-18_v4_dashboard_ux_redesign_master_plan` 와 짝: 알파랩 연구 정리는 **P4(§ `2026-07-12_dashboard_data_contract.md`)** 로 이미 설계됨(카탈로그 DB + /research 4엔드포인트 + 5뷰).
- **연계 방침**: 본 UX 재편의 "Reports/History/성과" 골격에 P4 뷰(판정카드·함정지도·절실험실·출구은행)를 **후속 탭**으로 편입. 현 Alpha 관찰 탭은 P4 완成 시 대체.
- 순서(사장님 결정 D4 확정): **본 UX 재편(P1~P6) 완료 후 → 알파랩 P4 카탈로그(P7, 별도 2.5~3일)**.

---

## 8. 단계별 구현 로드맵 (UXR 네임스페이스 — 기존 PROG_P* 문서군과 충돌 회피)

> 검토 §3.3·§3.7 반영: 잘못된 연구 수치·신뢰성 결함을 먼저 닫는 **UXR-P0**를 신설하고, 기존
> `PROG_P1~P7` 문서군과 구분되도록 **UXR-P0~P8** 네임스페이스를 쓴다.

| 단계 | 범위 | 요청 매핑 | 리스크 |
|---|---|---|---|
| **UXR-P0 정확성·안전(先)** | 재검토 BLOCK 교정: Alpha 성능게이트 분리·soft-error·/runs timeout·stale·파리티 주석·캐시 지문 | (검토 §5) | **완료(`736ed1a4`)** |
| **UXR-P1 관측·계약 동결** | WS disconnect 계측, 현 탭/route/field inventory, Backtest parity matrix, baseline 스크린샷 | R09 선행 | 낮음 |
| **UXR-P2 안정화·타이포** | 연결 debounce, 타이포·버전 배지, 탭 강조 | R03·R04·R08·R09·R32 | 낮음 |
| **UXR-P3 IA migration** | Audit 거버넌스 이전·Context 격하·Lab field-level 이전·Bench 개명 + redirect/dual-mount/rollback(§10-7) | R01·R40~R43·R50·R52 | 중 |
| **UXR-P4 울트라와이드·반응형** | 브레이크포인트·그래프 폭·밀도, overflow·접근성 게이트 | R02·R06·R07·R20 | 중 |
| **UXR-P5 Live 스테퍼** | 현 계약(`current_step`·`step_timings`·`backtest_progress`·`engine_state`) 기반 상태기계(§10-9)·follow-live·텍스트→시각화 | R10·R21~R27 | 높음(핵심) |
| **UXR-P6 Backtest gap 보강** | **이식 아님** — 현 웹 구현(`/bt/run`·bt-tab-run·bt-result-area·Monte Carlo) inventory → GUI parity matrix → **결손만** 보강 + 수동 mutation 게이트(§10-4) | R25·R28 | 중 |
| **UXR-P7 History·Reports/Wiki** | History stable identity·join·pagination(§10-10) + Reports 보안 계약(§10-5) | R05·R11·R12·R30·R31 | 중~높 |
| **UXR-P8 알파랩 P4** | 봉인 `/research/*` 계약·5뷰(§10-11) | R51 | 별도(UX 재편 후) |

**검증 게이트(각 단계)**: dashboard+history 회귀 · 셸 배선 가드 · 3해상도(1080/1440/3440) 실브라우저 스크린샷 · 안전 계약(no live/order)·`performance_proved=false`·단일 발행기/읽기전용 조회 불변 + **단계별 acceptance(§10-8)**.

---

## 9. 확정된 결정 (사장님 승인 반영) + 재검토 반영
1. **D1 탭 최종 구성 — 동의**: 확정 6탭 Live·Backtest·Replay·History·성과(전당)·Reports (+Alpha/P4 추후). 단 Audit **거버넌스 이전**(삭제 아님, §10-1).
2. **D2 Backtest 독립 유지** — 단 "이식"이 아니라 **현 웹 구현 gap-only 보강**으로 정정(§10-2, UXR-P6).
3. **D3 우선순위** — 검토 반영해 **UXR-P0(정확성·안전) 완료 → UXR-P1 관측·동결 → P2 안정화 → P3 IA → P4 울트라와이드 → P5 Live 스테퍼 → P6 Backtest → P7 History·Reports → P8 P4**.
4. **D4 알파랩 P4 — UX 재편 후 UXR-P8**.

> 다음 실행 단계: **UXR-P0는 완료(`736ed1a4`)**. 이후 **UXR-P1(관측·계약 동결)** — WS 끊김 계측·현 탭/route/field inventory·Backtest parity matrix·baseline 스크린샷. UX 구현(P2~) 착수 전 **본 개정 계획 승인 요청**.

---

## 10. 재검토 필수수정 반영 (검토 §6 11건 — 실행 계약 보강)

> 검토 보고서 `2026-07-18_ae23c847_ux_redesign_master_plan_review.md` §6의 11개 필수수정을 계약으로 봉인한다. 각 단계 착수 전 세부 실행문서로 전개한다.

### 10-1. Audit 거버넌스 이전 계약 (삭제 아님)
- 이전 대상: `AuditDecisionTrace`(`/decisions`)·`VerdictPanel`(freeze/regime/portfolio/verdict)·`final_approval→export_winner` 경계·`/record_decision`.
- 새 위치: History 또는 Reports의 **Governance 섹션**(또는 전역 drawer). 탭 내비게이션만 제거.
- 증명: candidate/evidence 바인딩·capability check·export governance 동일 유지 + 보안·파리티 테스트 통과 후에만 기존 내비 retire.

### 10-2. Backtest는 "이식"이 아니라 "gap-only 보강" (UXR-P6)
- 현 자산 inventory: `POST /bt/run`·`bt-tab-run.jsx`·`bt-result-area.jsx`(메트릭·차트·Monte Carlo)·`bt-tab-analysis.jsx`(overlay·A/B·portfolio)·`/bt/report`.
- 산출물: **python GUI ↔ 웹 field-level parity matrix** → 실제 결손만 구현. `/bt/report`는 Reports 허브에 기존 job taxonomy 유지한 채 연결(병렬 신규 금지).

### 10-3. UXR-P0(정확성·안전) 선행 — **완료**
- Alpha 성능게이트 분리(10/10/8/2/0)·soft-error·/runs timeout·stale·파리티 주석·캐시 지문 → `736ed1a4`.

### 10-4. 읽기전용 vs Backtest mutation 경계
- 읽기전용 SELECT-only는 **P4 `/research/*` 한정**. 일반 대시보드는 수동 mutation 보유.
- `POST /bt/run`·`/bt/job/cancel`·`/bt/job/meta`·`/bt/strategy`·`/bt/strategy/delete` 각각에 **수동 action·확인 절차·허용 저장소·자동호출 금지·demo/reference inert·CSRF/origin/auth 경계** 명시.

### 10-5. Reports/Wiki 보안·서빙 계약
- 허용 report root + path traversal 차단, iframe `sandbox`+CSP(스크립트 차단), 생성 HTML escape/sanitization·신뢰등급, 외부 URL·`file://`·절대경로 차단.
- index schema(stable ID·provenance/hash·missing/stale), 검색 API 범위·pagination·encoding·대형문서 제한.
- ⚠ `alpha_lab/reporting/build_html.py` 산출물은 **inline JS 포함** → same-origin iframe 금지(sandbox 또는 inert 렌더). "읽기 전용 화면" 설명만으로 안전하지 않음.

### 10-6. 단계 번호·순서 정본화
- **UXR-P0~P8** 단일 네임스페이스 고정(§8). §7 자기참조·P7/P8 혼용 제거.

### 10-7. IA 제거·이전의 route/state/migration 계약
- `/ui/audit`·`/ui/lab`·`/ui/context`·localStorage tab key redirect/fallback, deep-link·뒤로가기 호환.
- 컴포넌트별 새 owner + field-level parity 표, `test_shell_wiring_parity.py` whitelist 변경 기준, 번들 재생성·manifest hash.
- **삭제를 목적지보다 앞세우지 않는다** — 새 owner dual-mount + parity 통과 후에만 기존 내비 retire. feature flag rollback.

### 10-8. 단계별 acceptance 템플릿(각 UXR-P* 착수 시 채움)
대상/비대상 파일 · API/props/route 계약 · before/after 스크린샷(뷰포트별 overflow 허용치) · 측정 기준(연결 깜빡임 false-offline 허용치 등) · 자동 탭 전환이 수동 선택 안 덮는 규칙 · keyboard/focus/reduced-motion/a11y · build 명령·focused test 목록 · rollback 조건·feature flag.

### 10-9. Live 스테퍼 상태기계 계약
- raw phase(`latest.phase`·`current_step`·`phase_started_at`·`step_timings`·`backtest_progress`·`engine_state`) → 표시 상태(pending/active/success/failure/skipped/retry) 매핑표.
- idle/complete/stopping/legacy snapshot 처리, blocker·로그·시간 원천 필드, reconnect/replay 동작.
- **follow-live vs user-pinned 분리** — 사용자가 다른 단계 보는 동안 강제 이동 금지. backend 단일 발행기 불변.

### 10-10. History 데이터 계약
- stable research/run/series ID·join key·source precedence·provenance·pagination·redaction·partial/missing/conflict 상태.
- `/history/index`·`/history/detail` 응답 schema·byte-identical 필드·presentation-only 변환 + complete/partial/missing/conflict fixture. P7 전 봉인.

### 10-11. P8(알파랩 P4) 계약 승계
- normative input: `2026-07-12_dashboard_data_contract.md`(mode=ro·무집계·단일 DB·schema/mtime·오류 envelope·원문 딱지·acceptance) + `2026-07-12_dashboard_view_specs.md`.
- 5뷰 = 판정카드·함정지도·절실험실·출구은행 + **B1 live scorecard**(data-vessel/U-4 선행·별도 승인). `alpha_router`↔`research_router` 소유권·경로 충돌 재조사, 카탈로그 경로를 파일 서빙 URL로 바꾸지 않음.

### 10-보완(검토 §4)
- 연결 debounce 전 **disconnect 빈도·원인·ping/pong 증거 수집**(장애 은폐 방지).
- `performance_proved=false`를 **모든 연구 카드·보고서·export 근처**에 source-field 기반 표기.
- Wiki는 **원문 불변** — 별도 sidecar/index DB 또는 generated manifest(원문 frontmatter 수정 금지).
- 기간 추정은 작업분해 근거 확보 전까지 참고치로만.
