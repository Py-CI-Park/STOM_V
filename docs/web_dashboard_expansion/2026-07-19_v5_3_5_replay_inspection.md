# v5.3.5 Replay 전수검사표 (U6)

- 검사 일시: 2026-07-19 · 서버: wt-v5 8771 · 방법: 소스 인벤토리 + 안전 프로브 + 실브라우저 렌더 검사.

## 1. 구조 인벤토리
- 프론트 **11모듈 4,352줄**: sim-live-chart(800)·sim-chart-subpanes(647)·sim-chart-engines(597)·sim-tab-root(584)·sim-tab-controls(473)·sim-tab-panels(306)·sim-chart-utils(288)·sim-signal-log(228)·sim-tab-utils(236)·sim-chart-shell(153)·simulation-charts(40). 외부 차트 라이브러리 없음(순수 캔버스).
- 백엔드: `/sim/health` + **WS `/sim/ws`**(simulation_api.py·replay_engine.py) — 일일 tick/min DB 리플레이 + 조건식 매매 오버레이.

## 2. 검사 결과
| 항목 | 결과 |
|---|---|
| /sim/health 실호출 | ✅ 200 · status/module/api_version |
| 탭 렌더(3440) | ✅ replay 탭 · ▶재생 컨트롤 · **1.00화면** · overflow 0 · pageError 0 |
| 키보드 | ✅ 소스에 ArrowRight/ArrowLeft/Space/keydown 처리 존재 |
| WS 스트림(/sim/ws) | ⏳ 운영 검사 대기 — 리플레이 시작은 DB 데이터 필요(`_database/` 게이트) |
| 재생/배속/스텝/시킹 동작 | ⏳ 운영 검사 대기(동일 사유) |
| 신호 마커 정확성 | ⏳ 운영 검사 대기 |

## 3. 개선 적용
- **BT 결과→리플레이 직행 동선**: 결과 조건식 밴드에 `▶ 리플레이에서 확인` 딥링크 추가(`/ui/chart-replay`). 조건식/기간 prefill 은 운영 검사에서 파라미터 계약 확인 후(v5.3.5b).

## 4. 판정
구조 건전(모듈 분해·WS 단일 소스·키보드 지원·1화면 레이아웃). 실동작(재생·마커)은 tick/min DB 필요 — **운영 run 검사 항목으로 이관**.
