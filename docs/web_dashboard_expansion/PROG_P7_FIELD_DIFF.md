# PROG P7 — HoF + freeze_verdict 공유-셸 통합: 필드 다이프 (착수 전 산출물)

> **#1 규칙: 어떤 고유 필드도 손실되어선 안 된다.** 아래 두 쌍은 "중복"이 아니라 "발산(divergent)"이다.
> 진짜로 공유되는 블록만 추출하고, 각 패널의 모든 고유 필드/기능은 그대로 유지한다.
> 무손실 추출이 불가능하면 병합하지 않고 발산을 문서화한다.

날짜: 2026-06-15 · 브랜치: `feature/webbt-prog-p7-shell-unify`

빌드 모델(build-app.mjs ORDER): `chart.jsx`(idx4) < `research-pro.jsx`(idx13) < `research-lab.jsx`(idx14) < `dashboard-pages.jsx`(idx24) < `app.jsx`(idx25).
공유 컴포넌트는 **더 이른 ORDER 소비자**에 고유 top-level `function` 으로 정의하고, 더 늦은 소비자는 JSX 에서 `<window.<Name> .../>` 멤버표현식으로 직접 참조한다.
⚠️ **`const X = window.X` 자기-별칭으로 참조하면 안 된다** — 단일 번들 한 스코프에서 정의측 `function X` 와 충돌해 "already declared" SyntaxError(전 앱 크래시)가 난다(실제 P7 1차 구현에서 발생, 멤버표현식으로 수정). test_no_duplicate_globals 는 이제 자기-별칭도 최상위 선언으로 카운트해 이 충돌을 차단한다(과거 "자기-별칭 예외" 블라인드스팟 폐기).

---

## 쌍 A — Hall of Fame

| 항목 | `HallOfFamePanel` (chart.jsx ~1404) | `_RpHallOfFame` (research-pro.jsx ~355) |
|------|--------------------------------------|------------------------------------------|
| 마운트/소비처 | app.jsx 메인 대시보드(독립 패널) | research-pro `ProPage` 내부 카드(refreshKey) |
| 데이터 fetch | `GET /hall_of_fame` (timeout 4000) | `GET /hall_of_fame` (timeout 8000) |
| isDemo 가드 | ✅ (`window.isDemoSource(wsStatus)`) | ✅ (prop `isDemo`) |
| 사용하는 배열 | `data.human` + `data.ai` (둘 다) | `hof.ai` 만 (run_id·gen_no 있는 행) |
| 행 종류(kind) | human / seed / ai 3종 | seed / ai 2종 (human 미표시) |
| 마크업 시스템 | `.panel`/`.data-table` + 인라인 스타일 + `HOF_KIND_META`(색/배경/라벨 맵) | `.rp-card`/`.rp-table` + CSS 클래스 `.rp-kind-*` |
| 숫자 포맷 | `fmtMoney`,`fmtPctSigned`,`fmtPlain`,`fmtInt2` (chart.jsx) | `_rpMoney`,`_rpPct`,`_rpInt`,`_rpNum` (research-pro.jsx) |
| **컬럼** | 구분·이름·**총수익금(원)**·총수익률%·연평균%·MDD%·**payoff**·**일평균거래**·**동시보유**·**운영금(원)**·백테기간 | 종류·전략(run/gen)·백테기간·**점수(score)**·총수익·수익률·연환산·MDD·**거래(trades)**·액션 |
| 고유 컬럼 (A만) | **payoff, daily_avg_trades(일평균거래), _maxHold(동시보유), operating_capital_krw(운영금)** | — |
| 고유 컬럼 (B만) | — | **score(점수), trades(거래수)** |
| 고유 기능 (A만) | **정렬**(5키: 총수익률/총수익금/연평균/MDD/payoff), **필터**(전체/인간/시드/AI), **카운트 요약**(인간 N·시드 N·AI N), **📷 인간 결과 스크린샷 갤러리**(`ReferenceGallery`, `/reference_screenshots`+`/reference_img`), **30초 자동 새로고침**(setInterval), 단기-연환산 신뢰낮음 경고 칩, `annual_unreliable` 인라인 배지 | — |
| 고유 기능 (B만) | — | **확장 가능 인라인 조건식 미리보기**(`_RpStrategyCode`, 행 펼침), **"바로 백테스트" 워크벤치 링크**(`_rpOpenWorkbench`→백테스트 탭 적재), score 컬럼 |
| 공유 | `/hall_of_fame` fetch, isDemo 가드, `ai` 배열, 기본 테이블 chrome(thead/tbody) | (동일) |

### HoF 결정: **DEFER (병합 보류) — 근거 첨부**

**결정: 두 HoF 패널은 진짜로 발산하며, 컴포넌트 병합은 필드를 손실시키므로 분리 유지한다.**

근거:
1. **컬럼 집합이 비대칭.** A는 payoff·일평균거래·동시보유·운영금(원)을 가지고 human 행을 표시한다. B는 score·trades 를 가지고 human 행을 숨기며 run/gen 식별자 + 확장 조건식을 가진다. 공유 테이블-코어로 합치려면 "각 패널이 자기 컬럼셋을 넘기는" 설정 주도 구조(config-soup)가 되어 가독성·무손실 보장이 모두 깨진다.
2. **마크업/스타일 시스템이 다르다.** A는 `.data-table`+`HOF_KIND_META` 인라인, B는 `.rp-table`+`.rp-kind-*` CSS 클래스. 시각 일관성은 이미 공유 CSS 토큰(`var(--violet)`/`var(--amber)`/`var(--green)`)으로 제공되므로, 컴포넌트 합치기 없이도 일관성이 유지된다.
3. **숫자 포맷 헬퍼가 파일-로컬**(chart.jsx 의 fmtMoney vs research-pro.jsx 의 _rpMoney) — 공유 코어는 이들을 props 로 주입해야 하므로 추가 결합만 늘어난다.
4. **기능 발산이 본질적.** A의 정렬/필터/갤러리/자동새로고침과 B의 확장-조건식/워크벤치-링크는 서로 다른 사용자 동선(메인 성과 비교 vs 프로 조건식 재사용)을 섬긴다. 공통 분모로 환원되지 않는다.

→ **얇은 공유 헬퍼조차 안전 이득이 없다.** `HofKindBadge` 같은 뱃지 헬퍼는 A(HOF_KIND_META 인라인 3종)와 B(.rp-kind CSS 2종)의 시각 표현이 달라 통합 시 한쪽 스타일을 손실시킨다. 따라서 P7 에서 HoF 는 **변경하지 않는다**(무손실 불가 → 보류 문서화).

---

## 쌍 B — freeze_verdict

| 항목 | `_ValidationPanel` (research-lab.jsx ~370) | `VerdictPanel` (dashboard-pages.jsx ~167) |
|------|---------------------------------------------|--------------------------------------------|
| 마운트/소비처 | research-lab 의 read-only 검증 서브탭(더 큰 패널 내부) | verdict.html 이 이름으로 마운트(FROZEN 전역) |
| 데이터 fetch | `GET /freeze_verdict` (timeout 12000) | `GET /freeze_verdict` (+regime/revival/portfolio/decisions) |
| **공유 블록 1: PROMOTE 체크리스트** | ✅ `verdict.promote_checklist[]` {item,status,detail} 테이블 (status: pass✅/warn⚠️/fail❌/else⏳) | ✅ `v.promote_checklist[]` 테이블 (ICON 맵 사용) |
| **공유 블록 2: alerts** | ✅ `verdict.alerts[]` ⚠️ 리스트 (color: `var(--amber)`) | ✅ `v.alerts[]` ⚠️ 리스트 (color: `#c95`) |
| **공유 블록 3: summary-lines** | ✅ `verdict.lines[]` 리스트 | ✅ `v.lines[]` 리스트 |
| 고유 (A=_ValidationPanel) | **walkforward 창 테이블**(`verdict.walkforward.windows[]`: fit/eval/theta/policy/baseline) + 전체 검증 서브탭(ops·니치·연도분해·선택기·부검·반사실·MC·TMAP·격자·포트폴리오 결합 등 방대) | — |
| 고유 (B=VerdictPanel) | — | **OOS-CI 테이블**(`v.oos_diff_ci`: year/total_diff/CI95/P) + **4개 서브탭**(summary/regime/portfolio/decide), 결정 폼·이력, 레짐·부활, V6 포트폴리오 |

### 미세 스타일 차이(정본화 대상 — 의도된 작은 픽셀 변경)

| 속성 | _ValidationPanel(A) | VerdictPanel(B) | **정본 채택(더 풍부/깔끔)** |
|------|----------------------|------------------|------------------------------|
| 체크리스트 fontSize | 11 | 12 | **12** (B) |
| 체크리스트 width | 미지정 | `width:100%` | **100%** (B) |
| status→아이콘 | 인라인 삼항(pass/warn/fail/else⏳) | `ICON` 맵(pass/warn/fail/pending) | **로컬 status→icon 맵**(공유 컴포넌트 내부 정의, 전역 ICON 비의존) |
| 빈 상태 메시지 | 없음 | "PROMOTE 체크리스트: 데이터 없음" | **있음**(B) |
| alert 색 | `var(--amber)` | `#c95`(하드코딩) | **var(--amber)**(A, 토큰화) |
| alert fontSize | 11 | 12 | 12(B 와 통일) |
| lines fontSize | 11 | 12 | 12(B 와 통일) |

데이터 필드는 **정확히 동일**(`promote_checklist[].item/status/detail`, `alerts[]`, `lines[]`) → 무손실 추출 가능.

### freeze_verdict 결정: **DO (공유 추출 — 명확한 승리)**

3개 공유 블록을 `research-lab.jsx`(더 이른 ORDER)에 고유 이름으로 1회 정의하고 window-export:
- `function VdtPromoteChecklist({ v })`
- `function VdtAlerts({ v })`
- `function VdtSummaryLines({ v })`

소비:
- `_ValidationPanel`(research-lab.jsx): 인라인 체크리스트/alerts/lines → `<VdtPromoteChecklist v={verdict}/>` 등. **walkforward 테이블 등 나머지 전부 유지.**
- `VerdictPanel`(dashboard-pages.jsx): 인라인 체크리스트/alerts/lines → `<window.VdtPromoteChecklist v={v}/>`·`<window.VdtAlerts v={v}/>`·`<window.VdtSummaryLines v={v}/>` 멤버표현식 직접 참조(자기-별칭 const 금지 — 충돌). **OOS-CI 테이블 + 4 서브탭 전부 유지.**

---

## 손실되지 않는 고유 필드 체크리스트(추출 후 검증용)

- _ValidationPanel: walkforward 창 테이블(fit/eval/theta/policy/baseline), ops 현황, 니치 비교, 연도분해, 선택기 미리보기, 부검/반사실/MC/TMAP/격자, 포트폴리오 결합 — **모두 유지**
- VerdictPanel: OOS-CI 테이블(year/total_diff/CI95/P), 4 서브탭(summary/regime/portfolio/decide), 결정 폼·이력, 레짐·부활, V6 포트폴리오 — **모두 유지**
- HallOfFamePanel: 정렬·필터·갤러리·30초 자동새로고침·payoff/일평균거래/동시보유/운영금 컬럼·human 행 — **변경 없음(유지)**
- _RpHallOfFame: 확장 조건식·바로 백테스트·score·trades — **변경 없음(유지)**
