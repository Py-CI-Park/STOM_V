# 2026-04-04 V2.74~V2.77 downstream baseline audit

## 체인 기준
- 공식 기준 브랜치: `STOM_Version_2`
- downstream 전파 순서: `2U -> 2U_C -> CLI_v267 -> research/init`
- 공식 소스 커밋:
  - `67bc0652` (`STOM V2.74`)
  - `03063b4d` (`STOM V2.75`)
  - `0dfce757` (`STOM V2.76`)
  - `5c69dc82` (`STOM V2.77`)

## 브랜치 기준선
| 브랜치 | HEAD | 비고 |
|---|---|---|
| `STOM_Version_2U` | `ca04b12a` | `.pyd` 제거, serial-key 제외 |
| `STOM_Version_2U_C` | `41323a93` | custom integration |
| `STOM_Version_2U_C_CLI_v267` | `b90b3c2f` | CLI contract + `backtest/graph/` 보호 |
| `research/init` | `7143ade3` | canonical base = `CLI_v267` |
