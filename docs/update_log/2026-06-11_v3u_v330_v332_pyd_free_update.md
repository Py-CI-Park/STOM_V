# V3U V3.30~V3.32 pyd-free 반영 완료 기록 (2026-06-11)

## 목적

`STOM_Version_3`에 공식 반영된 V3.30~V3.32 변경을 `STOM_Version_3U`에 순차 반영했다. V3U lane 불변식에 따라 upstream `ui/main_window.pyd`는 추적하지 않고 V3U의 `ui/main_window.py` pyd-free 계약을 유지했다.

## 기준 범위

| 항목 | 값 |
| --- | --- |
| 공식 freshness 권원 | `https://github.com/devstom/STOM.git` `refs/heads/V3.00` (`refs/tags/V3.0`은 2026-04-23 V3.08 stale) |
| upstream tip | `fcc626a5` (2026-06-11 V3.32) |
| V3 worktree/branch | `STOM_V.wt-3` / `STOM_Version_3` → `3dea3b94 STOM V3.32` |
| V3U worktree/branch | `STOM_V.wt-3u` / `STOM_Version_3U` |
| 제외 범위 | V3.32 tail `fcc626a5` (윈도우 핸들 ctypes 수정 1건), runtime `_database`/`_log`/`*.db`, upstream `.pyd` |

## 순차 반영 커밋

| Version | upstream 경계 | V3 formal | V3U commit | 주요 V3U 보정 |
| --- | --- | --- | --- | --- |
| V3.30 | `d5fbdc87` | `a488af5d` | `9459a422` | 보정 없음 (MainWindow 계약 변화 없음) |
| V3.31 | `8392669d` | `b9cdcd99` | `83be2de0` | `database_check.py` 모듈 레벨 상수 구조 유지 + STG_DATA 기본값 4건 적용 |
| V3.32 | `68aa83f4` | `3dea3b94` | `1da630da` | 아래 3건 |

## V3.32 V3U 보정 상세 (모두 V3U 전용 파일)

1. **`ui.homepg` 사전 초기화 (게이트 자동 차단 사례)** — 홈탭 마우스오버가
   `set_home_tap.py:484-499`에서 `ui.homepg[0..15] = plot` 인덱스 할당, hover
   enter/leave(:51/:57)와 `draw_home_chart.py:114`가 읽음. 첨자 할당은 attr을
   만들지 않으므로 pyd가 하던 빈 dict 초기화를 `_init_runtime_state`에 추가.
   **attr inventory가 CRITICAL drift 1로 커밋 전 자동 검출** — V3 흡수 게이트
   설계 목적(pyd 인터페이스 변화 자동 감지)이 처음으로 실전 입증된 사례.
2. **`database_check.py`** — V3U 모듈 레벨 상수 노출 구조 유지한 채 upstream
   적용: MAIN_CLOUMNS `'보이스네임'→'읽기속도'`, MAIN_DATA `'F1'→1`, main 테이블
   `읽기속도` 컬럼 migration 로직.
3. **tts_sound 실 worker 전환** — supertonic 삭제로 기존 placeholder 사유
   (자동 다운로드/외부 런타임 부작용)가 소멸 → `TextToSpeak(soundQ, dict_set)`
   (win32com SAPI) 부착·시작. soundQ 소비자가 복원돼 '알림소리'가 pyd와 동일
   동작. `process_kill`에 quit/wait cleanup (webc 선례), conftest
   `STOM_V3U_DISABLE_TTS=1`, 부착 계약 회귀 테스트
   (`test_text_to_speak_attach_contract`), `_default_settings`에 `읽기속도: 1`.

## 검증 증거

```text
버전별: scripts/v3u_smoke_offline_gui.py PASS → verify_v3u_pyd_gui_contract.py 8/8 PASS
V3.30: pytest 48 passed, attr critical=0 (manifest verify_2026-06-11_v330.json)
V3.31: pytest 48 passed, attr critical=0 (manifest verify_2026-06-11_v331.json)
V3.32: 1차 게이트 FAIL (pytest 1 failed + critical=1: self.homepg) → 보정 후
       8/8 PASS, pytest 49 passed, attr critical=0 (manifest verify_2026-06-11_v332.json)
git ls-files *.pyd → empty (V3U), wt-3는 upstream pyd 갱신 보존
```

## 남은 리스크 / 후속 작업

- tail `fcc626a5` (`ui/etcetera/etc.py:271` `int(window.winId())` →
  `ctypes.c_void_p`) 미포함 — `change_title_bar_color`가 환경에 따라 큰 핸들
  값에서 오류 가능. V3 official source 0줄 수정 invariant상 V3U에서 선반영하지
  않고 다음 V3 흡수 시 formal로 포함한다. 사용자 직접 테스트에서 타이틀바
  색상 적용 오류 관찰 시 본 항목이 원인 후보 1순위.
- TextToSpeak 실 음성 재생, 홈탭 마우스오버 효과, 읽기속도 설정은 offline
  구조 검증 범위 밖 — 사용자 직접 테스트(B1) 확인 항목에 추가됨.
- 사용자 실 DB의 main 테이블은 첫 구동 시 `읽기속도` 컬럼 migration이
  자동 수행된다 (`database_check.py` V3.32 로직).

## 관련 문서

- `docs/update_log/2026-06-11_upstream_freshness_and_2uc_backport_review.md`
  (STOM_V 동시 커밋 공용 검토: 신선도 점검 + 2U_C 백포트 후보)
- `docs/V3U_INFERENCE_LESSONS.md` 사이클 15
- `docs/V3U_NEXT_STEPS.md` §5 사이클 15
