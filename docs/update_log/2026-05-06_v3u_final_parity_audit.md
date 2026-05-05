# V3U 최종 parity audit

작성일: 2026-05-06  
대상 worktree: C:\System_Trading\STOM\STOM_V.wt-3u  
대상 branch: STOM_Version_3U  
비교 기준 branch: STOM_Version_3

## 1. 감사 목적

이 문서는 STOM_Version_3U가 STOM_Version_3에서 분기된 pyd-free lane으로 유지되고 있는지 최종 확인하기 위한 감사 기록이다.

핵심 질문은 다음과 같다.

1. STOM_Version_3 공식 lane의 upstream 파일과 .pyd가 보존되어 있는가?
2. STOM_Version_3U에서는 .pyd가 제거되고 Python 대체 파일만 추가되었는가?
3. STOM_Version_2U의 pyd 추론 산출물은 참고 자료로만 사용되고, V2/Kiwoom 전용 구현이 3U에 섞이지 않았는가?
4. _database, _log, *.db 같은 runtime 파일이 git에 추적되지 않는가?
5. 아직 만들지 않기로 한 STOM_Version_3U_C branch가 생성되지 않았는가?

## 2. 기준 ref

| 구분 | ref | commit |
|---|---|---|
| V3 공식 기준 | STOM_Version_3 | $v3Short / $v3Head |
| V3U 감사 대상 구현 HEAD | STOM_Version_3U | $v3uShort / $v3uHead |

감사 대상 구현 HEAD는 pyd-free 구현 커밋 V3U pyd 제거를 실제 코드 경계로 전환한다까지이다. 이 문서 자체는 최종 감사 증적을 남기기 위한 문서-only 후속 커밋으로 추가된다.

## 3. V3U 전용 커밋 목록

`	ext
3d8f9c1e V3U pyd 제거를 실제 코드 경계로 전환한다
d05c132c V3U pyd 대체 검증 발판을 먼저 세운다
c04faec0 V3U pyd 제거 경계를 먼저 고정한다
`

## 4. 감사 전 diff 목록

STOM_Version_3...STOM_Version_3U 기준 감사 전 diff는 아래 6개 파일로 제한되었다.

`	ext
A	docs/V3U_PYD_REMOVAL_PLAN.md
A	scripts/v3u_gui_contract_manifest.py
A	scripts/v3u_smoke_offline_gui.py
A	scripts/verify_v3u_pyd_gui_contract.py
A	ui/main_window.py
D	ui/main_window.pyd
`

허용 의미는 다음과 같다.

| 파일 | 판정 | 사유 |
|---|---|---|
| docs/V3U_PYD_REMOVAL_PLAN.md | 허용 | V3U pyd 제거 계획/금지선 문서 |
| scripts/v3u_gui_contract_manifest.py | 허용 | V3U GUI contract inventory 도구 |
| scripts/v3u_smoke_offline_gui.py | 허용 | pyd-free 구조 smoke 도구 |
| scripts/verify_v3u_pyd_gui_contract.py | 허용 | pyd-free contract verifier |
| ui/main_window.py | 허용 | ui.main_window.MainWindow Python 대체 entry |
| ui/main_window.pyd | 허용 | V3U에서 제거해야 하는 upstream pyd |

이 문서가 커밋된 뒤에는 docs/update_log/2026-05-06_v3u_final_parity_audit.md가 감사 증적 문서로 추가되는 것이 유일한 추가 허용 diff다.

## 5. 2U 추론 py 참고 경계

사용자 전략상 STOM_Version_2U의 pyd 추론 결과는 V3U pyd 제거의 중요한 참고 자료다. 이번 3U 구현에서도 다음 관점은 2U의 추론 py에서 참고했다.

- MainWindow.__init__가 책임지는 runtime state의 범위
- queue, process handle, chart 상태값 초기화 방식
- pyd 내부 slot/wrapper가 Python event module과 연결되는 구조
- widget builder 호출 순서와 pyd-free 검증 관점

단, 2U 파일을 3U로 그대로 복사하지 않았다. 3U의 base는 반드시 STOM_Version_3이어야 하며, V3는 LS API 전환 등 공식 구조 변화가 있으므로 V2/Kiwoom 전용 구현을 직접 이식하면 lane 경계가 무너진다. 따라서 현재 ui/main_window.py는 2U를 참고 자료로 삼되, V3의 ui/create_widget, ui/update_widget, ui/draw_chart, ui/etcetera 구조에 맞춰 새로 작성한 Python entry다.

감사 중 추가/변경된 텍스트 파일에서 Kiwoom, 키움, KHOPENAPI, kiwoom_manager, stock_manager, OpenAPI marker를 검색했다. 코드 파일에서는 V2/Kiwoom 구현 marker가 발견되지 않았고, 문서의 금지사항 설명에만 Kiwoom 문구가 존재한다.

## 6. 실행 검증

아래 검증을 통과했다.

`powershell
python -m py_compile ui\main_window.py scripts\v3u_gui_contract_manifest.py scripts\v3u_smoke_offline_gui.py scripts\verify_v3u_pyd_gui_contract.py
python scripts\v3u_gui_contract_manifest.py --root . --output .omx/logs/v3u/contract_inventory_final_parity_audit.json
python scripts\v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.18 --offline --log-dir .omx/logs/v3u
python scripts\verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.18 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_v3u_pyd_gui_contract_final_parity_audit.json --log-dir .omx/logs/v3u
git ls-files '*.pyd'
git ls-files '_database/*' '_log/*' '*.db'
git branch --list STOM_Version_3U_C
`

결과 요약:

- py_compile 통과
- V3U GUI contract inventory 생성 통과
- V3U offline structural smoke 통과
- V3U pyd GUI contract verifier 통과
- STOM_Version_3U tracked .pyd 없음
- _database, _log, *.db tracked 파일 없음
- STOM_Version_3U_C branch 없음
- STOM_Version_3에는 upstream ui/main_window.pyd가 보존됨

## 7. 판정

최종 parity audit 기준에서 STOM_Version_3U는 STOM_Version_3 대비 V3U pyd-free 목적의 차이만 가진 상태로 판정한다.

다음 페이지에서는 code 변경이 아니라 전체 전환 상태를 인수인계 문서/보고 형태로 정리한다.

## 8. 남은 위험과 주의사항

- 현재 검증은 import/AST/contract/smoke 중심의 구조 검증이다.
- 실제 PyQt GUI 클릭 흐름, 거래 프로세스 실행, 실계좌/모의투자 runtime은 별도 안전 환경에서 검증해야 한다.
- _database seed는 runtime 자료이며 커밋하지 않는다.
- STOM_Version_3U_C는 아직 만들지 않는다.
- 다음 수정자는 3U에서 V3 공식 runtime 파일을 임의로 수정하기 전에 반드시 STOM_Version_3과의 허용 diff를 먼저 재확인해야 한다.
