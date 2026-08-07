# 다밴드 자율 발굴 밤샘 루프 (2026-06-14~)

> tmap_multiband_discovery.py — 생성→스모크(같은좌표 양분기)→전체기간 train→OOS 단계격상. ★PROMISING=전체기간+OOS까지 흑자(THETA급 바). 엔진 무수정.

| # | 트랙 | 템플릿 | robust 코너(스모크 min) | smoke q1/q2 | 전체train | OOS | 판정 |
|---|---|---|---|---|---|---|---|
| 0 | tick_new | llmgen_tick_session_isolated_small_ignite_midlarge_reburst_late_strict | — | -1,024,859 / None | — | — | no-go |
| 1 | tick_anchor | llmgen_theta_anchor_midcap_upperlate_discrete_reignite | b1_cap_max=1500 min=785,449 | 785,449 / 1,402,966 | -10,470,576 | — | smoke-pass |
| 2 | min_new | llmgen_min_trisession_buyflow_only_capfork_ma_reaccel | — | -11,229,331 / None | — | — | no-go |
| 3 | tick_new | llmgen_tick_anchor1500_midlarge_ma_money_reburst_discrete | — | -1,231,353 / None | — | — | no-go |
| 4 | tick_anchor | llmgen_tick_theta1500_midupper_contiguous_rehigh_strict | b2_sec_money_min=1000 min=269,199 | 504,842 / 269,199 | -21,700,906 | — | smoke-pass |
| 5 | min_new | llmgen_min_twoband_am_midcap_cumbuy_pm_large_ma_break_clean | — | -5,602,176 / None | — | — | no-go |
| 6 | tick_new | llmgen_tick_anchor1500_uppermid_late_turnover_discrete | — | -6,512,728 / None | — | — | no-go |
| 7 | tick_anchor | llmgen_tick_theta1500_midupper_late_rehigh_discrete_clean | b1_rate_min=6.0 min=159,107 | 1,643,712 / 4,027,329 | -14,726,036 | — | smoke-pass |
