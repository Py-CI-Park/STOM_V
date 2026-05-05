# V3/V3U 전환 최종 인수인계 보고서

작성일: 2026-05-06  
작성 위치: C:\System_Trading\STOM\STOM_V / STOM_Version_2  
참조 worktree: C:\System_Trading\STOM\STOM_V.wt-3, C:\System_Trading\STOM\STOM_V.wt-3u

## 1. 결론

V3 전환 kick-off부터 V3 공식 ingress, V3U pyd-free 분기, pyd 제거 구현, 최종 parity audit까지 완료되었다.

현재 기준 판정은 다음과 같다.

- STOM_Version_3는 V3 공식 업데이트 lane으로 STOM V3.18까지 반영된 상태다.
- STOM_Version_3U는 STOM_Version_3에서 분기된 pyd-free lane이며, tracked .pyd가 없다.
- STOM_Version_3U와 STOM_Version_3의 차이는 V3U pyd-free 계획/검증 도구/감사 문서와 ui/main_window.py 대체, ui/main_window.pyd 삭제로 제한된다.
- _database, _log, *.db runtime 파일은 추적하지 않는다.
- STOM_Version_3U_C는 만들지 않았다.

## 2. 현재 worktree 지도

`	ext
STOM_V/          -> STOM_Version_2       # V2 공식 유지/오케스트레이션 문서 위치, HEAD 0a2d7fa1
STOM_V.wt-2u/    -> STOM_Version_2U      # V2 pyd-free 유지
STOM_V.wt-dev/   -> STOM_Version_2U_C    # Kiwoom 유지 custom/backport lane
STOM_V.wt-3/     -> STOM_Version_3       # V3 공식 ingress, HEAD 7faec937
STOM_V.wt-3u/    -> STOM_Version_3U      # V3 pyd-free, HEAD 4aef1cce
STOM_V.wt-2uc/   -> integration archive  # active lane 아님
`

## 3. V3 공식 상태

- worktree: C:\System_Trading\STOM\STOM_V.wt-3
- branch: STOM_Version_3
- HEAD: $v3Head STOM V3.18
- 역할: V3 upstream 공식 파일 반영 lane
- 원칙: upstream .pyd 보존
- 현재 상태: clean

V3 공식 lane은 pyd-free 작업 대상이 아니다. 공식 V3에는 upstream ui/main_window.pyd가 보존되어야 하며, pyd 제거 구현은 3U에서만 수행한다.

## 4. V3U pyd-free 상태

- worktree: C:\System_Trading\STOM\STOM_V.wt-3u
- branch: STOM_Version_3U
- HEAD: $v3uHead V3U 최종 parity 감사 증적을 고정한다
- 역할: V3에서 분기한 pyd-free lane
- 현재 상태: clean
- tracked .pyd: 없음
- runtime DB/log tracked 파일: 없음

V3U 전용 커밋:

`	ext
4aef1cce V3U 최종 parity 감사 증적을 고정한다
3d8f9c1e V3U pyd 제거를 실제 코드 경계로 전환한다
d05c132c V3U pyd 대체 검증 발판을 먼저 세운다
c04faec0 V3U pyd 제거 경계를 먼저 고정한다
`

## 5. V3U와 V3의 최종 diff

`	ext
A	docs/V3U_PYD_REMOVAL_PLAN.md
A	docs/update_log/2026-05-06_v3u_final_parity_audit.md
A	scripts/v3u_gui_contract_manifest.py
A	scripts/v3u_smoke_offline_gui.py
A	scripts/verify_v3u_pyd_gui_contract.py
A	ui/main_window.py
D	ui/main_window.pyd
`

허용 의미:

| 파일 | 의미 |
|---|---|
| docs/V3U_PYD_REMOVAL_PLAN.md | V3U pyd 제거 계획/금지선 |
| docs/update_log/2026-05-06_v3u_final_parity_audit.md | V3U vs V3 최종 parity audit 증적 |
| scripts/v3u_gui_contract_manifest.py | GUI contract inventory 도구 |
| scripts/v3u_smoke_offline_gui.py | pyd-free structural smoke 도구 |
| scripts/verify_v3u_pyd_gui_contract.py | pyd GUI contract verifier |
| ui/main_window.py | V3U용 Python MainWindow 대체 entry |
| ui/main_window.pyd | V3U에서 제거된 upstream pyd |

## 6. 2U 추론 py 참고 원칙

사용자 아이디어대로 STOM_Version_2U의 pyd 추론 py는 3U pyd 제거 작업의 중요한 참고 자료로 사용했다.

다만 실제 적용 방식은 다음과 같이 제한했다.

- 3U base는 반드시 STOM_Version_3이다.
- 2U의 추론 py는 구조/속성/초기화 흐름 참고 자료다.
- 2U 파일을 3U에 그대로 복사하지 않는다.
- V2/Kiwoom 전용 구현을 V3U에 섞지 않는다.
- 3U의 ui/main_window.py는 V3의 ui/create_widget, ui/update_widget, ui/draw_chart, ui/etcetera 구조에 맞춘 Python entry다.

이 판단은 3U 커밋과 최종 audit 문서에 함께 기록했다.

## 7. 검증 증거

최종 인수인계 직전 아래 검증을 재실행했다.

`powershell
python -m py_compile ui\main_window.py scripts\v3u_gui_contract_manifest.py scripts\v3u_smoke_offline_gui.py scripts\verify_v3u_pyd_gui_contract.py
python scripts\v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.18 --offline --log-dir .omx/logs/v3u
python scripts\verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.18 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_v3u_pyd_gui_contract_final_handoff.json --log-dir .omx/logs/v3u
git ls-files '*.pyd'
git ls-files '_database/*' '_log/*' '*.db'
git branch --list STOM_Version_3U_C
`

결과 요약:

`	ext
[OK] V3U offline structural smoke passed
[OK] V3U pyd GUI contract passed
[OK] no tracked .pyd in V3U
[OK] no tracked runtime DB/log/db files in V3U
[OK] no STOM_Version_3U_C branch
`

## 8. 생성/갱신된 주요 문서

Root/orchestration 쪽:

- docs/V3_UPDATE_OPERATING_SYSTEM.md
- docs/V3_KICKOFF_READINESS_PLAN.md
- docs/update_log/2026-05-04_v3_transition_strategy_review.md
- docs/update_log/2026-05-06_v3_v3u_final_handoff.md ← 이 문서

V3U 쪽:

- docs/V3U_PYD_REMOVAL_PLAN.md
- docs/update_log/2026-05-06_v3u_final_parity_audit.md

## 9. 남은 위험

1. 현재 검증은 구조 검증 중심이다.
   - import/AST/py_compile/smoke/contract verifier는 통과했다.
   - 실제 PyQt GUI 클릭 흐름은 별도 검증이 필요하다.

2. 거래 runtime 검증은 수행하지 않았다.
   - 실계좌/모의투자/API 연결은 안전 환경에서 별도 수행해야 한다.

3. V3 upstream이 추가 업데이트되면 3U도 다시 따라가야 한다.
   - V3 공식 업데이트를 먼저 반영한다.
   - 그 뒤 3U에서 pyd-free 차이를 재검증한다.

4. STOM_Version_3U_C는 아직 만들지 않는다.
   - custom lane이 필요한 시점까지 3U_C 생성 금지선을 유지한다.

## 10. 다음 작업자가 바로 해야 할 일

다음 세션/다음 agent는 먼저 아래를 읽는다.

1. AGENTS.md
2. docs/V3_UPDATE_OPERATING_SYSTEM.md
3. docs/V3_KICKOFF_READINESS_PLAN.md
4. docs/update_log/2026-05-04_v3_transition_strategy_review.md
5. C:\System_Trading\STOM\STOM_V.wt-3u\docs\V3U_PYD_REMOVAL_PLAN.md
6. C:\System_Trading\STOM\STOM_V.wt-3u\docs\update_log\2026-05-06_v3u_final_parity_audit.md
7. 이 문서

후속 작업 추천 순서:

1. 3U에서 실제 GUI smoke를 안전한 offscreen/개발 환경에서 확장한다.
2. ui/main_window.py의 guarded legacy slot fallback 호출 기록을 확인한다.
3. 필요한 경우 fallback을 명시적 wrapper로 승격한다.
4. V3 upstream이 추가되면 STOM_Version_3에 공식 업데이트를 먼저 반영한다.
5. 그 뒤 STOM_Version_3U에 pyd-free 차이를 재적용/검증한다.
6. 2U_C에는 V3 기능을 선별 backport하되, LS 전환 자체를 Kiwoom 유지 lane에 무리하게 섞지 않는다.

## 11. 금지선 재확인

- STOM_Version_3의 upstream pyd를 제거하지 않는다.
- STOM_Version_3U_C를 아직 만들지 않는다.
- _database, _log, *.db를 커밋하지 않는다.
- 2U_C/Kiwoom custom을 3U에 섞지 않는다.
- 2U 추론 py는 참고 자료이며 3U의 base가 아니다.
- 공식 V3 업데이트와 3U pyd-free 보정은 별도 커밋/별도 검증으로 유지한다.
