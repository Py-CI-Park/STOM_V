# V3U V3.19~V3.29 pyd-free 반영 완료 기록 (2026-05-27)

## 목적

`STOM_Version_3`에 공식 반영된 V3.19~V3.29 변경을 `STOM_Version_3U`에 순차 반영했다. V3U lane 불변식에 따라 upstream `ui/main_window.pyd`는 추적하지 않고, V3U의 `ui/main_window.py` pyd-free 추론/어댑터 계약을 유지했다.

## 기준 범위

| 항목 | 값 |
| --- | --- |
| 공식 V3 worktree | `C:/System_Trading/STOM/STOM_V.wt-3` |
| 공식 V3 branch/head | `STOM_Version_3` / `3d4390ea STOM V3.29` |
| V3U worktree | `C:/System_Trading/STOM/STOM_V.wt-3u` |
| V3U branch/head | `STOM_Version_3U` / `e24918cd` 이후 본 문서 커밋 |
| 제외 범위 | V3.29 tail `f6fd482c..5286cde6`, runtime `_database`, `_log`, `*.db`, upstream `.pyd` |

## 순차 반영 커밋

| Version | V3 source range | V3 formal commit | V3U commit | pyd 처리 | 주요 V3U 보정 |
| --- | --- | --- | --- | --- | --- |
| V3.19 | V3 formal delta | `57511f89` | `3faa9be7` | 제외/계약 유지 | 기존 V3U pyd-free wrapper 유지 |
| V3.20 | V3 formal delta | `3340f0e2` | `8a8e26b0` | 제외/계약 유지 | 기존 V3U pyd-free wrapper 유지 |
| V3.21 | V3 formal delta | `bf16768e` | `3c37482d` | 제외/계약 유지 | 기존 V3U pyd-free wrapper 유지 |
| V3.22 | V3 formal delta | `2b0c0555` | `57159a9c` | 제외/계약 유지 | 기존 V3U pyd-free wrapper 유지 |
| V3.23 | V3 formal delta | `f0bef5d3` | `41e401e5` | 제외/계약 유지 | 기존 V3U pyd-free wrapper 유지 |
| V3.24 | `96822b73..75a7fa45` / local `f0bef5d3..22782984` | `22782984` | `be593744` | 제외/계약 유지 | `database_check` 모듈 레벨 기본 상수 노출 복구 |
| V3.25 | `22782984..468755b8` | `468755b8` | `9f854d61` | 변경 없음 | staged py_compile + V3U targeted pytest 통과 |
| V3.26 | `468755b8..134f57d6` | `134f57d6` | `d3c817bc` | 변경 없음 | staged py_compile + V3U targeted pytest 통과 |
| V3.27 | `134f57d6..995dee34` | `995dee34` | `dfdbbde7` | `ui/main_window.pyd` 제외 | V3U contract/attr inventory 통과 |
| V3.28 | `995dee34..812c1280` | `812c1280` | `ee3fbab2` | `ui/main_window.pyd` 제외 | `database_check` 상수 노출, V3U 기본 설정 Telegram/팩터선택 보강, 다크레드 `color_hv_bt` 보강 |
| V3.29 | `812c1280..3d4390ea` | `3d4390ea` | `e24918cd` | `ui/main_window.pyd` 제외 | `database_check` 상수 노출, `ui.tts_sound` placeholder 계약 노출, `ui/_icon/logo.png` 삭제 반영 |

## pyd-free 처리 원칙

- `git ls-files *.pyd` 결과가 비어 있도록 유지했다.
- upstream `ui/main_window.pyd` 변경(V3.27~V3.29)은 직접 반영하지 않고 `scripts/verify_v3u_pyd_gui_contract.py`의 upstream pyd evidence와 attr inventory로 계약만 검증했다.
- `ui/main_window.py`는 V3U 소유 pyd-free replacement로 유지했다.
- V3U 보호 경로(`scripts/v3u_*`, `scripts/verify_v3u_*`, `tests/v3u/**`, V3U update_log 등)는 공식 delta overlay 대상에서 제외했다.

## 검증 증거

최종 HEAD 기준으로 아래를 재실행했다.

```text
python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.29 --offline --log-dir .omx/logs/v3u
→ [OK] V3U offline structural smoke passed

python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.29 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/v3u_contract_manifest_final_V3_29.json --log-dir .omx/logs/v3u
→ 8/8 stages PASS, pytest gate 46 passed, attr inventory critical=0 warn=0

python -m pytest tests/v3u --tb=short -q
→ 46 passed, 3 warnings

git ls-files *.pyd
→ empty

git status --short --untracked-files=all
→ only ?? _database_backup_2026-05-22/en_key.txt
```

## 남은 리스크 / 후속 작업

- `tts_sound`는 V3.29 계약상 `ui.tts_sound`를 요구하지만, Supertonic TTS는 자동 다운로드/외부 런타임 부작용 가능성이 있어 V3U `main_window.py`에서는 우선 `_NullWorker` placeholder로 노출했다. 실제 TTS 재생 활성화는 별도 런타임 검증 후 진행한다.
- 검증은 offline structural smoke와 V3U contract/pytest 중심이다. 실제 GUI 조작, Supertonic 음성 재생, 실거래 API 연결은 수행하지 않았다.
- `_database_backup_2026-05-22/en_key.txt`는 기존 untracked runtime backup으로 유지했고 커밋하지 않았다.
