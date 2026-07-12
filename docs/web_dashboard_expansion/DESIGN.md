# STOM 웹 대시보드 설계 문서 (design.md)

> 2026-06-13 · Phase 6 (사용자 요청 S6: "이런 대시보드들이 가지고 있는 특징들, 잘 개발하기 위한 design.md").
> 적용 대상: V4 8탭([Research|Backtest|Replay|History|Lab|Workbench|Audit|Context])과 공통 셸.

## 1. 이 대시보드의 정체성

**"연구를 거래 화면의 밀도로 보여주는 분석 워크벤치"** — 일반 BI 대시보드가 아니라
트레이딩 터미널(HTS)·백테스트 리포트·실험 추적기(MLflow류)의 교집합이다. 따라서:

시각 방향은 새 외부 브랜드를 모사하지 않고 현행 터미널 언어를 정교화한다. 기억에 남는
장면은 Research의 대형 성과 그래프와 그 옆에서 실제 단계·시간·차단 사유가 함께 변하는
"graph-first evidence viewport"다. 표면 깊이는 `--bg-0..3`의 tonal shift와 hairline만으로
만들고, 장식성 카드·광택·무의미한 모션은 사용하지 않는다.

| 참조 모델 | 가져오는 특징 | 우리 구현 |
|-----------|--------------|----------|
| 트레이딩 터미널(HTS) | 정보 밀도, 실시간 갱신, 호가/체결 색 관습(매수=적, 매도=청) | 시뮬 탭 호가 사다리·오더플로우 테이프·라이브 캔들 |
| 백테스트 리포트(QuantStats류) | 수익곡선+MDD+분포+롤링 지표를 한 화면에 | 백테탭 분석 그리드·GUI 패리티 차트·HTML 리포트 |
| 실험 추적기 | run/세대 단위 이력, 비교, 명예의 전당 | 리서치랩·리서치 프로·Run Compare |
| 리플레이 도구 | 시간 비례 재생, 배속, 시킹 | wall-clock 페이싱 WS 스트림 |

## 2. 핵심 설계 원칙

1. **시간의 정직함**: 리플레이는 bar 간 실제 시간차 ÷ 배속으로 진행한다(1x에서 1분봉=1분).
   고정 인터벌 전송 금지. 모든 시계열 축에는 실제 기간(연도 포함)을 표기한다.
2. **데이터의 정직함**: DB에 없는 호가 레벨·지수를 합성하지 않는다. 있는 컬럼만 쓰고
   한계는 UI에 라벨로 명시한다("호가 1단계만 제공" 등). 추정치(체결강도 기반 매수/매도 분해 등)는
   추정임을 표시한다.
3. **무예외 API 계약**: 모든 대시보드 라우트는 HTTP 200 + `{ok, error}` 페이로드.
   읽기 전용 라우트는 엔진 상태를 절대 변경하지 않는다.
4. **빈 화면 금지**: 모든 탭은 첫 진입 시 예시(데모) 데이터를 '예시' 배지와 함께 표시한다.
5. **설명 가능한 UI**: 새 용어(세대·격자·니치·적합도·OOS)는 등장 위치에 hover 설명을 붙인다.
   축·단위·기간이 없는 차트를 만들지 않는다.
6. **재열람 가능성**: 모든 결과(잡·run·세대)는 ID로 다시 불러와 동일 시각화로 재현 가능해야 한다.

### 2.3 Dashboard control-plane security contract

- Ordinary read-only domain responses may retain the historical HTTP 200 + `{ok,error}`
  contract. Authentication and authorization failures are transport failures: missing or
  expired session is HTTP 401 / WebSocket 4401, while forbidden Origin or capability is
  HTTP 403 / WebSocket 4403.
- Only exact same-origin loopback `GET /ui/v4` and `GET /ui/v4/` bootstrap a process-local,
  bounded-lifetime `HttpOnly; SameSite=Strict` session. Other public reads never mint it.
- Every REST mutation and WebSocket action is server-classified. Loop control, safe backtest,
  and replay control are authenticated; strategy write, decision write, provider test, and
  final approval remain server-side default-OFF capabilities.
- Mutation payloads are frozen, strict, bounded Pydantic contracts. Unknown fields/actions and
  coercive booleans or resource values fail before a handler or side effect runs.
- Final approval is authorized only by a fresh server binding over the current completed run,
  generation, server winner, hard-gate result, frozen review, and strategy-code/evidence hashes.
  Client labels do not select or authorize the winner. Paired buy/sell export is one SQLite
  transaction and rolls back as a unit.

## 3. 시각 언어

- **폰트**: 라틴/숫자 = IBM Plex Sans/Mono, 한글 = 맑은 고딕(Malgun Gothic) 명시 fallback.
  탭·본문·차트 축 모두 동일 스택(`--sans`/`--mono`)만 사용 — 개별 font-family 하드코딩 금지.
- **색 관습**: 상승/매수 = `#4cd6b3`(민트적 역할, 다크 테마 가독성), 하락/매도 = `#ff5d6c`.
  호가창은 국내 HTS 관습(매도호가 청색조 위, 매수호가 적색조 아래)을 따른다.
- **밀도 우선, 그러나 위계**: 카드(패널) 단위 구성, 섹션 헤더로 그룹화, 핵심 수치는 stat 카드
  (큰 mono 숫자 + 작은 라벨). 차트는 컨테이너 폭 추종(고정 px 셀 금지 — ResizeObserver).
- **애니메이션은 의미가 있을 때만**: 라이브 캔들 성장·체결 플래시·활성 단계 글로우처럼
  "지금 무엇이 변했는가"를 전달할 때만 사용. 장식성 무한 애니메이션 금지.

### 3.1 디자인 토큰 일관성 (Phase11)
- **하드코딩 색 금지**: 인라인 hex/rgba 대신 토큰만 — 상태 배경은 `--teal-bg`/`--amber-bg`/`--red-bg`,
  강조는 `--teal`/`--amber`/`--red`/`--violet`/`--blue`, 텍스트는 `--ink-0..3`, 고원 강조는 `--mesa-gold`.
  토큰은 다크/라이트 양 테마에 정의돼 테마 전환 시 자동 대응(하드코딩은 라이트에서 깨짐).
- **공통 시각 유틸 재사용**(styles.css): 게이지 = `.stom-gauge`(+`.warn`/`.danger`),
  프로세스 흐름 = `.stom-flow-*`(SVG 노드/화살표·활성 글로우), 상관 히트맵 = `.stom-combo-*`.
  같은 의미의 위젯은 같은 클래스를 쓴다(탭마다 재발명 금지).
- **상태 표현 3종 일관**: 완료=teal, 진행/주의=amber, 위험/손실=red. 게이지 임계도 동일
  (CPU/MEM warn≥70~75·danger≥90).
- **빈 상태·섹션 헤더 통일**: 빈 상태는 한글 "데이터 없음/부족" 톤, 섹션 헤더는 `.research-empty`/`.panel-hd-title` 패턴.

## 4. 아키텍처 제약 (이 환경의 사실)

- 프런트는 **in-browser Babel JSX**: import/export·TS 불가, 컴포넌트는 window 전역,
  파일별 훅 별칭. 외부 CDN 금지 — 벤더는 저장소에 동봉(lightweight-charts 등).
- `index.html`의 `?v=` 캐시 버전은 계약 테스트(`test_index_html_cache_bumped`)와 동기 —
  jsx 수정 시 반드시 버전 범프.
- **React 참조 규약**: 스트림 누적 데이터는 immutable append(새 배열 생성)로 갱신한다.
  같은 배열을 push로 mutate하면 `useEffect` deps가 변화를 감지하지 못해 차트가 동결된다
  (Phase 6 봉 1개 버그의 실제 원인 — 회귀 금지).
- 차트 렌더 경로는 3종: ① Canvas `SimLiveChart`(라이브 리플레이 기본 — 성장 캔들·플래시),
  ② lightweight-charts(정밀 탐색·줌), ③ SVG(의존성 zero 보장 경로). 데이터 공급 인터페이스(bars 배열)는 동일하게 유지한다.
- 파일 분리: 탭당 로직 jsx + 차트 jsx, 800줄 초과 시 분할(예: sim-live-chart.jsx).
- 부모 핫파일(`app.py`·`app.jsx`·`research-lab.jsx`)은 외과수술적 최소 수정 —
  새 기능은 신규 파일 + 등록 줄 패턴(evolution-analysis.jsx·research-pro.jsx 선례).

## 5. 데이터 흐름 요약

```
일일 tick/min DB ─ replay_engine(OHLC·지표·호가 프레임) ─ /sim/ws (wall-clock 페이싱) ─ 시뮬 탭
strategy.db ─ stom_backtest CLI ─ BacktestJobManager ─ per-trade CSV ─ backtest_analysis(순수함수)
            └ /bt/run·/bt/jobs·/bt/analysis/* ─ 백테탭·리서치 프로·HTML 리포트
ai_strategy_loop state ─ app.py 읽기 라우트 ─ 진화 탭·리서치랩(·프로) ─ "바로 백테스트"(CustomEvent)
```

## 6. 공통 토큰과 재사용 primitive 계약

### 6.1 토큰

- 색·표면은 `--bg-0..3`, `--line-1..2`, `--ink-0..3`, `--teal`, `--amber`,
  `--red`, `--violet`, `--blue`, `--*-bg`만 쓴다. 상태는 색만이 아니라 아이콘·문구·형태로
  중복 인코딩한다. 새 raw hex/rgb/rgba는 금지한다.
- 본문/수치는 `--sans`/`--mono`, 크기는 `--fs-prose`, `--fs-dense`, `--fs-label`에
  연결한다. 수치·시간·ID는 tabular figures를 쓴다.
- 새 간격은 4px 격자(4/8/16/24/32)를 우선하고, 기존 6/10/14px는 선언된
  `--space-*` 호환 토큰으로만 유지한다. radius도 `--radius-*`만 쓴다.
- 후속 구현은 사용 전에 `--control-dense: 32px`, `--target-touch: 44px`,
  `--focus-width: 2px`를 공통 토큰으로 선언한다. fine pointer 데스크톱은 dense 높이,
  375px·coarse pointer는 최소 44×44 CSS px를 적용한다.
- dark/light는 의미가 동일한 한 쌍이다. `--ink-3`는 장식·비활성 보조 정보에만 쓰며
  본문이나 필수 라벨에 쓰지 않는다. focus는 양 테마에서 `--blue` 외곽선과 배경 간
  3:1 이상, 본문은 WCAG AA를 충족한다.

### 6.2 primitive와 상태

| Primitive | 책임 | 필수 상태 |
|---|---|---|
| `V4AppFrame` | rail/tablist, topbar, controlbar, stage의 유일한 셸 | live/archive, connected/disconnected |
| `SafetyStrip` | DEMO, 실거래 없음, HUMAN GATE, capability 상태 | safe, blocked; 장식 애니메이션 없음 |
| `RunSelector` | LIVE와 archive를 명시적으로 분리 | idle, loading, selected, error; 실패 시 live 대체 금지 |
| `StatusChip` | 짧은 상태·위험·승자 표시 | neutral, running, success, warning, danger, blocked |
| `MetricStrip` | 동일 단위의 핵심 수치 묶음 | value, unavailable(`—`+사유), stale |
| `StatePanel` | empty/loading/error/blocked의 공통 골격 | 제목, 원인, 마지막 정상 시각, 한 개의 복구 행동 |
| `ChartPanel` | 제목·단위·기간·범례·요약을 가진 시계열/분포 | loading skeleton, empty, error, stale, ready |
| `DataRegion` | 표/코드/로그의 소유된 overflow 영역 | keyboard focus, scroll affordance, row selected |
| `ActionBar` | 현재 문맥의 primary/secondary/danger 작업 | disabled reason, pending, success, error |
| `ProcessTimeline` | 실제 단계와 단계별 소요시간/차단 사유 | pending, active, done, failed, blocked |
| `TraceRow` | Audit/로그의 시각·actor·action·evidence 연결 | collapsed, expanded, copied |

`loading`은 레이아웃과 같은 skeleton으로 표시하되 진행률을 추정하지 않는다. `empty`는
아직 데이터가 없음을, `error`는 요청 실패와 재시도를, `blocked`는 정책·gate·capability로
진행할 수 없음과 해제 조건을 뜻한다. 이 네 상태를 같은 "데이터 없음" 문구로 합치지 않는다.

## 7. 8개 탭 화면 계약

| 탭 | 사용자 목표와 primary journey | 첫 화면의 필수 데이터/그래프 | 상태·위험 동작 | 375px collapse 순서 | 키보드/ARIA |
|---|---|---|---|---|---|
| **Research** | 연구 시작 → 실제 단계/세대/시간/로그 관찰 → 승자 검토 → 서버가 허용할 때만 승인 | 적합도/수익 추이 hero chart, `ProcessTimeline`, 단계별 시간, blocker, 최신 로그, winner 근거 | empty는 시작 안내, loading은 현재 단계만, error는 재연결, blocked는 gate 사유. start/stop/final approval는 danger이며 final approval default-OFF | authority/run → timeline → hero chart → metrics → blockers/log → winner/action | 단계 변경은 polite live region, 실패는 alert. 차트에는 텍스트 요약과 동일 데이터 표 제공 |
| **Backtest** | 전략 선택 → 실행 → queue/진행 확인 → 취소 또는 결과 분석 | equity+MDD chart, status/queue, 핵심 성과, trades, 실행 로그 | 전략 없음/queued/running/error/cancelled/blocked를 구분. run/cancel 및 strategy write는 확인·서버 capability 필요 | selector/action → status → equity/MDD → metrics → trades → log | 실행/취소 결과를 live region에 알리고, trades 표의 헤더·정렬 상태를 노출 |
| **Replay** | 세션 선택 → play/pause → 정확한 index seek → speed 변경 → 특정 frame 검토 | timestamp candle canvas, frame index/전체, 실제 경과시간, speed, 주문흐름/제공 데이터 한계 | source empty/loading/error/ended/blocked. start/seek/stop은 활성 Replay에서만 동작 | session/status → canvas → transport → timestamp/metrics → tape/detail | transport 이름·현재값 노출. 단축키는 활성 panel에서 비편집 focus일 때만; 숨은 Replay는 inert |
| **History** | archive 선택 → 로드 → 세대/성과 탐색 → 두 run 비교 또는 관련 탭 이동 | run 목록, fitness/equity summary, generation table, 비교 delta | archive empty/loading/error/stale. 로드 실패 시 live 데이터로 대체 금지; 삭제·승인은 제공하지 않음 | selector/error → summary → chart → generation list → compare/actions | 선택 행과 비교 대상을 명시하고, 표 캡션·헤더·정렬 상태 제공 |
| **Lab** | factor/edge view 선택 → 분포·상관·안정성 검사 → 근거를 후보와 연결 | factor importance/distribution, edge decay, correlation heatmap, sample/OOS 범위 | 표본 부족/계산 중/error/blocked를 구분. 분석 결과는 연구 근거이며 승인 권한이 아님 | scope/filter → primary factor chart → edge/correlation → sample caveat → detail | Canvas/SVG마다 요약·범례·data table, 필터 label과 선택 상태 제공 |
| **Workbench** | 후보 선택 → 나란히 비교 → 차이/constraint 확인 → Backtest/Context로 이동 | candidate comparison chart/table, 조건식 diff, hard-gate/score breakdown | 후보 부족/loading/error/stale. 선택/이동은 안전, export/approval은 여기서 수행 금지 | candidate selector → comparison summary → chart → diff → gates → actions | 비교 대상 수와 기준을 announce, diff는 줄 번호·추가/삭제를 텍스트로도 전달 |
| **Audit** | 기간/actor/action 필터 → decision 추적 → evidence 펼침 → ID 복사 | append-only timeline/table, capability·run/gen·hash linkage | empty/loading/error/tamper-warning/blocked. 기록 수정·삭제 UI 금지, decision write default-OFF | filters → warning/summary → trace list → expanded evidence → copy | 필터 fieldset/legend, 행 expand 상태, copy 결과 live region; 색만으로 outcome 구분 금지 |
| **Context** | run/gen 선택 → exact context pack 읽기 → 섹션 탐색 → 전체/부분 복사 | source IDs/hashes, prompt/rules/strategy/evidence sections, truncation 여부 | pack empty/loading/error/stale/blocked. 민감값은 서버가 제외; copy는 원문과 해시를 바꾸지 않음 | identity/hash → section nav → context body → truncation note → copy actions | heading outline, labelled code region, copy 대상/결과 announce, 가로 긴 코드는 owned region에서만 scroll |

### 7.1 Research graph-first viewport의 고정 위계

1280px 첫 viewport에서 hero chart가 주 콘텐츠 열의 가장 큰 면적을 차지한다. 그 위에는
LIVE/archive와 authority, 실제 `current_step`/`current_gen`이 있고, 옆 또는 바로 아래에는
`ProcessTimeline`, 단계별 누적이 아닌 개별 timing, blocker와 최신 로그가 보인다. 서버가
`current_gen=-1`을 보낸 경우 "시작 전"으로 표시하고 0세대로 보정하지 않는다. 그래프가
없어도 StatePanel이 같은 영역을 점유해 레이아웃이 무너지지 않으며, fake percent·합성 데이터로
빈 공간을 채우지 않는다.

## 8. 탭 내비게이션 exact ARIA 계약

1. 8개 탭을 포함하는 단일 요소는 `role="tablist"`와 접근 가능한 이름을 가진다.
2. 각 tab의 안정 ID는 `v4-tab-{key}`, panel은 `v4-panel-{key}`다. tab은
   `aria-controls`, `aria-selected`; panel은 `role="tabpanel"`, `aria-labelledby`로
   양방향 연결한다.
3. 선택 tab만 `tabIndex=0`, 나머지는 `-1`이다. `ArrowRight`/`ArrowLeft`는 순환,
   `Home`/`End`는 첫/마지막 tab으로 이동하고 즉시 선택한다. 이 자동 활성화 모델은 8개
   panel이 로컬이며 전환이 지연되지 않는다는 전제다.
4. 키 이동 후 focus는 선택 tab에 남고 panel로 강제 이동하지 않는다. 포인터 전환으로
   숨을 panel 안에 focus가 있었다면 새 선택 tab으로 회수한다.
5. 비활성 panel은 접근성 트리와 focus 순서에서 제외한다. Replay는 WS/재생 위치 보존을
   위해 마운트 상태를 유지하지만 `hidden`, `aria-hidden="true"`, `inert`를 함께 적용한다.
   활성 panel에는 세 속성을 제거한다.
6. URL의 유효한 `?tab=`은 초기 선택과 roving tabindex를 함께 결정한다. 알 수 없는 값은
   Research로 fail closed한다. 새로고침·archive 변경 뒤에도 선택 tab focus 계약을 유지한다.

## 9. 반응형·확대·overflow 계약

| 조건 | 셸과 제어 | 콘텐츠 |
|---|---|---|
| **1280px 이상** | rail + sticky top/control bar, run selector 한 행 우선 | Research는 hero+evidence rail, 다른 탭은 의미 있는 2열까지 허용 |
| **768px** | rail은 가로 tab strip 또는 축소 rail, header/control은 2행 wrap | main/side를 1열 또는 2열로 재배치하며 DOM/읽기 순서는 모바일 순서와 동일 |
| **375px** | tab strip, safety/run controls 완전 wrap, primary action 우선 | 모든 탭 1열; 위 표의 collapse 순서. 필수 라벨·상태를 ellipsis로 숨기지 않음 |
| **200% zoom** | 1280 CSS viewport가 약 640px인 경우 tablet/narrow 규칙 적용 | 문서 전역 overflow 0, sticky 요소가 콘텐츠/포커스를 가리지 않음 |

- 모든 grid/flex 자식과 차트 wrapper는 `min-width: 0`이다. `html/body/#root`에
  `overflow-x:hidden`을 넣어 결함을 숨기는 방식은 금지한다.
- 표·코드·정밀 시계열처럼 폭 보존 이유가 있는 `DataRegion`만 `overflow-x:auto`를 쓴다.
  영역은 focus 가능하고 접근 가능한 이름과 시각적 scroll affordance를 가진다. 차트는 우선
  ResizeObserver로 폭을 맞추며, owned region 밖으로 canvas/SVG가 넘지 않는다.
- 한국어 문장은 `word-break: keep-all; line-break: strict; overflow-wrap: break-word`를
  기본으로 한다. URL·hash·조건식·긴 ID에만 `overflow-wrap:anywhere`를 적용한다. 수치+단위,
  부호+숫자, 짧은 괄호 묶음은 가능한 한 함께 유지하며 chip과 action group은 줄바꿈한다.
- 375px/coarse pointer의 버튼, tab, select trigger, transport control은 최소 44×44 CSS px다.
  focus ring과 tooltip은 viewport에 잘리지 않아야 한다.

## 10. 접근성·테마·motion 계약

- DOM은 header/nav/main/section/aside/table/button의 의미를 보존하고 클릭 가능한 `div`를
  만들지 않는다. 모든 input/select에는 화면에 보이거나 프로그램적으로 연결된 label이 있다.
- `:focus-visible`은 2px 이상 외곽선과 충분한 offset을 가지며 hover/active/disabled와
  구별된다. focus를 제거하는 reset은 금지한다.
- `prefers-reduced-motion: reduce`에서는 pulse, flash, smooth scroll과 비필수 transition을
  제거한다. 상태 변화는 정적 아이콘·문구·색으로 남는다. 일반 모션도 transform/opacity/filter만
  쓰며 변화나 affordance를 설명하지 못하는 애니메이션은 금지한다.
- dark/light 모두 같은 정보·Canvas·상태를 표시한다. 테마 전환으로 chart series, focus,
  disabled reason, tooltip이 사라지면 실패다.
- 상태 갱신은 `aria-live="polite"`, 현재 작업을 막는 요청 실패만 `role="alert"`를 쓴다.
  고빈도 tick/log 전체를 live region으로 읽지 않고 요약된 상태 변화만 알린다.

## 11. 수용된 디자인 부채

| 부채 | 영향과 허용 이유 | 소유자 / 종료 조건 |
|---|---|---|
| in-browser Babel JSX, window 전역 | route-level code splitting/정적 타입 이점 제한. 현행 런타임 계약이라 W2-B에서 프레임워크 전환 금지 | W3 / production JSX runtime check와 vendor-Babel syntax gate 통과 |
| Replay keep-alive hidden mount | 메모리를 사용하지만 WS와 seek 위치 보존에 필요 | W2-A/W2-B / 비활성 `inert`·리스너 해제·메모리/키보드 QA 통과 |
| V2 공용 primitive와 V4 scoped CSS 병행 | 일부 legacy literal이 남을 수 있으나 V2 회귀를 피하기 위한 외과수술 범위 | W2-B / 새 토큰 우회 0, 중복 primitive inventory 기록 |

접근성, 전역 overflow, 오해를 부르는 상태에 대한 수용 부채는 없다. 새 Minor/Note만
영향 사용자, 정확한 위치, 수정안, 소유자, 사용자 승인 근거가 있을 때 기록할 수 있으며
Critical/Major는 완료 전에 수정한다.

## 12. 측정 가능한 품질 게이트와 점수 rubric

탭별 100점은 primary task completion 25, state/data honesty 20, responsive 15,
keyboard/accessibility 15, visual hierarchy/feedback 15, automated+real-browser evidence 10으로
계산한다. P0/P1, console/page error, 미검증 primary journey, global overflow, 오해를 부르는
상태, stale capture 중 하나라도 있으면 최대 94점이다.

- fresh installed Chrome에서 8탭 × 375/768/1280 × dark/light = 48개 기본 surface를
  캡처하고, 별도로 200% zoom, reduced motion, 긴 CJK, empty/large dataset을 검증한다.
- 모든 화면에서 `document.documentElement.scrollWidth <= clientWidth`; 넘침은 이름 붙은
  owned `DataRegion` 안에서만 허용한다.
- tablist는 tab 8, `aria-selected=true` 1, `tabIndex=0` 1, 노출 tabpanel 1이다.
  좌/우/Home/End, focus retention, hidden Replay inert를 실제 키보드로 검증한다.
- 8탭의 empty/loading/error/blocked와 danger action denied/pending/success/error를 fixture로
  렌더한다. Canvas는 non-empty pixels와 예상 draw/interaction event를 함께 증명한다.
- dark/light의 본문 AA, focus/비텍스트 상태 3:1, 375px touch 44×44, console/page/request
  error 0을 확인한다. 새 raw color·spacing bypass·중복 primitive는 0이어야 한다.
- objective visual-qa 뒤 Lane C의 접근성/휴리스틱/persona 검토를 수행하고 두 독립 reviewer가
  같은 fresh build에 PASS해야 한다. Critical/Major가 하나라도 남으면 실패다.

### 12.1 저장소 품질 게이트 (모든 Phase 공통)

전체 pytest 신규 실패 0(pre-existing 제외) · verifier · vendor-babel 구문 검사 ·
실데이터 스모크 · **Playwright 스크린샷**(육안 회귀 — 특히 차트 렌더) · 캐시 계약 동기 ·
부모 사전 동기화 후 PR → 머지 → wt-dev 8770 재기동.
