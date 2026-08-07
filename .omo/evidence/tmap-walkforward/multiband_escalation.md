# 다밴드 자율 발굴 밤샘 루프 (2026-06-14~)

> tmap_multiband_discovery.py — 생성→스모크(같은좌표 양분기)→전체기간 train→OOS 단계격상. ★PROMISING=전체기간+OOS까지 흑자(THETA급 바). 엔진 무수정.

| # | 트랙 | 템플릿 | robust 코너(스모크 min) | smoke q1/q2 | 전체train | OOS | 판정 |
|---|---|---|---|---|---|---|---|
| 0 | tick_new | llmgen_discrete_open_small_midlarge_reburst_clean | — | 1,734,031 / -203,841 | — | — | no-go |
| 1 | tick_anchor | llmgen_theta_threeband_open_mid_late_reburst | — | -2,426,169 / None | — | — | no-go |
| 2 | min_new | None | — | — | — | — | gen-fail |
| 3 | tick_new | llmgen_threeband_open_small_mid_late_capseg_reburst | — | -6,873,806 / None | — | — | no-go |
| 4 | tick_anchor | llmgen_theta_capladder_open_mid_late_highreclaim | — | -1,231,146 / None | — | — | no-go |
| 5 | min_new | llmgen_min_discrete_morning_supply_afternoon_reclaim | — | -5,842,440 / None | — | — | no-go |
| 6 | tick_new | llmgen_tick_discrete_open_small_midlarge_late_reclaim_v3 | — | -477,907 / None | — | — | no-go |
| 7 | tick_anchor | llmgen_theta_barbell_open_mid_late_highprint | b1_sec_money_min=1000 min=205,715 | 205,715 / 1,533,675 | -2,030,044 | — | smoke-pass |
| 8 | min_new | llmgen_min_twoband_midcap_supply_pm_price_reaccel | — | -6,370,035 / None | — | — | no-go |
| 9 | tick_new | llmgen_tick_threeband_session_cap_discrete_first_reignite | — | -2,755,915 / None | — | — | no-go |
| 10 | tick_anchor | llmgen_theta_discrete_open_mid_late_cap_reignite_clean | — | -1,910,485 / None | — | — | no-go |
| 11 | min_new | llmgen_min_barbell_am_supply_pm_ma_reaccel | — | -4,306,618 / None | — | — | no-go |
| 12 | tick_new | llmgen_tick_session_barbell_open_mid_late_cap_reburst | — | -3,909,918 / None | — | — | no-go |
| 13 | tick_anchor | llmgen_theta_open_mid_late_cap_reignite_ladder_clean | — | -3,606,454 / None | — | — | no-go |
| 14 | min_new | llmgen_min_trisession_discrete_supply_reaccel | — | -1,844,924 / None | — | — | no-go |
| 15 | tick_new | llmgen_tick_threeband_open_small_midlate_cap_rebreak_isolated | — | -3,146,414 / None | — | — | no-go |
| 16 | tick_anchor | llmgen_theta_open_mid_late_clean_rehigh_reclaim | — | -6,543,646 / None | — | — | no-go |
| 17 | min_new | llmgen_min_discrete_midcap_am_supply_pm_ma_qtyclean | — | -985,127 / None | — | — | no-go |
| 18 | tick_new | llmgen_tick_capseg_contiguous_open_mid_late_reignite | — | -3,165,178 / None | — | — | no-go |
| 19 | tick_anchor | llmgen_theta_contiguous_capladder_open_mid_late_priorhigh_reburst | — | -2,767,351 / None | — | — | no-go |
| 20 | min_new | llmgen_min_open_supply_pm_discrete_cumqty_ma_reclaim | — | -4,662,640 / None | — | — | no-go |
| 21 | tick_new | llmgen_tick_trislot_open_mid_late_cap_reignite_maflow | — | None / None | — | — | no-go |
| 22 | tick_anchor | llmgen_tick_theta_contiguous_midlarge_ma_burst_barbell | — | -6,582,793 / None | — | — | no-go |
| 23 | min_new | llmgen_min_twoband_cumbuy_velocity_am_pm_ma_proxy | — | -1,495,503 / None | — | — | no-go |
| 24 | tick_new | llmgen_tick_threeband_capladder_ma_reburst_slim | — | -8,250,612 / None | — | — | no-go |
| 25 | tick_anchor | llmgen_tick_theta_contiguous_small_mid_large_ma_reburst_lite | — | -6,027,866 / None | — | — | no-go |
| 26 | min_new | llmgen_min_threeband_am_supply_midflow_pm_ma_reclaim | — | -8,791,216 / None | — | — | no-go |
| 27 | tick_new | llmgen_tick_trisession_capladder_clean_ma_reburst | — | -18,833,810 / None | — | — | no-go |
| 28 | tick_anchor | llmgen_tick_theta_barbell_midlate_ma_reignite_proxy_v1 | — | -12,432,523 / None | — | — | no-go |
| 29 | min_new | llmgen_min_bisession_cumbuy_money_ma_capfork | — | -8,058,203 / None | — | — | no-go |
| 30 | tick_new | llmgen_tick_threephase_small_midlarge_prevfiltered_reburst | — | -13,079,081 / None | — | — | no-go |
| 31 | tick_anchor | llmgen_tick_theta_contiguous_open_mid_late_capfork_highreburst | — | -1,960,511 / None | — | — | no-go |
| 32 | min_new | llmgen_min_bifurcated_am_cumbuy_pm_maproxy | — | -2,057,741 / None | — | — | no-go |
| 33 | tick_new | llmgen_tick_triwindow_small_midlarge_ma_reburst_prevturn | — | -25,237,857 / None | — | — | no-go |
| 34 | tick_anchor | llmgen_theta_anchor_midlate_capfork_rehigh_clean | — | -4,267,967 / None | — | — | no-go |
| 35 | min_new | llmgen_min_bisession_cumbuy_reaccel_capdiverge_ma_proxy | — | -613,556 / None | — | — | no-go |
| 36 | tick_new | llmgen_tick_multiband_first_ignition_midlarge_prevtime_ma_reburst | — | -4,198,931 / None | — | — | no-go |
| 37 | tick_anchor | llmgen_tick_theta_contiguous_open_mid_late_avgprice_reburst_capfork | — | -3,138,051 / None | — | — | no-go |
| 38 | min_new | llmgen_min_am_cumbuy_persist_pm_ma_reaccel_discrete | — | -12,931,388 / None | — | — | no-go |
| 39 | tick_new | llmgen_tick_bislice_open_small_midlarge_ma_reburst_costaware | — | -13,710,049 / None | — | — | no-go |
