# Python 3.13 pyd-free 런타임 긴급 정렬 기록

## 배경

- 기록일: 2026-05-10
- 대상 브랜치: `STOM_Version_2U_C`
- 사용자 요청: V3가 Python 3.13 및 cp313 TA-Lib 기준으로 이동했으므로, pyd-free 유지 브랜치도 같은 64-bit 런타임으로 실행 가능하게 정렬한다.
- 공식 V2(`STOM_Version_2`)는 upstream `.pyd`/cp311 산출물을 보존해야 하므로 이번 3.13 긴급 정렬 대상에서 제외한다.

## 결정

- `STOM_Version_2U_C`의 64-bit 실행 배치(`stom*.bat`, `stom_backtest.bat`, `update_db_20260211.bat`)는 `C:\Python\64\Python31313\python.exe`를 명시적으로 사용한다.
- `pip_install_64.bat`는 Python 3.13.13 및 `utility\ta_lib-0.6.8-cp313-cp313-win_amd64.whl` 기준으로 설치한다.
- `requirements64.txt`는 V3 Python 3.13 런타임 패키지 기준에 2U 계열에서 필요한 `loguru`, `python-dateutil`, `pytz`, `tzlocal`을 포함한다.
- 32-bit `pip_install_32.bat`는 Kiwoom/레거시 32-bit 보조 경로가 남아 있어 이번 64-bit 3.13 정렬에서 제외한다.
- Python launcher `py`의 기본값이 `3.13t`(free-threaded)일 수 있으므로 배치에서는 `py`가 아니라 일반 3.13 실행 파일 절대 경로를 사용한다.

## 검증 결과

검증 시각: 2026-05-10 KST

- `C:\Python\64\Python31313\python.exe --version` → `Python 3.13.13`
- `C:\Python\64\Python31313\python.exe -m py_compile stom.py stom_backtest.py ui\ui_mainwindow.py utility\static.py utility\database_check.py` → 통과
- `C:\Python\64\Python31313\python.exe scripts\smoke_offline_gui.py --branch STOM_Version_2U_C --version V2.79 --offline --log-dir .omx\logs\py313` → 통과
- `C:\Python\64\Python31313\python.exe scripts\verify_pyd_gui_contract.py --branch STOM_Version_2U_C --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx\logs\py313\verify_pyd_gui_contract.json --log-dir .omx\logs\py313` → 통과
- `C:\Python\64\Python31313\python.exe scripts\verify_nonrelease_sync.py` → 통과
- `C:\Python\64\Python31313\python.exe -m pip install -r requirements64.txt` → 통과(모든 요구 패키지 충족)
- `C:\Python\64\Python31313\python.exe -c "import talib, PyQt5"` → 통과(`talib 0.6.8`)

## 이번 검증에서 확인된 이슈와 처리

- Python 3.13 환경에 `loguru`가 없어 2U smoke가 실패했던 원인을 확인했다. 2U_C `requirements64.txt`도 같은 3.13 기준으로 정렬했고 `loguru==0.7.3`을 명시했다.
- 오프라인 smoke 중 `키움매니저 실행 실패 - KHOPENAPI 호환 인터프리터 ... [no-candidate]` 로그가 남을 수 있다. 이는 `scripts\smoke_offline_gui.py`가 외부 프로세스 실행을 막기 위해 `resolve_stock_python = lambda: (None, [])`로 패치하는 검증 설계의 부산물이며, smoke/contract/nonrelease 검증은 모두 통과했다.
- Qt `createPlatformOpenGLContext` 및 font directory 경고가 stderr에 출력되었지만, 오프라인 GUI smoke와 pyd GUI contract는 모두 통과했다.

## 주의사항

- 오프라인 GUI smoke는 계좌/거래소 로그인 없이 가능한 범위의 실행 검증이다.
- 실제 Kiwoom/LS 로그인, 실거래, 장중 체결, 32-bit COM 경로는 별도 사용자 환경 검증이 필요하다.
