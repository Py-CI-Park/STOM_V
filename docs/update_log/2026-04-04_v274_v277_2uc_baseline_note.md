# 2026-04-04 V2.74~V2.77 2U_C baseline note
## 정규 업데이트 이후 개발 동향
- custom integration 유지
- network noise handling
- nonrelease guardrail 보강
## 보호 대상
- `utility/worktree_policy.py`
- `utility/setting.py`
- `utility/setting_base.py`
- `utility/setting_user.py`
- `utility/database_check.py`
- `ui/set_setup_tap.py`
- `ui/ui_button_clicked_settings.py`
- `ui/ui_return_press.py`
## 다음 반영 시 우선순위
- 부모는 `2U`
- custom behavior 충돌 시 local 우선
- 검증: python scripts/verify_nonrelease_sync.py, custom behavior 유지 확인
