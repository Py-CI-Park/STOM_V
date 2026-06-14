# V3U V3.33 pyd-free 반영 완료 기록 (2026-06-13)

## 목적

`STOM_Version_3`에 공식 반영된 V3.33을 `STOM_Version_3U`에 pyd-free로 반영했다.
직전 V3.32 흡수에서 제외했던 tail `fcc626a5`(윈도우 핸들 ctypes 수정)가 V3.33
범위에 포함되어 함께 정리됐다.

## 기준 범위

| 항목 | 값 |
| --- | --- |
| freshness 권원 | `https://github.com/devstom/STOM.git` `refs/heads/V3.00` (tip `bc23a067`) |
| upstream 경계 | `bc23a067` (2026-06-13 V3.33) |
| 반영 범위 | `68aa83f4..bc23a067` (V3.32 tail `fcc626a5` 포함) |
| V3 formal | `32991b24 STOM V3.33` |
| V3U commit | `3a1c1a93` |
| 제외 | upstream `ui/main_window.pyd`, runtime DB/log |

## V3.33 변경 (2026-06-13)

1. 전략탭 백테 시작 코드 별도 파일 분리 — `ui/event_click/button_clicked_stg_editer_bstart.py` 신규
2. 작업완료 명언리스트 별도 파일 분리 — `ui/create_widget/famous_saying.py` 신규
3. 백테 시작 코드 간소화
4. 명언 오타·맞춤법·투자명언 추가
5. 일부 프로세스 빌트인 print 삭제 + 콘솔 표시

## V3U 보정: 없음 (순수 overlay)

병렬 계약 분석 + 통합 게이트 attr inventory로 신규 `ui.X` 계약 0건 확정.

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| `button_clicked_stg_editer_bstart.py` (신규) | 보정 불필요 | `set_stg_tap.py`가 `*` import로 결선, 참조 attr(`market_infos`/`back_eques`/`shared_cnt`/`proc_backtester_*` 등)은 전부 기존 init |
| `ui.market_infos` (분석 false alarm) | 이미 커버 | `etc.py:133` `ui.market_infos = [...]` 외부 할당, V3.32에서 이미 26회 참조 — 게이트 critical=0 확정 |
| `famous_saying.py` (신규) | 계약 무관 | 순수 데이터 리스트, 여러 event_click이 import |
| 빌트인 print 삭제 (trade/backtest) | 계약 무관 | worker 프로세스 내부 변경, MainWindow 계약 영향 없음 |
| tail `fcc626a5` (winId ctypes) | 반영 완료 | `ui/etcetera/etc.py:change_title_bar_color` |

## 검증 증거

```text
python scripts/v3u_smoke_offline_gui.py --version V3.33 --offline → [OK]
python scripts/verify_v3u_pyd_gui_contract.py --version V3.33 → 8/8 stage PASS
  pytest gate 49 passed, attr inventory critical=0 warn=0
git ls-files *.pyd → empty
manifest: .omx/logs/v3u/verify_2026-06-13_v333.json
```

## 후속

- 3U_C lane은 `git merge STOM_Version_3U`로 따라잡기 (hop별 메커니즘 명문화 준수).
- 사용자 직접 테스트 시 확인 항목: 백테 시작(분리된 bstart 경로), 작업완료 명언
  표시, 타이틀바 색상(tail fcc626a5 — V3.32 미적용분 정리됨).
