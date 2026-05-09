# V3 / V3U / 2U_C 백포트 중간 점검 체크포인트 (v2)

작성일: 2026-05-06
v1 작성 시각: 2026-05-06 21:32:20 +0900 (root) / 21:32:22 +0900 (wt-dev)
v2 갱신: 2026-05-06 (동일일 이내 보강본)
기준 commit: `23924c8ffdede60c52f7dfe6eb4b15101ffa2679`
기준 제목: `V3 전환 전략 기준선을 문서화한다`
기준 시각: `2026-05-05 08:22:40 +0900`
체크포인트 commit (root): `38894912e05517ee443dba57a49dbbd7e74a1b1a`
체크포인트 commit (wt-dev): `8182764e1be54a2f39f5df3b97929d3fe57fe2d5`

## 0. v2 갱신 사유

v1 체크포인트는 현재 위치 고정에 집중했다. v2는 다음 작업자가 즉시 이어가도록 다음을 추가한다.

1. 과거 흐름을 단방향 타임라인으로 시각화한다.
2. 통합 진행률을 page 단위와 ASCII bar로 동시 표기한다.
3. 다음 단계용 OMC / PowerShell 명령을 단계별로 제공한다.
4. 종결까지 남은 모든 단계를 단일 테이블로 합친다.
5. 미래 개발을 더 잘하기 위한 운영 원칙을 영역별로 분리한다.
6. v1과 동일하게 root와 `wt-dev` 양쪽에 미러로 유지한다.

이 갱신은 기능 변경이 아니라 방향 유지 강화 목적이며, runtime 코드는 변경하지 않는다.

## 1. 문서 목적

이 문서는 V3 전환 전략 kick-off 이후 실제로 진행된 `STOM_Version_2`, `STOM_Version_3`, `STOM_Version_3U`, `STOM_Version_2U_C` 작업을 한 자리에서 추적하기 위한 checkpoint이다.

목적은 다음과 같다.

1. `23924c8f` 이후 진행된 V3 / V3U / 2U_C 흐름을 한 문서에서 다시 찾을 수 있게 한다.
2. V3 본편 11페이지가 어디까지 완료되었는지 명확히 한다.
3. 2U_C V3 backport 후속 cycle의 완료, no-op, hold 항목을 분리한다.
4. 다음 작업자가 즉시 이어갈 현재 page와 다음 page를 알 수 있게 한다.
5. `STOM_Version_3U_C`를 만들지 않는다는 원칙과 runtime artifact 미커밋 원칙을 다시 고정한다.
6. 다음 단계용 OMC / PowerShell 명령과 남은 전체 단계 테이블을 제공한다.

## 2. 통합 진행률 한눈 보기

```text
전체    [██████████████████░░]   91.3%   42 / 46 page
─────────────────────────────────────────────────────
V3 본편 [████████████████████]  100.0%   11 / 11 page
백포트  [████████████████████]  100.0%   30 / 30 page
재정렬  [████░░░░░░░░░░░░░░░░]   20.0%    1 /  5 page  ← 현재 위치
```

계산 기준:

```text
V3 본편 11 page 완료
+ 완료된 backport cycle 30 page (BP 사이클 6건 × 5 sub-page)
+ 현재 재정렬 cycle 1 page 완료
= 42 page 완료

전체 정의된 page = 11 + 30 + 5 = 46 page
```

이 v2 체크포인트 작성은 별도 갱신이며, 백포트 page 번호를 임의로 증가시키지 않는다.

## 3. 워크트리 지도 (HEAD 일치 검증 포함)

| 경로 | branch | 역할 | HEAD | 상태 |
|---|---|---|---|---|
| `STOM_V/` | `STOM_Version_2` | root orchestration / 공식 V2 유지 / V3-2U_C 문서 추적 | `0200c855` | clean |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | V2 pyd-free 유지 lane | `09c73048` | clean (현재 휴면) |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C` | Kiwoom 유지 custom / V3 선별 backport lane | `76329b3b` | `?? backtest/graph/`만 존재 |
| `STOM_V.wt-3/` | `STOM_Version_3` | V3 공식 ingress 완료 lane (V3.18) | `7faec937` | clean |
| `STOM_V.wt-3u/` | `STOM_Version_3U` | V3 pyd-free + parity audit 완료 lane | `4aef1cce` | clean |
| `STOM_V.wt-2uc/` | `integration/adopt-cli-v267-into-2uc` | archive / transition lane | `cf0e21c1` | active 아님 |

주의:

- `STOM_Version_3U_C`는 아직 만들지 않는다.
- `_database`, `_log`, `*.db`, `backtest/graph/` runtime/output 파일은 커밋하지 않는다.
- 2U_C의 `backtest/graph/`는 보호 대상 output 폴더로 남겨 둔다.

## 4. 23924c8f 이후 단방향 타임라인

```text
23924c8f  V3 전환 전략 기준선 문서화
   │
   ├── Phase 0~5  V3 worktree / DB seed / upstream ref / slice 계획 고정
   │              82256855, 9e8b7685, f0974285, cecdd2a1, b1da9924
   │
   ├── Phase 6    STOM_Version_3 에 V3.0 → V3.18 공식 반영 (19 commits)
   │              06b70418 → cb4cf6aa → ... → f5975f4c → 7faec937
   │
   ├── Phase 7~10 STOM_Version_3U pyd-free 전환 + parity audit (4 commits)
   │              c04faec0 → d05c132c → 3d8f9c1e → 4aef1cce
   │
   ├── c9dec9a4   V3 / V3U handoff 종결
   │
   ├── Phase 11   2U_C V3 백포트 큐 시작 (allowlist 고정)
   │              9cd88726 → 96049642 → 542d5701
   │
   ├── 백포트 적용  BP-004A → 004B → 004C(no-op) → 002A → 002B → 002C(hold)
   │              e204e0f3, 944bab37, f2f447d1, 76329b3b
   │
   ├── 38894912   root v1 중간 점검 체크포인트 고정
   ├── 8182764e   wt-dev v1 동일 미러
   │
   ├── (이 v2 갱신)  과거 / 미래 / OMC 명령 / 남은 단계 테이블 보강
   │
   └── 0200c855  현재 root HEAD (재정렬 cycle Page 1 완료 상태)
```

## 5. V3 본편 11페이지

```text
V3 kick-off / V3 / V3U 본편
[████████████████████] 100%
11 / 11 완료
```

| Page | 내용 | 상태 |
|---:|---|---|
| 1 | V3 전환 전략 기준선 문서화 | 완료 |
| 2 | AGENTS / docs 진입점 연결 | 완료 |
| 3 | DB seed / 2U pyd 추론 재사용 원칙 정리 | 완료 |
| 4 | V3 worktree 생성 준비 | 완료 |
| 5 | V3 upstream 기준 ref 고정 | 완료 |
| 6 | V3 공식 업데이트 계획 확정 | 완료 |
| 7 | V3.0 ~ V3.18 공식 반영 | 완료 |
| 8 | V3U pyd 제거 경계 고정 | 완료 |
| 9 | V3U pyd-free 구현 | 완료 |
| 10 | V3U parity 감사 | 완료 |
| 11 | V3 / V3U handoff 및 2U_C backport 진입 | 완료 |

## 6. 2U_C V3 백포트 후속 진행

```text
2U_C V3 backport 후속 (BP 사이클 6건)
[████████████████████] 100% (30 / 30 sub-page 완료)
```

| Cycle | 내용 | 상태 | 진행률 |
|---|---|---|---:|
| BP-004A | 시스템로그 ANSI escape 제거 | 완료 | 100% |
| BP-004B | 재무정보 / 웹크롤링 숫자 파싱 보정 | 완료 | 100% |
| BP-004C | chart payload 길이 처리 | no-op 완료 | 100% |
| BP-002A | 차트 봉 폭 계산 보정 | 완료 | 100% |
| BP-002B | DB차트 상태 초기화 | 완료 | 100% |
| BP-002C | 실시간차트 x축 append 조건 | hold 완료 | 100% |

각 cycle은 `(읽기 전용 분석 → mapping 확인 → 적용 또는 no-op/hold 판정 → 검증 → 문서화)` 5 sub-page 단위로 진행된다.

## 7. 현재 진행 페이지 (재정렬 cycle 5 page)

```text
현재 cycle: 남은 2U_C V3 backport 후보 재정렬
현재 page: Page 1 / 5 완료
다음 page: Page 2 / 5
진행률: 20%

[████░░░░░░░░░░░░░░░░] 20%
```

| Page | 내용 | 상태 | 진행률 |
|---:|---|---|---:|
| 1 | 완료 / no-op / hold / 미진입 후보 inventory 확인 | 완료 | 100% |
| **2** | **BP-001 / BP-003 / BP-005 세부 위험도 확인** | **다음** | **0%** |
| 3 | 다음 safe micro-candidate 또는 종료 후보 선정 | 대기 | 0% |
| 4 | 선정 결과 root 문서 반영 | 대기 | 0% |
| 5 | commit / final guard / 다음 cycle 안내 | 대기 | 0% |

## 8. 백포트 적용 결과 매트릭스

| Backport ID | V3 근거 | 2U_C commit | root 추적 commit | 결과 | 변경 파일 |
|---|---|---|---|---|---|
| `2UC-V3-BP-004A` | V3.03 `3e67661b` | `e204e0f3` | `cf0de0dd` | 완료 | `ui/ui_update_textedit.py` |
| `2UC-V3-BP-004B` | V3.17 `f5975f4c` / V3.18 `7faec937` | `944bab37` | `e7cb4035` | 완료 | `utility/webcrawling.py` |
| `2UC-V3-BP-004C` | V3.03 `3e67661b` | 없음 | `e7beae54` | no-op | — |
| `2UC-V3-BP-002A` | V3.14 `f76222f8` | `f2f447d1` | `58ecac0f` | 완료 | `ui/ui_draw_chart_items.py` |
| `2UC-V3-BP-002B` | V3.03 `3e67661b` | `76329b3b` | `4579096d` | 완료 | `ui/ui_draw_chart_db.py` |
| `2UC-V3-BP-002C` | V3.03 `3e67661b` | 없음 | `0200c855` | hold | — |

## 9. no-op / hold 판정 기록

### 9.1 no-op

| 항목 | 판정 | 이유 |
|---|---|---|
| `2UC-V3-BP-004C` | no-op | 2U_C는 `coin` 인자를 포함한 7/9 chart payload를 유지하지만, V3.03 변경은 6/8 payload를 전제한다. |
| BP-002 crosshair 중복 방지 | no-op | 2U_C에 이미 `not (same_code and same_time)` 조건이 존재한다. |
| BP-005 BounceButton | no-op | 2U_C `ui/set_widget.py`에 이미 동일 기능이 구현되어 있다. |

### 9.2 hold

| 항목 | 판정 | 이유 |
|---|---|---|
| `2UC-V3-BP-002C` | hold | V3는 `same_code and not same_time`에서 x축 append를 수행하지만, 2U_C draw/update 계열은 대부분 `same_code and same_time`에서만 incremental update를 수행한다. |
| `2UC-V3-BP-004D` | hold | DB관리/progressbar 개선은 V3 DB/분석 시스템 전제가 섞여 있어 별도 설계가 필요하다. |
| `2UC-V3-BP-004E` | hold | 프로그램 종료 흐름은 V3 LS receiver 종료 구조와 섞여 있어 Kiwoom 유지 종료 계약 재검토가 필요하다. |
| BP-002 arrow index 음수화 | hold | V3 LS `market_gubun` 구조 의존성이 강하고 2U_C factor map 구조와 충돌할 수 있다. |
| BP-002 LS routing | hold | Kiwoom 유지 lane에 LS routing 조건을 직접 가져오면 안 된다. |
| HOLD-001 분석 시스템 확장 | hold | strategy 신규 구조 / 분석 DB / 설정 UI / runtime 전략 연산이 묶여 있다. |
| HOLD-002 DB 구조 개선 | hold | 거래소별 분리 / PRIMARY KEY / INSERT OR REPLACE는 기존 2U_C DB와 비호환 가능성이 크다. |

## 10. 미진입 후보 재검토 표 (Page 2 작업 대상)

| 후보 | 우선 | 구분 | 다음 확인 방향 | 위험 |
|---|:---:|---|---|---|
| `2UC-V3-BP-001` 백테스트 엔진 안정화 | 1 | 미진입 | V3 backtest 변경 중 broker-neutral / DB-neutral 소형 변경만 micro 후보화 | 2U_C custom 회귀 위험 큼 |
| `2UC-V3-BP-003` Binance/Upbit 안정화 | 2 | 미진입 | websocket 종료 / queue / 최초 tick 계산 중 LS 무관 부분만 후보화 | 실거래 runtime 영향 |
| `2UC-V3-BP-005` UI 버튼 / progress 표시 | 3 | 미진입 | BounceButton 제외, progressbar만 분리 후보화 | 거의 no-op 예상 |
| `2UC-V3-BP-004D` | hold | hold | V3 DB/분석 시스템 분리 설계 후 재검토 | 적용 금지 |
| `2UC-V3-BP-004E` | hold | hold | Kiwoom 종료 계약 분리 설계 후 재검토 | 적용 금지 |

## 11. 최신 commit 확인

### 11.1 `STOM_Version_2` 최신 10개

```text
0200c855 2U_C BP-002C hold 판정을 root 문서에 고정한다
4579096d 2U_C BP-002B 적용 이력을 root 문서에 고정한다
58ecac0f 2U_C BP-002A 적용 이력을 root 문서에 고정한다
e7beae54 2U_C BP-004C를 no-op 판정으로 고정한다
e7cb4035 2U_C BP-004B 적용 이력을 root 문서에 고정한다
cf0de0dd 2U_C BP-004A 적용 이력을 root 문서에 고정한다
542d5701 2U_C V3 백포트 Phase 11을 후보 선정으로 닫는다
96049642 2U_C V3 백포트 후보 allowlist를 고정한다
9cd88726 2U_C V3 백포트 진입 기준을 현재 상태에 맞춘다
c9dec9a4 V3와 V3U 전환 인수인계를 마무리한다
```

### 11.2 V3 lane 최신 5개 (`STOM_Version_3`)

```text
7faec937 STOM V3.18
f5975f4c STOM V3.17
66f90b1d STOM V3.16
bbc3fd1d STOM V3.15
f76222f8 STOM V3.14
```

### 11.3 V3U lane 전체 V3U 전용 4개 (`STOM_Version_3U`)

```text
4aef1cce V3U 최종 parity 감사 증적을 고정한다
3d8f9c1e V3U pyd 제거를 실제 코드 경계로 전환한다
d05c132c V3U pyd 대체 검증 발판을 먼저 세운다
c04faec0 V3U pyd 제거 경계를 먼저 고정한다
```

### 11.4 2U_C lane 최신 5개 (`STOM_Version_2U_C`)

```text
76329b3b 2U_C DB차트 상태 초기화를 보강한다
f2f447d1 2U_C 차트 봉 폭 계산을 마지막 간격 기준으로 보정한다
944bab37 2U_C 재무정보 숫자 파싱을 보정한다
e204e0f3 2U_C 시스템로그 색상 escape를 제거한다
baefe77b 2U_C pyd MainWindow 상태 계약을 주변 helper와 맞춘다
```

## 12. branch별 기준 이후 요약

| branch | 기준 이후 요약 | 현재 결론 |
|---|---|---|
| `STOM_Version_2` | V3 전략, V3/V3U handoff, 2U_C backport 추적 문서화 | root orchestration 정상 |
| `STOM_Version_3` | `STOM V3.0` ~ `STOM V3.18` 공식 반영 (19 commits) | 완료 |
| `STOM_Version_3U` | V3 기반 pyd-free 전환 + parity 감사 (4 commits) | 완료 |
| `STOM_Version_2U_C` | Kiwoom 유지 lane에 V3 기능 선별 backport (4 적용 + 1 no-op + 1 hold) | 진행 중 |

## 13. 다음 단계 OMC / PowerShell 명령

다음 작업은 `남은 후보 재정렬 Page 2 / 5`이다. 코드 변경이 아니라 위험도 검토 단계이므로 모든 명령은 읽기 전용이다.

### 13.1 Page 2 즉시 시작 (allowlist + hold 사유 다시 펼치기)

```powershell
omx sparkshell powershell -NoProfile -Command "
git -C C:\System_Trading\STOM\STOM_V status --short;
git -C C:\System_Trading\STOM\STOM_V grep -n -A 12 -e '### BP-001' -e '### BP-003' -e '### BP-005' -- docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md;
git -C C:\System_Trading\STOM\STOM_V grep -n -A 8 -e '2UC-V3-BP-004D' -e '2UC-V3-BP-004E' -- docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md;
git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short
"
```

### 13.2 BP-001 broker-neutral 후보 1차 스캔

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-3 log --oneline 06b70418..7faec937 -- backtest/
git -C C:\System_Trading\STOM\STOM_V.wt-3 show 7faec937 -- backtest/backengine_base.py
git -C C:\System_Trading\STOM\STOM_V.wt-dev grep -n "def " -- backtest/backengine_base.py
```

판단 기준: V3 변경 중 LS / DB / 분석 시스템 / pyd 와 결합되지 않은 함수 단위 변경만 micro 후보로 분리한다.

### 13.3 BP-003 Binance/Upbit broker-isolated 변경 추출

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-3 log --oneline 06b70418..7faec937 -- trade/binance/ trade/upbit/ trade/restapi_binance.py trade/restapi_upbit.py
git -C C:\System_Trading\STOM\STOM_V.wt-dev grep -nE "websocket|queue|Traceback" -- trade/restapi_binance.py trade/restapi_upbit.py
```

판단 기준: LS API와 공통 receiver 구조에 묶이지 않은 Binance/Upbit 전용 변경만 후보화한다.

### 13.4 BP-005 progressbar 단독 분리 또는 no-op 확정

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-3 show f76222f8 -- ui/create_widget/set_widget.py ui/update_widget/update_progressbar.py
git -C C:\System_Trading\STOM\STOM_V.wt-dev grep -n "BounceButton\|progressbar\|setValue" -- ui/set_widget.py ui/ui_update_textedit.py
```

판단 기준: BounceButton는 이미 존재하므로 no-op, progressbar 표시만 broker-neutral 단위로 분리 가능하면 후보화한다.

### 13.5 적용 시점 검증 게이트 (코드 변경 발생 시 필수)

```powershell
python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py
python C:\System_Trading\STOM\STOM_V\scripts\verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev
python -m py_compile <변경된 파일>
git -C C:\System_Trading\STOM\STOM_V.wt-dev diff --check
git -C C:\System_Trading\STOM\STOM_V.wt-dev diff --cached --check
```

`release sync preflight passed` 출력을 commit 전에 반드시 확인한다.

### 13.6 OMC 보조 명령 (선택)

| 목적 | 명령 |
|---|---|
| 사양 / 로그 / 평가 보조 컨텍스트 확장 | `/oh-my-claudecode:explore "BP-001 backtest broker-neutral 후보"` |
| 합의 기반 후보 선정 계획 | `/oh-my-claudecode:ralplan "남은 BP 재정렬 page 2~5"` |
| 코드 적용 시점 검증 게이트 | `/oh-my-claudecode:verify "BP-XXXX micro-candidate 적용 후 release sync"` |
| 적용 직전 비판적 리뷰 | `/oh-my-claudecode:critic "BP-XXXX 위험도와 회귀 가능성"` |
| 외부 문서 / 참고 자료 보강 | `/oh-my-claudecode:external-context "V3 backtest engine 변경 사양"` |

## 14. 남은 전체 단계 통합 테이블 (현재 → 종결)

| # | Cycle | Page | 항목 | 상태 | 진행률 | 실행 위치 |
|---:|---|---:|---|---|---:|---|
| 1 | 재정렬 | 1 | 완료 / no-op / hold / 미진입 inventory | 완료 | 100% | root |
| **2** | **재정렬** | **2** | **BP-001 / BP-003 / BP-005 세부 위험도 확인** | **다음** | **0%** | root + wt-3, wt-dev |
| 3 | 재정렬 | 3 | 다음 safe micro-candidate 또는 종료 후보 선정 | 대기 | 0% | root |
| 4 | 재정렬 | 4 | 선정 결과 root 문서 반영 | 대기 | 0% | root |
| 5 | 재정렬 | 5 | commit / final guard / 다음 cycle 안내 | 대기 | 0% | root |
| 6 | BP-001 | A | backtest broker-neutral micro 1건 추출 | 조건부 | 0% | wt-3 → wt-dev |
| 7 | BP-001 | A | py_compile + smoke + verify_release_sync 통과 | 조건부 | 0% | wt-dev |
| 8 | BP-001 | A | 2U_C commit + root 추적 commit | 조건부 | 0% | wt-dev → root |
| 9 | BP-003 | A | websocket 종료 / queue 보정 micro 1건 추출 | 조건부 | 0% | wt-dev |
| 10 | BP-003 | A | mock 검증 (실계정 호출 금지) + commit | 조건부 | 0% | wt-dev |
| 11 | BP-005 | – | progressbar 단독 분리 또는 no-op 확정 | 조건부 | 0% | wt-dev |
| 12 | 종결 | – | 모든 BP 큐 종료 / HOLD 항목 재확인 / 최종 handoff | 대기 | 0% | root |

조건부: Page 2 위험도 검토 결과에 따라 진입 여부가 결정된다. micro-candidate가 broker / DB / pyd-neutral 조건을 충족하지 않으면 hold로 종결한다.

## 15. 미래 작업을 더 잘하기 위한 운영 원칙

| 영역 | 원칙 | 위반 시 행동 |
|---|---|---|
| 브랜치 분리 | V3 공식 lane은 upstream `.pyd` 보존 / pyd 제거는 V3U 전용 | 즉시 revert |
| 3U_C 정책 | `STOM_Version_3U_C` 미생성 유지 | 만들지 말 것 |
| 백포트 단위 | 파일 단위 cherry-pick 금지, micro-candidate 단위 수동 이식만 허용 | 후보 분리 후 재시작 |
| Stage 정책 | `git add -A` 금지, 변경 파일 명시 add만 허용 | hunk 단위 stage 재구성 |
| Runtime 보호 | `_database`, `_log`, `*.db`, `backtest/graph/` stage 금지 | 즉시 unstage |
| 검증 게이트 | py_compile + git diff --check + verify_release_sync.py | 실패 시 commit 차단 |
| 결합 변경 차단 | LS / DB / pyd 결합 변경이 한 commit에 있으면 즉시 hold | 후보 재분리 |
| 문서 동기 | root와 active worktree 양쪽에 동일 checkpoint 미러 | 미러 누락 시 commit 보강 |
| 커밋 메타 | 한국어 본문, Constraint / Rejected / Confidence / Directive / Tested 라인 유지 | 본문 보강 후 amend 금지, 신규 커밋으로 보강 |
| 위험도 분리 | 위험도가 다른 변경을 한 후보에 묶지 않는다 | 후보 ID 분리 |

## 16. 다음 작업자가 즉시 읽어야 할 문서 우선순위

1. 이 문서 (`docs/update_log/2026-05-06_v3_2uc_backport_midpoint_checkpoint.md`)
2. `docs/update_log/2026-05-06_v3_v3u_final_handoff.md`
3. `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`
4. `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md`
5. `docs/V3_KICKOFF_READINESS_PLAN.md`
6. `docs/V3_UPDATE_OPERATING_SYSTEM.md`
7. `C:\System_Trading\STOM\STOM_V.wt-3u\docs\V3U_PYD_REMOVAL_PLAN.md`
8. `C:\System_Trading\STOM\STOM_V.wt-3u\docs\update_log\2026-05-06_v3u_final_parity_audit.md`
9. `CLAUDE.md`

## 17. 절대 유지할 원칙

- `STOM_Version_3U_C`는 아직 만들지 않는다.
- V3 공식 lane에는 upstream `.pyd`를 보존한다.
- V3 pyd 제거는 `STOM_Version_3U`에서만 수행한다.
- 2U_C는 V3 branch가 아니라 Kiwoom 유지 custom lane이다.
- 2U_C backport는 broker-neutral / DB-neutral / pyd-neutral micro-candidate만 우선한다.
- LS API 전제, DB migration 전제, chart payload 계약 변경은 별도 설계 전까지 hold한다.
- `git add -A`를 사용하지 않는다.
- `_database`, `_log`, `*.db`, `backtest/graph/`를 커밋하지 않는다.

## 18. 변경 이력

| 버전 | 일자 | 변경 사항 | 추적 commit |
|---|---|---|---|
| v1 | 2026-05-06 21:32 KST | root와 wt-dev에 동일 미러로 최초 작성 | `38894912` (root), `8182764e` (wt-dev) |
| v2 | 2026-05-06 (당일 내 보강) | 과거 타임라인, 통합 진행률 그래프, OMC 명령, 남은 전체 단계 테이블, 운영 원칙 분리 추가 | (이 commit) |
