# V3U V3.29 반영 이후 다음 단계 안내 (2026-05-27)

## 현재 상태

V3U는 V3.19~V3.29 반영, pyd-free 검증, 커밋 메시지 한글 복구, Ralph state 정리까지 완료된 상태다.

| 항목 | 값 |
| --- | --- |
| 워크트리 | `C:/System_Trading/STOM/STOM_V.wt-3u` |
| 브랜치 | `STOM_Version_3U` |
| 현재 HEAD | `38f6ce61` 이후 본 문서 커밋 |
| 기준 공식 V3 | `STOM_Version_3` / `3d4390ea STOM V3.29` |
| 남은 untracked 항목 | `_database_backup_2026-05-22/en_key.txt` |

## 진행률

| 단계 | 상태 | 진행률 |
| --- | ---: | ---: |
| V3.19~V3.29 V3U 반영 | 완료 | 100% |
| pyd-free 검증 | 완료 | 100% |
| 커밋 메시지 한글 복구 | 완료 | 100% |
| Ralph state 정리 | 완료 | 100% |
| 실제 GUI 실행 테스트 | 다음 단계 | 0% |
| 오류 수정 / dev 개발 | 대기 | 0% |
| 최종 handoff / push 정리 | 대기 | 0% |

## 다음 작업 1 — 직접 GUI 테스트

직접 확인할 항목은 아래 순서로 진행한다.

| 순서 | 테스트 항목 | 목적 |
| ---: | --- | --- |
| 1 | 프로그램 실행 / MainWindow 부팅 | V3U pyd-free MainWindow 실제 부팅 확인 |
| 2 | 기본 탭 전환 | 탭/위젯 연결 오류 확인 |
| 3 | 설정창 열기/닫기 | V3.28 설정/팩터/TTS 보정 영향 확인 |
| 4 | 차트창 / 호가창 / 전략창 열기 | dialog/window wrapper 오류 확인 |
| 5 | 백테스트 관련 창 열기 | backtest UI 연결 및 프로세스 placeholder 확인 |
| 6 | 종료 동작 확인 | QThread/timer/process cleanup 오류 확인 |
| 7 | 콘솔 traceback / `_log` 오류 확인 | 자동 smoke에서 잡히지 않는 런타임 오류 수집 |
| 8 | TTS/Supertonic 관련 버튼은 신중히 확인 | 현재 `tts_sound`는 placeholder 계약 복구 상태이므로 실제 활성화는 별도 검토 필요 |

## 다음 작업 2 — 오류 발생 시 처리

오류가 나오면 아래 자료 중 가능한 것을 수집한다.

```text
1. 콘솔 traceback
2. _log 파일 내용
3. 어떤 버튼/화면에서 발생했는지 순서
4. 스크린샷 또는 에러 메시지
```

처리 흐름은 아래와 같다.

```text
원인 분석 → V3U 규칙에 맞게 수정 → pytest/contract/smoke 재검증 → 커밋
```

## 다음 작업 3 — dev 개발 후보

| 우선순위 | dev 작업 | 비고 |
| ---: | --- | --- |
| 1 | 실제 GUI 테스트 오류 수정 | 최우선 |
| 2 | Supertonic TTS 실제 활성화 여부 결정 | 현재는 placeholder 계약만 복구 |
| 3 | V3U 런타임 안정화 | 종료/스레드/로그 오류 중심 |
| 4 | 최종 handoff 문서 정리 | 테스트 결과 포함 |
| 5 | 필요 시 2U_C/3U_C 쪽 계획 | 별도 단계 |

## 주의사항

- 커밋 메시지 복구 때문에 `STOM_Version_3U`의 커밋 해시가 변경되었다.
- 로컬에서만 쓰면 문제 없지만, 원격에 이전 해시를 이미 push했다면 이후 push 전략을 조심해야 한다.
- push 전에는 반드시 원격 상태를 확인한다.
- `_database_backup_2026-05-22/en_key.txt`는 기존 runtime backup으로 유지 중이며, 본 문서 작업에서는 삭제하지 않는다.

## 추천 다음 시작점

```text
STOM_Version_3U 실제 GUI 실행 테스트
```

직접 실행 후 오류가 있으면 로그를 기준으로 dev 수정 단계로 이어간다.
