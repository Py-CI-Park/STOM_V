# 2026-04-04 V2.75 2U/2U_C blocker audit

## 증상
- `2U`와 `2U_C`에서 `V2.75` 반영 후 `verify_nonrelease_sync.py`가 새로 실패했다.
- 새 실패 항목:
  - telegram qlist contract mismatch
  - WebCrawling stop contract is incomplete

## 근거
- `V2.75` release는 실제로 아래 surface를 변경했다.
  - `utility/telegram_bot.py`
  - `utility/webcrawling.py`
- `V2.74` 상태의 `2U` / `2U_C`는 branch-local non-release contract를 만족했다.
- `V2.75` 반영 후 두 브랜치 모두 release 쪽 구현으로 회귀했다.

## 결론
- 이 red gate는 verifier stale이 아니라 `V2.75`가 branch-local non-release contract를 덮어쓴 결과로 본다.
- 최소 corrective path는 다음과 같다:
  - `2U`: `utility/telegram_bot.py`, `utility/webcrawling.py`를 `9822681d` 상태로 복구
  - `2U_C`: 같은 두 파일을 `2c660152` 상태로 복구

## 수정 범위
- 코드 수정은 `telegram_bot.py`, `webcrawling.py` 두 파일로 제한
- 계약 고정용 text-based test 추가
- `CLI_v267`, `research/init`, `V2.76`, `V2.77`는 이 단계에서 건드리지 않음