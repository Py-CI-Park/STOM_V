# v5.6 UX Lift 계획 — 검수 라운드3 + Newsletter_AI 벤치마크 (2026-07-20)

## 0. "왜 계속 못 고치나"에 대한 답 (재발 방지 장치)
반복 실패의 공통 원인: ① 개방형 요구를 패치 수준으로 축소 ② 기본값/브라우저 저장상태/데이터 상태가 사장님 환경과 달라 검증이 어긋남 ③ 디자인 기준 문서 부재로 라운드마다 즉흥 판단.
→ 이번 라운드부터 **(a) design.md 계약**(모든 시각 변경은 문서 기준으로), **(b) 기하 게이트**(fits·겹침·높이편차), **(c) 사장님 상태 재현 검증**(구 localStorage 주입·실데이터 run 선택), **(d) 벤치마크 채택 목록** 4장치를 상시 운영한다.

## 1. Newsletter_AI 벤치마크 검토 (D:\...\Newsletter_AI)
| 채택 | 내용 | 반영 |
|---|---|---|
| ✅ | `DESIGN.md` 디자인 계약(Atmosphere/Color token/Typo/Spacing 4px 배수/Components/Motion/A11y+debt) | U10 — 대시보드 `design.md` 신설 |
| ✅ | 템플릿형 HTML 리포트 생성기(`generators/html_report.py`, 표지·계층·mail-safe 계약) | U12 — run 보고서 v3 디자인 시스템 템플릿 |
| ✅ | `utils/debug_logger.py` + logs/ 관찰성 | U9 — 백엔드 링버퍼 로그 API + 프론트 에러 버퍼 + 설정탭 로그 뷰어 |
| ✅ | 검증 viewport 계약(375/768/1280) 개념 | 기하 게이트 3해상도(3440/2560/1920)에 명문화 |
| ⏸ | Next.js 프론트 스택 | 현 esbuild/전역 컴포넌트 체계 유지(이식 비용 대비 이득 낮음) |

## 2. 요구 원장 (이번 지시 전수)
- [x] **U1** 상황판 제목 영어화("LIVE RESEARCH BOARD") + UX 개선
- [x] **U2** 현재세대 카드와 KPI(현재세대·fitness·MDD·tokens) **통합 단일 카드**(중복 제거)
- [x] **U3** 상황판 4차트 높이 증대(356→460, 플롯 flex 충전) — 가독성
- [x] **U4** 라이브 매트릭스 셀 높이 증대(480→560) + **3열 배치 옵션**(2/3/4)
- [x] **U5** 백테 스테이지 4열 선택 시 실제 4열(스팬 제거)
- [x] **U6** 초기 화면: 연구 중=해당 스테이지, 아니면 **1. 생성**
- [x] **U7** 히스토리 속도 근본 수정 2차: `/runs` slim(3MB→수십KB)·`/history/index` TTL 캐시(3~6s→ms)·Compare/계보시각화 lazy fold
- [x] **U8** 벤치마크 검토(§1) 반영
- [x] **U9** 백엔드/프론트 로그 뷰어(설정탭) — 링버퍼, 읽기 전용
- [x] **U10** `design.md` 구축
- [x] **U11** 탭 순서 Live→History→**Reports**→성과→Backtest→Replay
- [x] **U12** 결과 보고서 내용 재구체화 + HTML 생성 스킬 v3(디자인 토큰 템플릿) · History↔Reports 연계 구조

## 3. 브랜치
`loop/process-research-pipeline` → **feature/dashboard-v5.6-uxlift** (통합) → 최종 태그 `V2UC-Dashboard-v5.6.0`.

## 4. 게이트
기하(플롯 fits 4/4·셀 균일·겹침0) + 성능(히스토리 진입 전송량 <300KB·서버 지연 엔드포인트 0) + 사장님 상태 재현 + 포커스드 pytest.
