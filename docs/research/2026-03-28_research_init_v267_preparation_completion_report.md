# 2026-03-28 research/init v267 준비 완료 보고서

## 목적

이 문서는 `research/init` 브랜치를 `wt-dev / STOM_Version_2U_C_CLI_v267` 기준으로
따라갈 수 있는 상태까지 정리한 작업의 완료 보고서다.

이번 작업의 목표는 공식 `v267`과 바이트 단위로 동일한 브랜치를 만드는 것이 아니라,
리서치 브랜치가 유지해야 할 고유 문서와 최소 호환 보정을 제외하고,
핵심 실행 경로와 주요 기능 축을 `v267` 기준으로 정렬하는 것이었다.

---

## 작업 범위 요약

이번 완료 범위에는 아래 항목이 포함된다.

1. 홈탭 크롤링을 `v267` 통합 구조로 전환
2. CHQS 단일 런타임 프로세스 구조 반영
3. UI / 설정 골격을 `v267` 기준으로 정렬
4. 안전한 로직 subset 우선 반영
5. 백테스트 결합 묶음 반영
6. tick + 시장미시구조 분석 흐름 반영
7. 잔여 tail sync 정리
8. 최종 `SyntaxWarning` 1건 제거
9. 원격 `origin/research/init` push 완료

---

## 적용 커밋 목록

| 순서 | 커밋 | 설명 |
|---|---|---|
| 1 | `94df5da` | 리서치 워크트리 전환 계획 문서 추가 |
| 2 | `7409bd3` | 리서치 워크트리 기준선을 `v267`로 고정 |
| 3 | `f5d7d25` | 홈탭 크롤링을 `v267` 통합 구조로 전환 |
| 4 | `9099ea7` | CHQS 단일 런타임 구조 반영 |
| 5 | `c3fd0b8` | UI / 설정 골격 정렬 |
| 6 | `4d31d92` | 안전한 로직 파일군 일부 반영 |
| 7 | `23bcdfe` | 백테스트 결합 로직 반영 |
| 8 | `2a60f33` | tick 전략 + 시장미시구조 분석 흐름 반영 |
| 9 | `67f700e` | 잔여 v267 차이 정리 |
| 10 | `fd78090` | 마지막 `SyntaxWarning` 제거 |

---

## 핵심 반영 내용

### 1. 홈탭 / 런타임 구조
- `utility/webcrawling_homtab.py` 기반 split 경로 제거
- `utility/webcrawling.py` 기반 통합 홈탭 크롤링 경로 반영
- `ChartHogaQuerySound` 중심의 단일 `proc_chqs` 구조 반영
- `ui_mainwindow.py`, `ui_import_hook.py`, `ui_process_kill.py`, `ui_etc.py` 등 관련 경로 정리

### 2. UI / 설정 계층
- `set_style`, `set_widget`, `set_setup_tap`, `set_dialog_*`, `set_*_tap` 등 주요 UI 골격을 `v267` 기준으로 정렬
- 홈탭 label/key를 `코스피200선물`, `국제금` 기준으로 맞춤

### 3. 백테스트 / 전략 로직
- `back_static`, `backengine_base_oms`, 시장별 backengine, `optimiz`, `rolling_walk_forward_test`를 반영하여
  `sell_cond` 코드 체계와 `opti_turn/opti_kind` 흐름을 정렬
- tick 전략 + `trade/microstructure_analyzer.py` 도입
- `utility/setting_user.py`, `utility/database_check.py`, `ui_button_clicked_settings.py`를 함께 조정해
  `시장미시구조분석` 설정 흐름을 연결

### 4. tail sync 및 마감
- CLI / tests / docs / utility tail 차이 정리
- 마지막 문자열 이스케이프 오탈자 수정으로 `SyntaxWarning` 제거

---

## 검증 결과

### 정적 검증
- broad `py_compile` 통과
- 마지막 `SyntaxWarning` 제거 후 경고 없는 상태 확인

### 기동 검증
- `python stom.py` 실행 후 20초 이상 프로세스 생존 확인
- 표준 출력/표준 에러에 치명적 예외 없음 확인

### 중간 smoke / focused checks
- `ChartHogaQuerySound` import 가능 확인
- 홈탭 차트 키 정렬(`코스피200선물`, `국제금`) 확인
- architect 검토 승인

---

## 의도적으로 남겨둔 차이

이번 작업은 `v267`과의 **완전 동일 코드화**가 아니라,
리서치 브랜치가 `v267`을 따라갈 수 있는 상태 정리를 목표로 했다.
따라서 아래 차이는 의도적으로 유지한다.

| 파일 | 유지 이유 |
|---|---|
| `AGENTS.md` | research 브랜치 전용 운영 규칙 유지 |
| `CLAUDE.md` | research 브랜치 전용 지침 유지 |
| `docs/research/2026-03-28_wt_lab_home_crawler_integration_plan.md` | wt-lab 전환 계획 및 판단 근거 기록 |
| `utility/static.py` | `summer_time = summer_t` 호환 alias 유지 |

---

## 최종 판단

### 기능 동등성 관점
`research/init`은 홈탭, 런타임, UI 골격, 백테스트, tick 전략, microstructure 흐름까지 포함해
**핵심 실행 경로 기준으로는 `v267`을 따라갈 수 있는 수준까지 정리되었다.**

### 코드 동일성 관점
`research/init`은 위 의도적 차이 파일과 호환 alias를 남기므로,
**`STOM_Version_2U_C_CLI_v267`와 바이트 단위로 동일한 코드는 아니다.**

### 실무 결론
> `research/init`은 리서치 브랜치로서 유지해야 할 branch-specific 문서와 최소 호환 보정을 제외하면,
> `v267` 기준으로 작업이 충분히 완료된 상태라고 판단한다.

---

## 남은 caveat

아래 사항은 이번 완료 보고 범위 밖이지만, 참고로 남긴다.

1. 이번 승인 기준은 **full regression certification** 이 아니라
   - clean branch 상태
   - startup smoke
   - broad `py_compile`
   - focused smoke checks
   에 기반한다.
2. 실제 장시간 GUI 사용, 장시간 홈탭 갱신, 실제 전략 운용, 전체 테스트 스위트 실행까지 모두 끝낸 것은 아니다.
3. 향후 `v268+` 또는 research 고유 실험이 시작되면, 이번 상태를 기준점으로 이어가면 된다.

---

## 최종 상태

- 브랜치: `research/init`
- 원격: `origin/research/init`
- 최신 커밋: `fd78090`
- 상태: clean / push 완료

