# 2026-04-04 V2.74~V2.77 research/init baseline note
## 정규 업데이트 이후 개발 동향
- canonical base = CLI_v267
- network noise handling
- backtest button contract 정리
- runtime regression 정리
## 보호 대상
- research branch-specific compatibility
- `backtest/back_static.py`
- `backtest/backengine_base.py`
- `backtest/backtest.py`
- `utility/setting.py`
- `utility/setting_user.py`
- `utility/worktree_policy.py`
- `utility/telegram_bot.py`
- `utility/webcrawling.py`
## 다음 반영 시 우선순위
- 부모는 `CLI_v267`
- research-specific 유지 요소는 local 우선
- 검증: python scripts/verify_nonrelease_sync.py, research compatibility 유지, CLI_v267 정렬 확인
