# V3U V3.35 pyd-free 반영 완료 기록 (2026-07-12)

## 목적

`STOM_Version_3`에 공식 반영한 V3.35를 `STOM_Version_3U`에 pyd-free 방식으로 반영했다.
V3.35 marker(`b27ae51c`) 이후 tail 4건(`1150bc99`, `01187d69`, `80412a0d`, `9d24b635`)이
upstream에 존재하여 함께 흡수했다.

## 기준 범위

| 항목 | 값 |
| --- | --- |
| freshness 권원 | `https://github.com/devstom/STOM.git` `refs/heads/V3.00` (tip `9d24b635`) |
| upstream 경계 | `9d24b635` (2026-07-11, V3.35 + tail) |
| 반영 범위 | `c3db5f9c..9d24b635` (12개 파일, +210/-139) |
| V3 formal | `c6ac10b2 STOM V3.35` |
| V3U overlay commit | `2fb212e2` |
| 제외 | runtime DB/log, upstream pyd 변경 없음 |

## V3.35 변경 (2026-07-07)

1. 바이낸스선물 정정주문 추가
2. LS증권을 통한 거래소 시장가 주문시 주문가격 오류 수정
3. 주문 예외 처리 강화

### 포함된 tail (2026-07-08 ~ 07-11)

| commit | 내용 |
| --- | --- |
| `1150bc99` | LS 주문체결 메시지 ordxctptncode 누락 방어 |
| `01187d69` | 풀 리퀘스트 병합 #38 |
| `80412a0d` | LS 주문체결 데이터 오류 처리 강화, 해외선물 체결/정정취소 데이터 처리 분리 |
| `9d24b635` | 주문체결 데이터 수신 처리 간소화 |

## V3U 보정: 없음 (순수 overlay)

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| trade/* 11개 파일 | 계약 무관 | worker/trader 프로세스 내부 변경, MainWindow 계약 영향 없음 |
| `ui/create_widget/set_dialog_etc.py` | 보정 불필요 | 기존 attr만 참조, attr inventory critical=0 warn=0 |
| `ui/main_window.pyd` | 해당 없음 | V3.35 범위에 upstream pyd 변경 없음, V3U tracked `.pyd` 0건 유지 |

## 검증 증거

```text
python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.35 --offline → [OK]
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.35
  --upstream-ref STOM_Version_3 --manifest .omx/logs/v3u/verify_2026-07-12_v335.json → 8/8 stage PASS
  pytest gate 49 passed, attr inventory critical=0 warn=0
```

## 후속

- 3U_C lane은 `git merge STOM_Version_3U`로 따라잡기.
- 사용자 직접 테스트 시 확인 항목: 바이낸스선물 정정주문, LS 시장가 주문가격,
  주문 예외 처리(LS/Upbit), 해외선물 체결/정정취소 분리 처리.
