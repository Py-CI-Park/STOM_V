# V2.51 CLI shipped scope 정리

- 작성일: 2026-03-07
- 대상 브랜치: `STOM_Version_2U-cli-research-v251`

## 목적

`cli/` 디렉터리에 구현된 기능이 많아졌지만,
실제로 `stom_backtest.py` 가 공식적으로 노출하는 기능과
내부 라이브러리/연구용 모듈을 구분하지 않으면 문서와 코드가 어긋난다.

이 문서는 **현재 shipped CLI 범위**를 고정한다.

---

## 1. 공식 shipped CLI

### A. 기본 백테스트 실행
- 진입점: `stom_backtest.py`
- 관련 모듈:
  - `cli/config.py`
  - `cli/runner.py`
  - `cli/output.py`
  - `cli/timeframe_detector.py`

### B. 공식 서브커맨드
- `formula`
  - `list`
  - `add`
  - `test`
  - `delete`
  - `export`
  - `import`
- `strategy`
  - `list`
  - `validate`
  - `analyze`

관련 모듈:
- `cli/subcommands.py`
- `cli/formula.py`
- `cli/strategy.py`
- `cli/strategy_loader.py`

---

## 2. 현재 library-only 모듈

아래는 구현되어 있으나, 현재 `stom_backtest.py` 공식 서브커맨드로는 직접 노출하지 않는다.

### 운영/보조 모듈
- `cli/data_bridge.py`
- `cli/monitor.py`
- `cli/engine_tuner.py`
- `cli/report.py`

### 자동화/분석 모듈
- `cli/history.py`
- `cli/sweep.py`
- `cli/optimizer.py`
- `cli/ai_controller.py`

### 생성/실험 성격 모듈
- `cli/strategy_generator.py`

---

## 3. 운영 원칙

1. 문서에서 “CLI 기능 구현 완료”라고 표현할 때는 **공식 shipped CLI 범위만 기준**으로 한다.
2. library-only 모듈은 구현되어 있어도, help/subcommand에 노출되지 않으면 “공식 CLI”로 간주하지 않는다.
3. 향후 공식 CLI로 승격할 기능은 다음 중 하나를 만족해야 한다.
   - `stom_backtest.py` 의 옵션/서브커맨드로 연결됨
   - smoke / unit / integration 테스트가 추가됨
   - 사용자 문서에 사용 예시가 반영됨

---

## 4. 현재 결론

현재 브랜치는:
- **기본 백테스트 + formula/strategy** 는 공식 CLI
- 나머지 다수의 `cli/` 모듈은 **Python API / library-only / 연구용 성격**

즉, “구현된 모듈 수”와 “shipped CLI 범위”를 분리해서 관리해야 한다.
