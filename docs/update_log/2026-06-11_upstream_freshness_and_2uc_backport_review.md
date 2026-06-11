# 업스트림 신선도 점검 (V2/V3) + V3.30~V3.32 흡수 + 2U_C 백포트 상세 검토 (2026-06-11)

본 문서는 `STOM_V`(V2 release-ingress lane)와 `STOM_V.wt-3u`(V3U lane)에 동시 커밋되는 공용 검토 기록이다.

## 1. V2 lane 신선도 점검 결과: 반영분 없음

| 항목 | 값 |
| --- | --- |
| freshness 권원 | `https://github.com/devstom/STOM.git` `refs/tags/V2.0` |
| upstream tag hash | `873d51ee` (docs/UPSTREAM_SYNC_STRATEGY.md 기록과 일치) |
| upstream `_update.txt` head | `2026-04-08 V2.79` |
| 로컬 `STOM_V` `_update.txt` head | `2026-04-08 V2.79` (동일) |
| 판정 | **V2 신규 공식 업데이트 없음 — V2→2U→2U_C 전파 사유 없음** |

## 2. V3 lane 신선도 점검 결과: V3.30~V3.32 신규 발견·흡수 완료

### 2.1 freshness 권원 정정 사항

- `refs/tags/V3.0`은 `2026-04-23 V3.08`(`d21e4242`)에서 멈춘 **stale tag**다.
- 실 V3 개발은 `refs/heads/V3.00`에서 진행 중이며, 점검 시점 tip은
  `fcc626a5` (2026-06-11, `_update.txt` head `2026-06-11 V3.32`)다.
- `docs/UPSTREAM_SYNC_STRATEGY.md`의 "V3 wave source 후보: refs/tags/V3.0"은
  향후 `refs/heads/V3.00` 기준으로 갱신이 필요하다 (후속 권고 §4-4).

### 2.2 버전 경계와 흡수 커밋

| Version | upstream 경계 | V3 formal (wt-3) | V3U pyd-free (wt-3u) | 주요 내용 |
| --- | --- | --- | --- | --- |
| V3.30 (2026-05-27) | `d5fbdc87` | `a488af5d` | `9459a422` | 베이스 리시버 속도 최적화, 업비트 웹소켓 핑 옵션, 모든 웹소켓 강제 종료, 리시버 시간 형변환 수정 (V3.29 tail 웹소켓 안전 종료 4건 포함) |
| V3.31 (2026-05-28) | `8392669d` | `b9cdcd99` | `83be2de0` | 야간선물 일자 변경 확인 시간 증가, 업비트 체결 필터 수정, 국내주식/지수선물 장마감 초기 설정, 실시간 시간 필터 수정 |
| V3.32 (2026-06-11) | `68aa83f4` | `3dea3b94` | `1da630da` | 당일DB→일자DB append, 업비트 첫틱 당일매수/매도금액 수정, 홈탭 마우스오버, tts 윈도우 기본 전환(supertonic 삭제), 라이브러리 갱신 |

- tail 제외: `fcc626a5` "윈도우 핸들 값이 너무 커서 발생하는 오류 수정"
  (`ui/etcetera/etc.py:271` `int(window.winId())` → `ctypes.c_void_p(...)`, bump 이후 1건).
  V3.29 tail 제외 선례와 동일하게 다음 버전 흡수 시 포함한다.
- wt-3 parity 검증: V3.32 formal commit 후 `git diff HEAD 68aa83f4`가 lane-local
  문서(docs/, CLAUDE.md, AGENTS.md, .gitignore) 외 완전 일치.
- V3U 검증: 버전별 offline smoke + 통합 게이트 8/8 PASS (최종 pytest 49,
  attr inventory critical=0). V3.32에서 게이트가 신규 계약 `ui.homepg`
  (홈탭 마우스오버) 누락을 CRITICAL drift로 사전 차단 → V3U 보정 후 PASS.

## 3. 2U_C (STOM_Version_2U_C) 백포트 후보 상세 검토

### 3.1 검토 시점 2U_C 상태

- `STOM_V.wt-dev`는 현재 기능 브랜치
  `lazycodex/tick-sparse-positive-generation-improvement-20260604` (HEAD `0244cb7e`)
  체크아웃 상태로 개별 기능(tick sparse positive generation) 개발 중이다.
- V2 upstream 신규가 없으므로(§1) 공식 전파(V2→2U→2U_C) 사유는 없다.
- 아래 후보는 **V3 lane 선별 백포트**(STOM_V `4cc2654f` "V3 후보 인벤토리와 선별
  백포트" 운영 패턴)의 차기 입력이다.

### 3.2 항목별 검토 표

| # | V3 변경 (버전) | 2U_C 대응 surface | 판정 | 근거 |
| --- | --- | --- | --- | --- |
| 1 | 업비트 첫틱 당일매수/매도금액 수정 (V3.32) | `trade/upbit/upbit_receiver_tick.py` (당일매수금액 로직 존재) | 🟢 **백포트 후보 1순위** | 0시 정각 전일 매수/매도수량 수신 무시 — 2U_C 업비트 실시간 수집 사용 시 동일 결함 가능. 수정 범위 작고 데이터 정합 직결 |
| 2 | 웹소켓 종료 안전화·강제 종료·핑 옵션 (V3.29 tail + V3.30) | `utility/kimp_upbit_binance.py` (websockets.connect ping_interval=60 기존재), upbit 자체 웹소켓 모듈 | 🟡 **검토 후보** | 2U_C kimp는 ping_interval 이미 설정. 종료 안전화(스레드 락 경쟁 방지)는 2U_C 종료 시 잔여 traceback 관찰 시 채택 |
| 3 | 리시버 시간 형변환 오류 수정 (V3.30) | `trade/upbit/`·`trade/stock_korea/` receiver | 🟡 **검토 후보** | V3 베이스 리시버 구조(상속)와 2U_C 분리 파일 구조가 달라 라인 단위 이식 불가 — 증상(시간 형변환) 기준 대조 필요 |
| 4 | 국내주식 장마감 시간 초기 설정 (V3.31) | `trade/stock_korea/` + 설정 기본값 | 🟡 **검토 후보** | 2U_C 국내주식 lane 사용 중이면 기본값 비교 1회로 판정 가능 |
| 5 | 야간선물/지수선물 관련 수정 (V3.31) | 해당 없음 | ⚪ 해당 없음 | wt-dev `trade/`에 국내 선물(future) lane 부재 (binance/future_oversea/stock_korea/upbit만 존재) |
| 6 | 베이스 리시버 속도 최적화 (V3.30) | 구조 상이 | ⚪ 보류 | V3 전용 클래스 구조 최적화 — 2U_C는 V3K safe-staged 기준(STOM_V `adfe80c7`)으로 별도 평가 |
| 7 | tts 윈도우 기본 전환 (V3.32) | 해당 없음 | ⚪ 해당 없음 | 2U_C 소리는 `utility/chart_hoga_query_sound.py` (V2 구조) — supertonic 도입 이력 자체가 없음 |
| 8 | 홈탭 마우스오버·읽기속도 설정 (V3.32) | 해당 없음 | ⚪ 해당 없음 | V3 UI 전용 |
| 9 | 당일DB→일자DB append 전환 (V3.32) | DB 관리 도구 | 🟡 **검토 후보** | 야간선물 일자 중복이 원인 — 2U_C는 야간선물 lane이 없어 긴급도 낮음. DB 자동 관리 사용 시 동작 차이만 확인 |
| 10 | 윈도우 핸들 ctypes 수정 (tail `fcc626a5`) | 동일 함수 없음. 유사 패턴 `ui/ui_draw_chart_db.py:127` `win32gui.SetForegroundWindow(int(self.ui.winId()))` | ⚪ 관찰 항목 | 2U_C에 `change_title_bar_color` 부재. win32gui 경로는 핸들 크기 이슈 보고 시 재검토 |

### 3.3 반영 방식 권고

1. **즉시 코드 반영은 보류한다.** wt-dev가 기능 브랜치 개발 중이므로, 백포트는
   기능 브랜치 정리(머지 또는 보류 판단) 후 `STOM_Version_2U_C` 위에서 별도
   사이클로 진행한다 (V3K safe-staged 기준 적용).
2. 1순위 후보(#1 업비트 첫틱)는 다음 2U_C 사이클 시작 시 가장 먼저
   `upbit_receiver_tick.py` 당일매수/매도금액 경로를 V3.32 diff(`07a7a79e`,
   `567f60cb`)와 대조한다.
3. 🟡 후보(#2·#3·#4·#9)는 증상 관찰 또는 기본값 1회 대조로 채택/기각을 확정하고
   `docs/CARRY_FORWARD_REGISTRY.md`에 결과를 기록한다.

## 4. 후속 권고

1. V3U lane: 사용자 직접 테스트 B1에 V3.30~32 효과 확인 항목 추가
   (홈탭 마우스오버, 알림소리 TTS 윈도우 음성, 읽기속도 설정 탭).
2. V3 다음 흡수 시 tail `fcc626a5` 포함 (V3.33 또는 차기 wave).
3. 2U_C 백포트 사이클은 §3.3 순서로 진행.
4. `docs/UPSTREAM_SYNC_STRATEGY.md`의 V3 freshness 권원을 `refs/tags/V3.0`(stale)
   에서 `refs/heads/V3.00`으로 갱신 (별도 docs 사이클).

## 5. 검증 증거

```text
git fetch https://github.com/devstom/STOM.git refs/tags/V2.0:... → _update.txt head 2026-04-08 V2.79 (로컬 동일)
git fetch https://github.com/devstom/STOM.git refs/heads/V3.00:... → 5286cde6..fcc626a5, _update.txt head 2026-06-11 V3.32
wt-3: a488af5d(V3.30) b9cdcd99(V3.31) 3dea3b94(V3.32), parity diff = lane-local 문서만
wt-3u: 9459a422(V3.30) 83be2de0(V3.31) 1da630da(V3.32), 통합 게이트 8/8 PASS x3 (최종 pytest 49, critical=0)
wt-dev: 기능 브랜치 0244cb7e, 코드 변경 없음 (검토만)
```
