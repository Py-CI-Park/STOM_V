# V3U V3.34 pyd-free 반영 완료 기록 (2026-06-29)

## 목적

`STOM_Version_3`에 공식 반영한 V3.34를 `STOM_Version_3U`에 pyd-free 방식으로 반영했다.

## 기준 범위

| 항목 | 값 |
| --- | --- |
| freshness 권원 | `https://github.com/devstom/STOM.git` `refs/heads/V3.00` (tip `c3db5f9c`) |
| upstream 경계 | `c3db5f9c` (2026-06-24 V3.34) |
| 반영 범위 | `bc23a067..c3db5f9c` |
| V3 formal | `25680a83 STOM V3.34` |
| V3U overlay commit | `e6dcab91` |
| V3U gate/test adjustment | pending commit (본 기록 커밋) |
| 제외 | runtime DB/log, upstream pyd 변경 없음 |

## V3.34 변경 (2026-06-24)

1. 해외주식 주문체결 데이터 처리 오류 수정
2. 바이낸스선물 감시종목제한 설정 추가
   - 100으로 설정 시 전일 거래대금순위 100개 종목만 감시
   - 미설정 시 700여개의 전체 종목 감시

## V3U 보정

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| runtime source | 보정 없음 | V3 공식 변경 12개 파일을 pyd-free lane에 순수 overlay |
| `ui/main_window.py` | 보정 없음 | 신규 `ui.X` 계약 없음, attr inventory `critical=0 warn=0` |
| `ui/main_window.pyd` | 유지 삭제 | V3.34 범위에 upstream pyd 변경 없음, V3U tracked `.pyd` 0건 유지 |
| `tests/v3u/test_data_layer.py` | 테스트 보정 | upstream V3.34가 `database_check.py`의 DB seed 상수를 함수 내부 local로 이동시켜 기존 module-level 상수 직접 검증이 깨짐. 공식 source를 수정하지 않고 tmp_path 격리 `database_check()` 실행 기반 검증으로 변경 |

## 검증 증거

```text
python -m pytest tests/v3u/test_data_layer.py -q
→ 6 passed

python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.34 --offline --log-dir .omx/logs/v3u
→ [OK] V3U offline structural smoke passed

python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.34 --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_2026-06-29_v334.json --log-dir .omx/logs/v3u
→ 8/8 stage PASS
  pytest gate 49 passed, attr inventory critical=0 warn=0
```

## 후속

- 3U_C lane은 `git merge STOM_Version_3U`로 따라잡기.
- 사용자 직접 테스트 시 확인 항목: 해외주식 주문체결 처리, 바이낸스선물 감시종목 제한 설정 저장/적용, V3.33 잔여 수동 항목(백테 시작·명언·타이틀바 색상).
