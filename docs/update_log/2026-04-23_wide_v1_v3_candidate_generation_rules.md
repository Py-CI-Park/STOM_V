# Wide v1 v3 후보 생성 규칙 구현

## 목적

PR #21 이후 WideV1IterationV2_20260423__cand005가 같은 wide baseline 기준에서 cand003보다 높은 reference score를 기록했으므로, cand005를 새 reference best로 삼는 v3 후보 생성 경로를 추가했다.

## 변경 사항

- `best_feature_mix_v3` 후보 생성 helper를 추가했다.
- v3 후보군을 `v3_tighten_secondary`, `v3_repair_trade_amount`, `v3_replace_secondary`로 나눴다.
- `v3_control_keep_best`는 cand005 기존 결과를 report metadata로 보존하고 재실행 후보에서는 제외했다.
- 기존 `iteration_v2_*` CLI/config 옵션 표면에서 `best_feature_mix_v3` mode를 허용했다.
- research report에 v3 후보 family 분포와 control metadata를 표시했다.

## 검증

```text
focused tests:
  python -m pytest tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py -q
  output:
........................................................................ [ 44%]
........................................................................ [ 88%]
..................                                                       [100%]
162 passed in 5.90s

ruff:
  python -m ruff check cli/research_iteration_v3.py cli/research_loop.py cli/subcommands.py cli/research_report.py tests/unit/test_research_iteration_v3.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_report.py
  output:
All checks passed!

sync guard:
  python scripts/verify_nonrelease_sync.py
  output:
[OK] ��ũƮ���� .pyd ������ �����ϴ�.
[OK] �ڷ��׷� qlist ����� ���� MainWindow ������ ��ġ�մϴ�.
[OK] MainWindow�� �ڷ��׷� ��Ÿ���� �����մϴ�.
[OK] ���� ���� ���İ� TelegramProcessAlive ��θ� ����մϴ�.
[OK] �ڷ��׷� alive helper�� �����մϴ�.
[OK] Jisu cleanup matches V2.70 removal.
[OK] Shutdown cleanup matches current MainWindow runtime.
[OK] WebCrawling runtime wiring matches QThread contract.
[OK] static.py compatibility exports match runtime contract.
[OK] WebCrawling stop contract includes timeout and cancellation guards.
[OK] Key loading safety guard is present.
[OK] Kiwoom P/L rounding matches expected loss math.
[OK] ������ ��ũƮ������ �ø���Ű UI ������ ���ܵ˴ϴ�.
[OK] ���� ������ ��ũƮ�� �ø���Ű ��å�� �����ϴ�.
[OK] dict_set ���簡 ������ ��ũƮ�� �ø���Ű ��å�� �����ϴ�.
[OK] legacy utility/setting.py�� ������ ��ũƮ�� �ø���Ű ��å�� �����ϴ�.

��� ������ ��ũƮ�� ����ȭ ���巹�� �˻縦 ����߽��ϴ�.

diff check:
  git diff --check
  output:
no output

full unit tests:
  python -m pytest tests/unit/ -q
  output:
........................................................................ [  6%]
........................................................................ [ 13%]
........................................................................ [ 19%]
.....................................................s.................. [ 26%]
........................................................................ [ 32%]
........................................................................ [ 39%]
........................................................................ [ 45%]
........................................................................ [ 52%]
........................................................................ [ 59%]
........................................................................ [ 65%]
........................................................................ [ 72%]
........................................................................ [ 78%]
........................................................................ [ 85%]
........................................................................ [ 91%]
........................................................................ [ 98%]
..................                                                       [100%]
============================== warnings summary ===============================
tests/unit/test_analyzer.py::test_analyze_result_frame_returns_candidates
tests/unit/test_analyzer.py::test_analyze_result_frame_returns_candidates
tests/unit/test_analyzer.py::test_save_analysis_writes_json
tests/unit/test_analyzer.py::test_save_analysis_writes_json
tests/unit/test_analyzer.py::test_analyze_ttest_independent
tests/unit/test_analyzer.py::test_analyze_ttest_independent
tests/unit/test_analyzer.py::test_analyze_ttest_operator_direction
  C:\Python\64\Python3119\Lib\site-packages\scipy\stats\_axis_nan_policy.py:573: RuntimeWarning: Precision loss occurred in moment calculation due to catastrophic cancellation. This occurs when the data are nearly identical. Results may be unreliable.
    res = hypotest_fun_out(*samples, **kwds)

tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module
tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module
  C:\Python\64\Python3119\Lib\site-packages\binance\ws\websocket_api.py:4: DeprecationWarning: websockets.WebSocketClientProtocol is deprecated
    from websockets import WebSocketClientProtocol  # type: ignore

tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module
  C:\Python\64\Python3119\Lib\site-packages\websockets\legacy\__init__.py:6: DeprecationWarning: websockets.legacy is deprecated; see https://websockets.readthedocs.io/en/stable/howto/upgrade.html for upgrade instructions
    warnings.warn(  # deprecated in 14.0 - 2024-11-09

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1097 passed, 1 skipped, 10 warnings in 82.17s (0:01:22)
```

## 남은 리스크

- v3 candidate_count=10 full-year runtime은 별도 실행 결과 문서에서 기록한다.
- cand005 control은 재실행하지 않으므로 동일 조건 재현성 검증은 이번 구현 단계에서 생략한다.
- v3 best도 최종 채택이 아니며 promote/WFO 검증이 필요하다.
