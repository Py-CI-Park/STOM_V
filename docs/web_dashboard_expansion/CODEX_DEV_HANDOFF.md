# Codex 개발 핸드오프 — 동시 개발 · 워크트리 · DB 안정 운영 노하우

> 목적: 이번 세션(Track Z 대시보드 현대화)에서 쓴 **개발 방식 전체**를 Codex(또는 다른 AI 에이전트)가 그대로 재현할 수 있도록 기록한다.
> 핵심 주제: ① wt-dev에서 **연구/업데이트가 라이브로 돌아가는 동안** 별도 워크트리에서 대시보드를 개발하고 PR-머지로 동시 진행한 방법, ② **공유 SQLite DB**를 쓰면서도 안정적으로 개발한 노하우, ③ 검증 게이트·실수·교훈·치트시트.
> 작성 시점 기준: parent 브랜치 `lazycodex/tick-sparse-positive-generation-improvement-20260604`, 8770 라이브.

---

## 0. 한눈에 보는 운영 모델

```
[wt-dev]  parent 브랜치 체크아웃 · 8770 라이브 서버 · 연구 루프(loop_runs.db 쓰기) · 미커밋 연구파일 ~240개
   │  (절대 손대지 않는 보호 영역: ai_strategy_loop/{tmap,scripts,brain/prompts}/**, .omo/**, docs/update_log/**, backtest/graph/, tests/unit/test_*(비대시보드))
   │
   │  origin/parent  ◀── PR 머지(merge commit) ──┐
   ▼                                              │
[wt-webbt] parent 기준 feature 브랜치 분기 → 개발 → 게이트 → PR → 머지
   │                                              │
   └── 머지 후: git -C wt-dev merge origin/parent  (대시보드 파일만 갱신, 연구 파일 무손치)
                 → 8770 새로고침이면 반영(정적 서빙, 서버 재시작 불필요)
```

**불변 원칙(이게 안정성의 핵심):**
1. **파일 분리(file-disjoint)** — 대시보드 개발은 `ai_strategy_loop/dashboard/**` + `tests/unit/dashboard/**`(+ 일부 `tests/unit/test_dashboard_*`)만 만진다. 연구는 그 외. 두 워크스트림이 **같은 파일을 동시에 수정하지 않으므로** 같은 parent 브랜치에서 충돌 없이 공존한다.
2. **연구 워크스트림 미접촉** — wt-dev의 미커밋 연구 파일은 commit/stash/reset/삭제 절대 금지. 반영(merge)은 *대시보드 파일만* 업데이트한다.
3. **동작 불변(behavior-invariant) 우선** — 대시보드 변경은 가능한 한 런타임 동작을 바꾸지 않는다(빌드/구조 리팩터). 그래야 라이브 8770·연구 루프·DB에 영향이 없다.
4. **모든 변경은 게이트 통과 후에만 머지** — 빌드 + 런타임 하네스 + 전체 테스트 + verify_nonrelease.

---

## 1. 저장소 · 워크트리 토폴로지

`git worktree list` (7개, 단일 `.git` object store 공유):

| 워크트리 | 브랜치 | 역할 | 규칙 |
|----------|--------|------|------|
| `STOM_V/` | STOM_Version_2 | V2 ingress 베이스라인 | 손대지 않음 |
| `STOM_V.wt-2u/` | STOM_Version_2U | V2U 레인 | 손대지 않음 |
| `STOM_V.wt-3*/` | STOM_Version_3/3U/3U_C | V3 계열 베이스라인 | 손대지 않음 |
| **`STOM_V.wt-dev/`** | `lazycodex/tick-sparse-...` (parent) | **활성: 8770 + 연구 루프 + DB writer** | 읽기/반영만, 연구파일 미접촉 |
| **`STOM_V.wt-webbt/`** | `webbt-base`(=origin/parent 추적) | **대시보드 개발 워크트리** | 여기서 feature 분기 → PR |

- **워크트리는 `.git`을 공유** → 한 브랜치는 한 워크트리에서만 체크아웃 가능. 그래서 wt-webbt는 parent를 직접 체크아웃 못 하고, parent를 *추적하는* 로컬 브랜치(`webbt-base`) 위에서 feature 브랜치를 분기한다.
- **로컬 작업 브랜치는 머지 후 정리해도 히스토리는 보존**된다(§8). 원격 `feature/webbt-*` ref + merge commit + PR 3중 보존.

---

## 2. 동시 개발 모델 (핵심)

### 2.1 왜 가능한가 — file-disjoint
`git -C wt-dev merge origin/parent`가 항상 깨끗한 이유: parent에 들어오는 변경(대시보드)과 wt-dev의 미커밋 변경(연구)이 **겹치는 파일이 0개**라서 git이 대시보드 파일만 업데이트하고 연구 파일은 건드리지 않는다. 머지 전 항상 dry-run으로 확인:

```bash
DEV=.../STOM_V.wt-dev ; B=lazycodex/tick-sparse-positive-generation-improvement-20260604
git -C "$DEV" merge-tree $(git -C "$DEV" merge-base HEAD origin/$B) HEAD origin/$B \
  | grep -iE "CONFLICT|changed in both" || echo "no conflicts"
```

### 2.2 표준 1-사이클 (대시보드 작업 → 반영)
```bash
WT=.../STOM_V.wt-webbt ; DEV=.../STOM_V.wt-dev
B=lazycodex/tick-sparse-positive-generation-improvement-20260604

# 1) 최신 base에서 작업 브랜치 분기
cd "$WT" && git fetch origin && git checkout -B webbt-base origin/$B
git checkout -b feature/webbt-<작업명>

# 2) 개발 (ai_strategy_loop/dashboard/** + tests/unit/dashboard/** 만)

# 3) 게이트(§4) 전부 통과

# 4) 커밋 + 푸시 + PR + 머지 (merge commit 유지 = 브랜치 라인 보존)
git add <변경파일>
git commit -m "<type>(webbt): ..."
git push -u origin feature/webbt-<작업명>:feature/webbt-<작업명>
gh pr create --base "$B" --head feature/webbt-<작업명> --title "..." --body-file <body.md>
gh pr merge <PR번호> --merge        # ⚠️ 스택 PR이면 --delete-branch 주의(§7)

# 5) 8770(wt-dev)에 반영 — 연구 파일 미접촉
LOCK=.../.git/worktrees/STOM_V.wt-dev/index.lock
[ -f "$LOCK" ] && [ ! -s "$LOCK" ] && rm -f "$LOCK"     # 0-byte stale lock(GitKraken poller) 제거
git -C "$DEV" fetch origin
git -C "$DEV" status --short -- ai_strategy_loop/dashboard/ | head   # 대시보드 파일 clean 확인(비어야 함)
git -C "$DEV" merge --no-edit origin/$B                 # 대시보드만 갱신, 연구 미커밋 보존
# 8770 브라우저 Ctrl+Shift+R (정적 서빙 → 서버 재시작 불필요)
```

### 2.3 반영이 막히는 경우 & 안전 처리
`git merge`가 `your local changes would be overwritten`로 abort하면(=wt-dev에 그 파일 미커밋 변경 존재):
- **그 파일이 대시보드 파일이면**(예: 다른 워크스트림이 같은 대시보드 기능을 미커밋으로 작업 중) → 그 작업을 먼저 origin에 정식화하거나, 백업 후 `git restore -- <대시보드파일들만>` 으로 정리 후 머지. **연구 파일은 절대 restore/clean 금지.**
- 패치 백업: `git -C "$DEV" diff -- <파일> > backup.patch` 후 처리.
- abort는 안전하다(트리 무변경). 원인 파일을 정확히 좁혀서만 처리한다.

### 2.4 절대 하지 말 것
- wt-dev 푸시(연구팀이 자기 시점에 푸시). 반영은 **로컬 머지만**.
- 연구 파일(tmap/scripts/.omo/brain/prompts/docs/update_log) commit·삭제·reset.
- `backtest/graph/`를 git 소스로 취급(보호된 결과 데이터).

---

## 3. DB · 데이터 사용 & 안정 개발 노하우 (핵심)

### 3.1 데이터 지형
- **`loop_runs.db`** (SQLite, `controller.state._S.LOOP_RUNS_DB`): 연구/진화 루프의 run 데이터. **writer = 연구 루프(wt-dev), reader = 대시보드 백엔드(app.py, 8770)**. app.py에 직접 `sqlite3.connect(...)` ~9곳.
- JSON 아티팩트: `reference_strategies.json`, `regime_report_*.json`, `rejected_registry.json`, `.omo/evidence/pipeline/*/state.json` 등.
- 세대별 equity CSV, StaticFiles(스크린샷/번들).
- **`backtest/graph/`**: 보호된 결과 데이터.

### 3.2 어떻게 "쓰면서 동시에" 안정적으로 개발했나
1. **대시보드 개발이 DB 접근층을 안 건드림** — Track Z는 *프론트엔드 빌드/소스* 리팩터(동작 불변)였다. app.py의 DB 라우트·쿼리는 무변경. → 라이브 8770(DB 읽기)와 연구 루프(DB 쓰기)가 개발 중에도 중단 없이 계속 돌았다. **DB 경합이 개발에서 발생하지 않음.**
2. **항상-200 graceful 계약** — 백엔드 라우트는 예외를 던지지 않는다(`HTTPException` 0개). 데이터 없음/락/부분상태면 `{"error": ...}` 본문을 200으로 반환. → 연구 루프가 DB에 쓰는 중(쓰기 트랜잭션)에도 대시보드가 크래시하지 않고 우아하게 빈/에러 상태를 렌더.
3. **테스트는 DB를 모킹** — 런타임 하네스(node+jsdom)는 `/status`→contract-valid `IDLE_STATE`, `/config/spec`→`[]`, `/health`→ok, WebSocket→onopen stub 로 백엔드를 *모의*한다. → 대시보드 테스트가 **라이브 DB나 실행 중 서버 없이** 결정론적으로 돈다. DB 상태와 무관하게 게이트가 안정.
4. **8770은 정적 서빙** — 서버는 커밋된 `bundle/*`·HTML을 정적 제공. 반영 = 파일 새로고침이라 **서버 재시작/DB 커넥션 재생성 불필요** → 라이브 DB 세션·연구 루프에 무중단.
5. **SQLite 동시성** — 읽기(대시보드)는 짧은 connect, 쓰기(루프)는 단일 writer. 읽기 다수 + 단일 writer 공존(WAL 친화). 대시보드가 DB 스키마/쓰기를 안 건드리므로 writer와 충돌 없음.
6. **결과 데이터 불변** — `backtest/graph/`·`.omo/evidence/`는 git 전파 소스로 다루지 않음. 대시보드는 *읽기만*.

### 3.3 Codex에서 지킬 DB 규칙
- 대시보드 작업이면 **DB 접근층(app.py 쿼리/connect) 변경 금지** — 프론트만. 불가피하게 백엔드를 바꿔야 하면 별도 작업·별도 검증으로 분리.
- 테스트는 **항상 DB를 모킹**(하네스의 IDLE_STATE/RUNNING_STATE 픽스처 재사용). 라이브 DB 의존 테스트 만들지 말 것.
- 라우트는 **no-exception graceful** 패턴 유지(예외→200+error 본문).

---

## 4. 검증 게이트 (모든 PR 필수, 정확한 명령 + 기대값)

```bash
WT=.../STOM_V.wt-webbt
# 1) 빌드 (모던 ESM 번들; 결정론적 = 재실행 시 동일 해시)
cd "$WT/ai_strategy_loop/dashboard/webui-build" && node build-app.mjs

# 2) 런타임 하네스 — 7탭 + 3 standalone 페이지 0-error 렌더 (DB 모킹, jsdom)
node track-z-harness.mjs            # → "allPass": true

# 3) 누락 cross-module import 정적 체커 (분해형 작업 필수)
node check-missing-imports.mjs      # → ZERO

# 4) 전체 유닛 테스트 — ⚠️ tests/unit/dashboard/ 만 돌리지 말 것(§6 교훈). 전체!
cd "$WT" && python -m pytest tests/unit/ -q -p no:cacheprovider
#   기대: 7 failed (사전존재 backend/CLI/PyQt) / ~3240+ passed / 2 skipped — 신규 실패 0

# 5) non-release sync verifier
python scripts/verify_nonrelease_sync.py   # → exit 0

# 6) 파일 크기 상한
wc -l ai_strategy_loop/dashboard/frontend/*.jsx | sort -rn | head   # 모두 ≤ 800
```

**핀 베이스라인(고정값)**: `7 failed` = 사전존재 backend/CLI/PyQt 계약 테스트(test_backtest_button_contract, test_backtest_process_protocol_diagnostics×2, test_backtest_spawn_contract_audit×2, test_runner_helpers, test_ui_jisu_cleanup). 이들은 **프론트와 무관 — 고치지 말 것**. 매 PR이 정확히 이 집합과 동일해야 한다.

---

## 5. Track Z에서 쓴 구체 기법 (재사용 가능한 패턴)

### 5.1 빌드 모델 (현재 상태)
- `webui-build/build-app.mjs`: **esbuild `bundle:true` → `frontend/bundle/app.js` (classic IIFE)**. 단일 엔트리 `src/track-z-entry.pilot.js`가 모듈 그래프를 끌어옴.
- **React는 alias-to-shim**으로 외부화: `src/react-shim.js`(`export const {useState,...} = window.React`), `react-dom-shim.js`. esbuild엔 rollup식 `output.globals`가 없어서 bare `external`은 런타임 `require("react")` 크래시 → **alias→가상 shim**이 정답.
- `manifest.json`에 `model:"bundle"` 기록. content-hash `?v=`를 5개 HTML에 자동 주입. **단, `styles.css ?v=`는 수동 핀**(변경 시 5 HTML + 핀 테스트 동시 갱신).
- 과거 concat(단일 전역스코프) 경로는 은퇴(P5.0). 모듈 스코프라 이름 충돌 구조적 불가능.

### 5.2 FROZEN 계약 (개명/변경 금지)
- `window.LabPage/ProPage/VerdictPanel/App` — HTML이 이름으로 마운트. 엔트리가 `Object.assign(window, {...})`로 재발행.
- stom-ui 노출(`fmt*`/`STATUS_KR`/`_axisTicks`/`_priceTick`/`_hmsTimeLabel`/`STOM_PIPELINE`/`isDemoSource`/`livePanelPending`) — **항상 `window.`로 참조, import 변환 금지**.
- app.js 스크립트 태그는 classic+defer 유지(type=module 금지 — inline 마운트와 cross-realm 문제).

### 5.3 대형파일 분해 패턴 (barrel)
원본 `X.jsx`(예: 2873줄) → **얇은 barrel `X.jsx`**(import 후 동일 `export {...}` + `Object.assign(window,...)` 재발행) + **<800줄 하위 모듈 N개**. 소비자는 변경 없음(barrel에서 동일 표면 import). 모든 파일 ≤800줄.

### 5.4 가드(영구 회귀 방지)
- `test_no_duplicate_globals` / `test_no_duplicate_top_level_declarations` — 전역 충돌.
- `check-missing-imports.mjs` + `test_no_missing_cross_module_imports.py` — **bare cross-module 참조 누락**(하네스가 못 잡는 클래스).
- `track-z-harness.mjs` V1~V4 — 파일럿/서빙번들/탭별/standalone 런타임 렌더.
- 하네스 freshness 가드 — 커밋된 번들이 소스와 동기인지(`git diff --quiet`).

---

## 6. 실수 & 교훈 (정직 기록 — Codex가 반복하지 말 것)

| 실수 | 증상 | 교훈/규칙 |
|------|------|-----------|
| **게이트 축소** — 속도 위해 `pytest tests/unit/dashboard/`만 돌림 | 상위 `tests/unit/`의 소스-읽기 테스트 27개가 분해로 깨졌는데 미감지 → 누적 후 39 failed | **파일을 옮기는 작업(분해/리네임)은 매 단계 전체 `tests/unit/`**. 하위폴더 게이트 금지. |
| **bare 헬퍼 import 누락** — `_btFetchJson` 등 | 빌드는 통과(esbuild가 free-global로 둠), 런타임 fetch 경로에서 `ReferenceError` | 하네스는 모든 fetch 경로를 안 돈다 → **정적 `check-missing-imports` 가드 필수**. 분해 시 `<Component/>`뿐 아니라 **bare 헬퍼/const 참조**도 import 연결. |
| **스택 PR `--delete-branch`** | base 브랜치 삭제가 의존 PR을 auto-close | 스택 PR은 자식을 먼저 parent로 retarget 후 머지, 또는 `--delete-branch` 빼기. 닫히면 동일 내용 새 PR로 대체. |
| 빌드 산출물 미커밋 | freshness 가드 1 failed | 소스 변경 PR엔 **재빌드한 `bundle/app.js`+manifest+HTML 동봉 커밋**. |
| 헤더 주석의 `*/`, `fmt*/...` | esbuild 주석 조기종료/정규식 오인 | 주석에 `*/`·`fmt*/` 금지(` / `·`·` 사용). |

---

## 7. 브랜치 · 히스토리 관리

- **머지는 merge commit**(`gh pr merge --merge`) — `git log --graph`에 각 브랜치 라인 + `Merge pull request #N` 영구 기록. squash/rebase는 라인 소실하니 지양.
- **로컬 작업 브랜치 정리해도 히스토리 3중 보존**: ① merge commit 그래프, ② 원격 `feature/webbt-*` ref, ③ GitHub PR. → 로컬은 워크트리/브랜치 최소로 유지, 깃 라인은 살아있음.
- 로컬 정리: `git checkout -B webbt-base origin/$B` 로 비킨 뒤 `git branch | grep feature/webbt | xargs git branch -D` (모두 merged면 안전).
- **워크트리는 함부로 제거 금지**(특히 wt-dev=연구·8770, V2/V3 베이스라인).

---

## 8. Codex로 옮길 때 — 에이전트 운영 패턴

이 작업들을 Codex 에이전트로 구동할 때의 권장 운영:
1. **계획은 합의로** — 큰 작업 전 Planner→Architect→Critic식 합의(이 repo에선 ralplan)로 위험·게이트·수용기준을 먼저 고정. Codex에선 동일 역할을 순차 프롬프트(설계→반론검토→비평)로 재현.
2. **저자/검토 분리** — 작성 패스와 검토 패스를 분리(같은 컨텍스트에서 self-approve 금지). Codex도 별도 검토 단계로.
3. **단계별 green 체크포인트** — 한 PR = 한 논리 단위. 게이트(§4) 통과 시에만 다음. 막히면 마지막 green에서 정지·보고.
4. **비가역 단계는 사전 보고** — flip 같은 비가역 변경 전엔 사람 확인. 안전망(예: 폴백 플래그/되돌림 단일 커밋) 마련.
5. **독립 검증** — 에이전트 보고를 믿지 말고 핵심 게이트(빌드/하네스/전체 베이스라인/체커)를 **오케스트레이터가 직접 재실행**해 확인.
6. **보호 경계 명시** — 매 작업 프롬프트에 "연구 파일·backtest/graph·stom-ui exports·7개 사전존재 실패 미접촉"을 못박기.
7. **DB 안전** — 대시보드 작업은 프론트만, 백엔드 DB층 무변경, 테스트는 DB 모킹(§3.3).

---

## 9. 빠른 참조 치트시트

```bash
# 환경
WT=C:/System_Trading/STOM/STOM_V.wt-webbt
DEV=C:/System_Trading/STOM/STOM_V.wt-dev
B=lazycodex/tick-sparse-positive-generation-improvement-20260604

# 작업 시작
cd "$WT" && git fetch origin && git checkout -B webbt-base origin/$B && git checkout -b feature/webbt-<X>

# 게이트(전부 통과해야 머지)
cd "$WT/ai_strategy_loop/dashboard/webui-build" && node build-app.mjs && node track-z-harness.mjs && node check-missing-imports.mjs
cd "$WT" && python -m pytest tests/unit/ -q -p no:cacheprovider   # 7 failed / 2 skipped / 나머지 pass
python scripts/verify_nonrelease_sync.py

# 머지 + 반영
git add -A && git commit -m "..." && git push -u origin feature/webbt-<X>:feature/webbt-<X>
gh pr create --base "$B" --head feature/webbt-<X> --body-file body.md && gh pr merge <N> --merge
git -C "$DEV" fetch origin && git -C "$DEV" merge --no-edit origin/$B   # 8770 반영(연구 미접촉)

# 히스토리 조회
git log --graph --oneline "$B" | head -40        # 머지 라인
gh pr list --state merged --limit 30             # PR 히스토리
```

---
*이 문서는 Track Z 세션의 운영 방식을 그대로 옮긴 것이며, 동시-개발/DB-안정/검증-게이트/히스토리-보존 노하우를 Codex가 재현하기 위한 단일 참조다. 관련 상세: 같은 폴더의 `TRACK_Z_*` 문서(설계·실행로그·flip·분해), `COLLISION_TAX.md`.*
