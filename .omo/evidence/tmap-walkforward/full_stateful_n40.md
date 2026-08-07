# 다밴드 자율 발굴 밤샘 루프 (2026-06-14~)

> tmap_multiband_discovery.py — 생성→스모크(같은좌표 양분기)→전체기간 train→OOS 단계격상. ★PROMISING=전체기간+OOS까지 흑자(THETA급 바). 엔진 무수정.

| # | 트랙 | 템플릿 | robust 코너(스모크 min) | smoke q1/q2 | 전체train | OOS | 판정 |
|---|---|---|---|---|---|---|---|
| 0 | tick_new | llmgen_tick_discrete_open_small_midupper_late_turnover_reburst | — | -11,278,411 / None | — | — | no-go |
| 1 | tick_anchor | llmgen_theta_anchor_midlate_capisolated_ma_reburst_generalized | — | -300,192 / None | — | — | no-go |
| 2 | min_new | llmgen_min_open_midcap_cumbuy_pm_uppercap_flow_ma_isolated_v2 | — | -1,295,084 / None | — | — | no-go |
| 3 | tick_new | llmgen_tick_anchor_small_two_rehigh_conservative_discrete | — | -2,637,717 / None | — | — | no-go |
| 4 | tick_anchor | llmgen_tick_theta_anchor_contiguous_midupper_strict_rehigh_slim | — | -6,181,120 / None | — | — | no-go |
| 5 | min_new | llmgen_min_twoband_am_cumbuy_persist_pm_capflip_qty_ma_strict | — | -1,114,831 / None | — | — | no-go |
| 6 | tick_new | llmgen_tick_theta_anchor_midlate_density_throttled_reburst | — | -4,010,711 / None | — | — | no-go |
| 7 | tick_anchor | llmgen_tick_theta_anchor_contiguous_midupper_late_valuegated_rehigh | — | -230,906 / None | — | — | no-go |
| 8 | min_new | llmgen_min_bisession_buyvelocity_midcap_pm_upper_ma_proxy | — | -8,020,984 / None | — | — | no-go |
| 9 | tick_new | llmgen_tick_anchor_small_midlate_prevtime_ma_reaccel_guarded | — | -729,213 / None | — | — | no-go |
| 10 | tick_anchor | llmgen_tick_theta_anchor_mid_late_rehigh_density_guard | — | -1,913,894 / None | — | — | no-go |
| 11 | min_new | llmgen_min_buyqty_only_am_midcap_pm_capfork_ma_reaccel | — | -1,691,382 / None | — | — | no-go |
| 12 | tick_new | llmgen_tick_theta_anchor_conservative_midlate_prevtime_liquidity_ladder | — | -1,421,946 / None | — | — | no-go |
| 13 | tick_anchor | llmgen_tick_theta_anchor_midlate_valueguard_rehigh_isolated | — | -1,534,677 / None | — | — | no-go |
| 14 | min_new | llmgen_min_open_midcap_buyqty_persist_afternoon_uppercap_mapulse_discrete | — | -4,464,263 / None | — | — | no-go |
| 15 | tick_new | llmgen_tick_theta_anchor_midlate_capisolated_value_reburst | — | 743,956 / 1,144,121 | — | — | no-go |
| 16 | tick_anchor | llmgen_tick_theta_anchor_midupper_late_strict_reignite_isolated_v6 | — | -2,085,156 / None | — | — | no-go |
| 17 | min_new | llmgen_min_am_midcap_flowpersist_pm_othercap_maproxy_discrete | — | -551,773 / None | — | — | no-go |
| 18 | tick_new | llmgen_tick_theta_anchor_threephase_capseg_strict_reburst_v7 | — | -3,544,062 / None | — | — | no-go |
| 19 | tick_anchor | llmgen_tick_theta_anchor_midlate_capfork_rehigh_turnover_guard | — | -14,567,200 / None | — | — | no-go |
| 20 | min_new | llmgen_min_open_midcap_persistent_buy_pm_othercap_ma_reburst_guarded | — | -846,235 / None | — | — | no-go |
| 21 | tick_new | llmgen_tick_theta_anchor_midlate_valueburst_twofork_slim | — | -13,355,433 / None | — | — | no-go |
| 22 | tick_anchor | llmgen_tick_theta_anchor_multisession_highnear_valueburst_clean_v9 | — | -2,946,666 / None | — | — | no-go |
| 23 | min_new | llmgen_min_twozone_midcap_cumbuy_am_uppercap_pm_ma_reaccel_clean_v1 | — | -1,571,491 / None | — | — | no-go |
| 24 | tick_new | llmgen_tick_theta_anchor_boundary_midupper_reburst_strict_v1 | — | -16,019,858 / None | — | — | no-go |
| 25 | tick_anchor | llmgen_theta_anchor_conservative_midlate_capgap_reignite | — | -1,036,757 / None | — | — | no-go |
| 26 | min_new | llmgen_min_split_open_midcap_cumbuy_pm_uppercap_maproxy_flowonly_v1 | — | -1,763,609 / None | — | — | no-go |
| 27 | tick_new | llmgen_tick_theta_anchor_small_midupper_value_density_reburst_discrete_v8 | — | -2,392,265 / None | — | — | no-go |
| 28 | tick_anchor | llmgen_tick_theta_anchor_mid_late_capisolated_rehigh_guard_v1 | — | -2,990,916 / None | — | — | no-go |
| 29 | min_new | llmgen_min_threezone_buyqty_pressure_moneypulse_ma_caporthogonal_v1 | — | -1,644,321 / None | — | — | no-go |
| 30 | tick_new | llmgen_tick_theta_anchor_small_midupper_strict_prevbounded_reburst | — | -4,510,063 / None | — | — | no-go |
| 31 | tick_anchor | llmgen_tick_theta_anchor_mid_upper_rehigh_two_relays_clean | — | -6,185,454 / None | — | — | no-go |
| 32 | min_new | llmgen_min_open_flowpersist_afternoon_caporthogonal_maproxy_buyqtyonly_v2 | — | -1,015,563 / None | — | — | no-go |
| 33 | tick_new | llmgen_tick_anchor_small_mid_late_caporthogonal_reburst_v1 | — | -2,441,195 / None | — | — | no-go |
| 34 | tick_anchor | llmgen_theta_anchor_midlate_turnover_capped_reburst | — | -1,878,723 / None | — | — | no-go |
| 35 | min_new | llmgen_min_twosession_pure_minqty_midcap_am_uppercap_pm_rebreak_v1 | — | -1,209,985 / None | — | — | no-go |
| 36 | tick_new | llmgen_tick_anchor_open_small_midlate_conservative_reburst_v1 | — | -1,471,648 / None | — | — | no-go |
| 37 | tick_anchor | llmgen_tick_theta_anchor_midupper_late_density_rehigh_nonoverlap_v1 | — | -1,386,250 / None | — | — | no-go |
| 38 | min_new | llmgen_min_open_midcap_buyaccum_pm_capshift_maproxy_discrete | — | -1,024,885 / None | — | — | no-go |
| 39 | tick_new | llmgen_tick_anchor_open_small_midupper_late_strict_breakrelay_v1 | — | -6,780,442 / None | — | — | no-go |
