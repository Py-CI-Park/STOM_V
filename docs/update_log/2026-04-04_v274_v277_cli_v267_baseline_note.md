# 2026-04-04 V2.74~V2.77 CLI_v267 baseline note
## 정규 업데이트 이후 개발 동향
- backengine opti kind alias 복구
- split hoga arrays 복구
- backtest button contract 정리
- network noise handling
## 보호 대상
- CLI contract
- `backtest/graph/`
- `backtest/back_static.py`
- `backtest/backengine_base.py`
- `backtest/back_subtotal.py`
- `backtest/backtest.py`
- `utility/setting.py`
- `utility/setting_base.py`
- `utility/lazy_imports.py`
- `utility/worktree_policy.py`
- `utility/telegram_bot.py`
- `utility/webcrawling.py`
## 다음 반영 시 우선순위
- 부모는 `2U_C`
- CLI contract와 graph 보호가 최우선
- 검증: python scripts/verify_nonrelease_sync.py, pytest tests/unit/ -q, backtest/graph/ untouched, CLI contract 유지 확인
