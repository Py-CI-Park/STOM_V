# V5.0 — Live 밀도 재설계 (사장님 최우선 미완 직접 해소)

- 작성: 2026-07-19 · 브랜치: `v5-0-live-density` (from `feature/dashboard-v5-overhaul` @ 2268b709)
- 워크트리: `STOM_V.wt-v5` (서버 8771)

## 문제 (실측 근거)
v4 Live: `v4-research.jsx` hero-col이 모든 차트/패널을 **세로 스택** → FITNESS 단일 그래프 2782×520 지배,
전체 높이 18,136px(12.6화면). 3440에서 여러 그래프 동시 관찰 불가.

## 변경
1. **hero 세로 스택 → 2열 그리드**: Fitness·Equity·Profit·Quality를 `.v5-live-grid`(2열) 셀로 재배치.
2. **KPI 바 상단 이동**: `_V4Stats`를 그리드 위 상단으로.
3. **hero 높이 상한 320px**: `.v4-hero-primary` 캔버스 max-height 320(P4 울트라 bump 제압).
4. **상세 폴드 기본 접힘**: `_V4Fold` defaultOpen true→false(6개, 요약 상시+상세 클릭).
5. **텍스트 근거 밴드 압축(L2)**: `.v4-research-evidence-grid` 세로 나열 → 3열 compact.
6. **타이포 확대**: 페이지 제목 22px, 패널 제목 16px.

## 검증 (실측 before/after · 3해상도)
| 지표 | v4(before) | V5.0(after) | 플랜 기준 |
|---|---|---|---|
| hero 높이 | 520px | **300px** | ≤320 ✅ |
| 그리드 | 1열 2782px | **2열 1384px** | 2열 ✅ |
| scrollH/vh(3440) | ~12.6 | **1.74** | ≤2.0 ✅ |
| scrollH/vh(2560) | — | **1.73** | ✅ |
| scrollH/vh(1920) | — | 2.31 | 짧은 뷰포트 |
| 폴드 기본 | 6 펼침 | **0 펼침** | 요약+클릭 ✅ |
| 페이지 제목 | 16px | **22px** | ≥22 ✅ |

`artifacts/v5_0_after_{3440,2560,1920}.png`. (idle 상태 측정 — 러닝 시 온보딩 숨김으로 첫화면 밀도 추가 개선.)

## 남은 refine(후속)
- 러닝 상태 4그래프 first-screen 90% 노출 재측정(run 데이터 필요).
- 상단 프로세스 상황판 통합·단계별 자동전환은 V5.1.
