@echo off
rem QSP3 map-surgery campaign - 12 round budget, drop>filter>tighten, exit2=stop, exit3=skip recorded round
cd /d C:\System_Trading\STOM\STOM_V.wt-dev
set PYTHONUTF8=1
set STOM_ALLOW_MINIMAL_SETTING=1
for /L %%r in (1,1,12) do (
  echo ===== QSP3MAP ROUND %%r =====
  python -m ai_strategy_loop.revision.round_runner ^
    --base-buy QSP2ANCH_R8C2_B --base-sell QSP2_T_ANCH_900_920_S ^
    --config docs\research\quant_scoring_pipeline\config_qsp3.json ^
    --holdout-config docs\research\quant_scoring_pipeline\config_qsp3_holdout.json ^
    --tag qsp3map --round %%r --n 3 --actions drop,filter,tighten
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
echo ===== BUDGET EXHAUSTED 12 rounds =====
exit /b 0
