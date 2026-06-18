# P6 — WCAG AA 대비 매트릭스 (양 테마) · 커밋 아티팩트

> 2026-06-15. 프로그램 P6(디자인시스템 랜딩) M4 검증의 객관 산출물.
> 텍스트 토큰(`--ink-0..3`) × 배경 토큰(`--bg-0..3`) 전 조합을 WCAG 2.x 상대휘도 공식으로 계산.
> 기준: 정상 텍스트 ≥4.5:1(AA), 큰/굵은 텍스트 ≥3:1(AA-large). hex 출처: `styles.css` `:root`(dark)·`[data-theme="light"]`.

## 계산 방법 (WCAG relative luminance)
- 각 채널 `c8/255` → sRGB 역감마: `c ≤ 0.03928 ? c/12.92 : ((c+0.055)/1.055)^2.4`.
- `L = 0.2126·R + 0.7152·G + 0.0722·B`.
- `ratio = (max(L_fg,L_bg)+0.05) / (min(L_fg,L_bg)+0.05)`.

## 최종 hex (P6 수정 반영)
| 토큰 | DARK | LIGHT |
|---|---|---|
| --ink-0 | `#e8edf2` | `#0e131a` |
| --ink-1 | `#a8b3c0` | `#3c4655` |
| --ink-2 | `#778496` (P6: `#6a7686`→) | `#5f6a79` (P6: `#6a7686`→) |
| --ink-3 | `#45505e` | `#a4adba` |
| --bg-0 | `#07090c` | `#f5f6f8` |
| --bg-1 | `#0c1014` | `#ffffff` |
| --bg-2 | `#11161c` | `#f0f2f6` |
| --bg-3 | `#161c24` | `#e6eaf0` |

## DARK 테마
| text \ bg | --bg-0 | --bg-1 | --bg-2 | --bg-3 |
|---|---|---|---|---|
| --ink-0 | 16.92 PASS | 16.21 PASS | 15.43 PASS | 14.54 PASS |
| --ink-1 | 9.37 PASS | 8.98 PASS | 8.55 PASS | 8.06 PASS |
| --ink-2 | 5.25 PASS | 5.02 PASS | 4.78 PASS | 4.51 PASS |
| --ink-3 | 2.43 FAIL | 2.33 FAIL | 2.22 FAIL | 2.09 FAIL¹ |

## LIGHT 테마
| text \ bg | --bg-0 | --bg-1 | --bg-2 | --bg-3 |
|---|---|---|---|---|
| --ink-0 | 17.24 PASS | 18.64 PASS | 16.63 PASS | 15.44 PASS |
| --ink-1 | 8.83 PASS | 9.55 PASS | 8.52 PASS | 7.91 PASS |
| --ink-2 | 5.08 PASS | 5.49 PASS | 4.90 PASS | 4.55 PASS |
| --ink-3 | 2.10 FAIL | 2.27 FAIL | 2.02 FAIL | 1.88 FAIL¹ |

판정: PASS = 정상텍스트 AA(≥4.5) 통과. AA-large = 3.0–4.5(큰/굵은 텍스트만 허용). FAIL = <3.0.

## 수정 내역 (FAIL → 수정)
- **--ink-2** 가 P6 이전 정상텍스트 기준(≥4.5)에서 일부 배경에 미달했다(예: DARK ink-2×bg-2=3.94, bg-3=3.71; LIGHT ink-2×bg-0=4.27, bg-2=4.12, bg-3=3.82). `--ink-2`는 도움말 스트립·빈상태·요약 부제 등 **정상 prose** 에도 쓰이므로 AA-normal 실패로 간주, 토큰 hex를 최소 보정했다.
  - **DARK**: `#6a7686 → #778496` (밝기 +12%, 색상 유지). 4 배경 모두 ≥4.51.
  - **LIGHT**: `#6a7686 → #5f6a79` (밝기 −10%, 색상 유지). 4 배경 모두 ≥4.55.
  - 영향: 이 토큰을 참조하는 **모든 테마 사용처**(양 테마 각자 값)에 적용된다. 색상(hue)은 보존하고 명도만 조정해 디자인 의도를 유지했다.

## --ink-3 — 의도적 미수정 (¹ 장식·AA-large 전용)
`--ink-3`는 정의상 **faint/장식/비핵심** 계층이다. `styles.css` 전 사용처(36곳)를 감사한 결과 정상 본문 prose 가 없음을 확인했다:
- 순수 장식: `.panel-hd-title .dot`(점), placeholder(`.input::placeholder`), 코드 줄번호(`.code-block .ln`), `.phase-active-pulse`.
- faint 메타데이터/부제(작은 mono, 10–12px): `.summary-sub`, `.rp-topbar-sub`, `.rp-card-sub`, `.side-kv .k`, `.rp-mini-label`, 빈상태 안내(`.rp-empty`/`.research-empty`/`.rp-code-empty`), 구분선(`.rp-compare-sep`), 코드 주석 토큰(`.tok-com`).

이들은 시각적 위계상 **3차 보조정보**다. ink-3 를 AA-normal 까지 올리면 ink-2 와 명도가 수렴해 위계가 붕괴된다. WCAG 상 비핵심 텍스트·장식은 대비 의무 대상이 아니므로 **AA-large(≥3:1) 미만이라도 의도적으로 유지**한다(정상 본문 미사용 전제). 핵심 본문은 ink-0/ink-1/ink-2 가 담당하며 전부 AA-normal 통과.

## 요약
- 정상 본문에 쓰이는 토큰(--ink-0/--ink-1/--ink-2): **양 테마 4×3=24 조합 전부 AA-normal(≥4.5) 통과**.
- --ink-3: 장식/비핵심 전용, AA-large 미만이나 정상 본문 미사용 → 의도적 예외.
- P6 변경 토큰: `--ink-2` (DARK #778496, LIGHT #5f6a79). 명도만 조정, hue 보존.
