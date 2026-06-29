# 2026-06-29 V3.34 흡수 재개 컨텍스트 및 upstream 확인

## 목적

직전 V3.33 완료 상태, 2026-06-29 upstream V3.00 확인 결과, 그리고 이번 세션의 V3.34 hop별 흡수 결과를 다음 작업자가 바로 이어받을 수 있도록 고정한다.

## 최종 lane 상태

| lane | branch | HEAD | origin 동기화 | 작업트리 상태 | 판정 |
|---|---|---:|---|---|---|
| V3 공식 | `STOM_Version_3` | `25680a83` | local ahead 1 | clean | V3.34 공식 반영 완료 |
| V3U | `STOM_Version_3U` | `e63d5b62` | local ahead 4 | `_database_backup_2026-05-22/`, `.gjc/` runtime state 존재 | V3.34 pyd-free 반영 및 3U_C cross-link 완료 |
| 3U_C | `STOM_Version_3U_C` | `3ec6dc66` | local ahead 6 | clean | V3.34 custom lane 흡수 완료 |

## 이전 작업 진행률 — V3.33

| 구분 | 작업 | 진행률 | 결과/근거 | 상태 |
|---|---|---:|---|---|
| V3 공식 | upstream V3.33 반영 | 100% | `32991b24 STOM V3.33` | 완료 |
| V3U | V3.33 pyd-free overlay | 100% | `3a1c1a93` | 완료 |
| V3U | V3.33 감사/기록 문서화 | 100% | `d5e14038`, `docs/update_log/2026-06-13_v3u_v333_pyd_free_update.md` | 완료 |
| 3U_C | V3U V3.33 흡수 merge | 100% | `705fb7fd` | 완료 |
| 3U_C | 사이클 6 기록 문서화 | 100% | `8c7f2d8f` | 완료 |
| V3U | 3U_C 흡수 cross-link 기록 | 100% | `34b49f77` | 완료 |
| 검증 | V3U/3U_C 자동 게이트 | 100% | V3U 8/8 PASS, 3U_C 8/8 PASS + tests/v3uc 32 | 완료 |

## 이번 작업 진행률 — V3.34

| 순서 | 작업 | 진행률 | 결과/근거 | 상태 |
|---:|---|---:|---|---|
| 1 | V3 공식 lane에 V3.34 반영 | 100% | `25680a83 STOM V3.34`, changed-path parity 일치, `ui/main_window.pyd` 보존 | 완료 |
| 2 | V3U lane에 V3.34 pyd-free 반영 | 100% | `e6dcab91` overlay + `a179f4bf` 기록/test + `bcbfc902` doc cleanup | 완료 |
| 2 | V3U 통합 게이트 | 100% | smoke OK, verify 8/8 PASS, pytest 49 passed, attr critical=0 warn=0 | 완료 |
| 3 | 3U_C lane에 V3.34 merge 반영 | 100% | merge `352a3838`, record `3ec6dc66`, 충돌 0 | 완료 |
| 3 | 3U_C 게이트 | 100% | verify 8/8 PASS, pytest 49 passed, tests/v3uc 32 passed, invariant diff allowlist only | 완료 |
| 4 | 사용자 직접 GUI 확인 | 0% | 해외주식 주문체결 처리, 바이낸스선물 감시종목제한 설정 저장/적용 등 | 사용자 수동 확인 필요 |
| 5 | V3U backup 디렉터리 정리 | 0% | `_database_backup_2026-05-22/` untracked 보존 중 | 사용자 데이터 판단 필요 |

## upstream V3.00 확인 결과

확인 명령:

```bash
git ls-remote --symref https://github.com/devstom/STOM.git HEAD refs/heads/V3.00 refs/tags/V3.0
git fetch https://github.com/devstom/STOM.git refs/heads/V3.00:refs/remotes/devstom_tmp/V3.00_latest
```

| 항목 | 값 |
|---|---|
| upstream HEAD | `refs/heads/V3.00` |
| upstream `refs/heads/V3.00` | `c3db5f9c3964b72c44e642426c11199c06cd6eef` |
| upstream `refs/tags/V3.0` | `d21e42425cfc6f2254431e8622b1bbf0dd89303e` |
| 이전 local V3 공식 최신 반영 | V3.33 (`32991b24`, upstream 경계 `bc23a067`) |
| upstream `_update.txt` top marker | `2026-06-24 V3.34` |
| 이번 반영 후 V3 공식 | V3.34 (`25680a83`, upstream 경계 `c3db5f9c`) |

## V3.34 upstream 버전 표

| 버전 | upstream 날짜 | upstream commit 범위 | upstream commit | 변경 요약 | 처리 상태 |
|---|---|---|---|---|---|
| V3.34 | 2026-06-24 | `bc23a067..c3db5f9c` | `934c4f26`, `213d5e4a`, `c3db5f9c` | 해외주식 주문체결 데이터 처리 오류 수정; 바이낸스선물 감시종목제한 설정 추가 | V3/V3U/3U_C 반영 완료 |

## V3.34 upstream `_update.txt` section

```text
2026-06-24 V3.34
1. 해외주식 주문체결 데이터 처리 오류 수정
2. 바이낸스선물 감시종목제한 설정 추가
- 100으로 설정 시 전일 거래대금순위 100개 종목만 감시
- 미설정 시 700여개의 전체 종목 감시
```

## 검증 증거

```text
# V3 official
changed-path parity against refs/remotes/devstom_tmp/V3.00_latest → clean
python -m py_compile <11 changed Python files> → pass
git ls-files "*.pyd" → ui/main_window.pyd

# V3U
python -m pytest tests/v3u/test_data_layer.py -q → 6 passed
python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.34 --offline --log-dir .omx/logs/v3u → OK
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.34 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_2026-06-29_v334_final.json --log-dir .omx/logs/v3u → 8/8 PASS

# 3U_C
python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U_C --version V3.34 --offline --log-dir .omx/logs/v3u → OK
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U_C --version V3.34 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_3uc_2026-06-29_v334.json --log-dir .omx/logs/v3u → 8/8 PASS
python -m pytest tests/v3uc -q → 32 passed
```

## 다음 안내 대상

| 번호 | 항목 | 안내 |
|---:|---|---|
| 4 | 사용자 직접 GUI 확인 | 해외주식 주문체결 처리, 바이낸스선물 감시종목제한 설정 저장/적용, V3.33 잔여 항목(백테 시작·명언·타이틀바 색상)을 실제 GUI에서 확인 |
| 5 | V3U backup 디렉터리 정리 | `_database_backup_2026-05-22/`는 사용자/runtime 백업으로 보존 중이다. 삭제·이동은 사용자 판단 후 별도 처리 |
