# STOM_Version_2U_C / CLI_v258 - AI Agent Instructions

## 브랜치 역할

`STOM_Version_2U_C`는 커스텀 개발의 홈 브랜치이며, `CLI_v258`은 CLI 자동화 개발 브랜치입니다.
업스트림(V2) → 2U(pyd→py) → 2U_C(커스텀) → CLI(자동화) 순서로 전파됩니다.

## 시리얼키 정책 (필수)

> **이 브랜치에서는 시리얼키를 사용하지 않습니다.**

- 업스트림(V2)의 pyd에는 시리얼키 인증이 포함되어 있음
- 2U 계열(2U, 2U_C, CLI)에서는 V2.36.U1.5에서 시리얼키 기능을 **의도적으로 제거**함
- pyd→py 추론 시 **시리얼키 관련 코드를 절대 추가하지 않음**
- 시리얼키 관련 업스트림 변경은 추론에서 **제외**

## 업스트림 동기화 방식

이 브랜치는 업스트림 파일을 **커스텀 수정**하고 있으므로, 오버레이가 아닌 **cherry-pick**으로 동기화합니다.

```
2U의 버전 커밋 → cherry-pick → 2U_C → cherry-pick → CLI_v258
```

- 충돌 시 CLI 커스텀 코드를 보존 (`--ours`)
- cherry-pick 후 반드시 `pytest tests/unit/ -q` 실행
- 상세: `docs/UPSTREAM_SYNC_STRATEGY.md` 4.2절, 9절 참조

## CLI 커스텀 수정 파일 (충돌 주의)

업스트림과 다른 CLI 고유 수정이 있는 파일:

| 파일 | CLI 수정 내용 |
|------|-------------|
| `backtest/back_static.py` | TRADE_RESULT_B/S/R_COLUMNS, GetResultDataframe 확장 |
| `backtest/backengine_base.py` | CLI 호환 import, 엔진 설정 |
| `backtest/back_subtotal.py` | CLI 호환 수정 |
| `utility/setting.py` | CLI 전용 DICT_SET (삭제하면 안 됨) |
| `utility/setting_base.py` | CLI 호환 별칭 6개 (DB_*_BACK_*) |
| `utility/lazy_imports.py` | V2.62에서 삭제되었으나 CLI에서 복원 유지 |

## 커밋 규칙

| 항목 | 규칙 |
|------|------|
| 형식 | `<type>: <설명>` (feat, fix, refactor, docs, test, chore) |
| 스테이징 | 명시적 파일 지정 (`git add -A` 사용 금지) |
| 테스트 | 커밋 전 `pytest tests/unit/ -q` 통과 확인 |
| 버전 업데이트 | `STOM V{major}.{minor}` (업스트림 반영 시) |
