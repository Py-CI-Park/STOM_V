# P1 Branch Static Map

Status: `complete`

## Strategy Code Facts

| Role | Table | Name | Lines | SHA-256 | Runtime call |
|---|---|---|---:|---|---|
| C_T buy | `stockbuy` | `C_T_900_920_U2_B` | `431` | `902cb36b87f5828548531583cd4aa16ed4a5a2a597b3db3abba217cb0f86e2e3` | `self.Buy` |
| C_T sell | `stocksell` | `C_T_900_920_U2_S` | `87` | `e61d8ba393ae74de73d07e0cd291861bc3edeec1050cbc7d06a0750d67cba5c6` | `self.Sell` |
| Control buy | `stockbuy` | `Tick_B_902_905_Update_2` | `128` | `15feb9f96176a666f58fc2e7e5d32dad6f4779c01d7f0e2419bfad41a43f6afa` | `self.Buy` |
| Control sell | `stocksell` | `Tick_S_902_905_Update_2` | `47` | `093ba24ee300691afb7e4e8ef48c4d85e4ea92356c4c73a7795d3e059254b8f1` | `self.Sell` |

## C_T Time Hints

Static hints only:

- C_T buy has tokens `90500`, `91000`, `91500`, `92000`.
- Prior line inspection showed the first buy branch begins with `if 매수 and 시분초 < 90500`.
- The diagnostic window `09:02:00..09:05:00` therefore lies in the earliest C_T buy branch by static hint.
- C_T sell has tokens `92000`, `93000`, so the sell side may be mostly inactive inside `09:02..09:05` unless forced exits or engine state trigger it.

These facts are not treated as root-cause proof. P3 mixed-pair runtime evidence decides the workload axis.

## Control Reference

Previous page control run `ct_preflight_control_902_905_warm_20260605` passed on the same `2025-01-03 09:02..09:05` window with CSV/metrics, profit `149,567`, trades `1`, and MDD `2.99`.
