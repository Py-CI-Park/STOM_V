@echo off
rem QSP6 deep campaign - 2y design / 23mo holdout, per-trade objective, depth-first, no tighten
rem   actions: deep(depth search) > filter(rescue) > drop(amputate). tighten is EXCLUDED
rem   because QSP3 measured its out-of-sample gain at ~0 (design-only improvement).
cd /d C:\System_Trading\STOM\STOM_V.wt-dev
set PYTHONUTF8=1
set STOM_ALLOW_MINIMAL_SETTING=1
for /L %%r in (1,1,10) do (
  echo ===== QSP6 ROUND %%r =====
  python -m ai_strategy_loop.revision.round_runner ^
    --base-buy QSP2ANCH_R8C2_B --base-sell QSP2_T_ANCH_900_920_S ^
    --config docs\research\quant_scoring_pipeline\config_qsp6.json ^
    --holdout-config docs\research\quant_scoring_pipeline\config_qsp6_holdout.json ^
    --tag qsp6deep --round %%r --n 3 --actions deep,filter,drop --objective per_trade
  if errorlevel 3 (
    echo ===== ROUND %%r already recorded - skip =====
  ) else if errorlevel 2 (
    echo ===== EARLY STOP round %%r: judge=converged/diverged =====
    exit /b 2
  ) else if errorlevel 1 (
    echo ===== ERROR STOP round %%r =====
    exit /b 1
  )
)
echo ===== BUDGET EXHAUSTED 10 rounds =====
exit /b 0
