# V2.51 CLI 검증 기준선

- 작성일: 2026-03-07
- 대상 브랜치: `STOM_Version_2U-cli-research-v251`

## 목적

CLI 브랜치의 로컬 검증 명령을 고정하여,
각 개발 페이스에서 무엇이 통과해야 하는지 명확하게 기록한다.

## 1차 Smoke

```bash
python3 stom_backtest.py --help
python3 stom_backtest.py --list-strategies
python3 stom_backtest.py formula --help
python3 stom_backtest.py strategy --help
```

## 기본 정적 검증

```bash
python3 -m compileall cli scripts tests stom_backtest.py
```

## 로컬 품질 게이트

```bash
python3 scripts/pre_commit_check.py
python3 scripts/run_tests.py --all
```

## 직접 pytest 기준

```bash
python3 -m pytest tests/unit -q
python3 -m pytest tests/integration -q
```

## 운영 원칙

1. `pre_commit_check.py` 는 false positive 없이 실제 문제를 보여줘야 한다.
2. `run_tests.py` 는 실패 수를 `0/0` 으로 축소하지 않고 실제 summary를 보여줘야 한다.
3. 전체 suite가 아직 깨져 있어도, 검증 스크립트는 **왜 실패했는지 정확히 출력**해야 한다.
