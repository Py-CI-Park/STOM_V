# 백테 분석 역량 전수 감사 (퀀트/통계/빅데이터 기법) — 2026-06-02

> 사용자 요청: "백테스팅 결과 분석 기능이 충분한지, 통계적 빅데이터·퀀트 분석 기법을 최대한 활용하는지 전수 검사."
> 방법: Workflow(6 에이전트) — fitness/autopsy/dashboard/CSV컬럼/추가스크립트 인벤토리 병렬 수집 → 프로젝트 맥락 가중 갭 감사.
> **한 줄 답: 충분하지 않음. 기본 지표는 갖췄으나 위험조정수익·분포·꼬리위험·과적합탐지·MFE/MAE 효율이 대거 미구현.**
> 프로젝트 핵심 제약: 소표본(연 40~120거래)·강한 레짐의존·과적합취약 → **정직한 과적합/강건성 평가가 최우선**.

## PART A — 커버리지 요약 (있음/부분/없음)

| 범주 | 있음 | 부분 | 없음 |
|------|------|------|------|
| 위험조정수익 | Calmar | — | **Sharpe·Sortino·Omega·Information Ratio** |
| 분포 | 승률·payoff | profit factor·손익분포 | **skewness·kurtosis** |
| 꼬리위험 | — | worst-N(부분) | **VaR·CVaR·최대연속손실** |
| 낙폭 | 깊이(MDD) | — | **지속기간·회복시간·Ulcer·time-under-water** |
| **과적합 탐지** | — | 다중검정(autopsy BH-FDR만) | **PBO/CSCV·Deflated Sharpe·White Reality Check** ← 최대공백 |
| 강건성 | holdout·MC·bootstrap CI | walk-forward·CV(연도분할) | 파라미터 민감도 |
| 거래수준 | 시간대분석(segment) | 보유시간 평균·**MFE/MAE(R_MAE 미사용!)** | edge ratio |
| 시계열 구조 | — | regime(휴리스틱) | autocorrelation·변동성군집·Markov |
| 벤치마크 | — | — | buy&hold·alpha/beta·지수대비 |
| 빅데이터/ML | — | 단변량 importance(Cohen's d) | **다변량 importance·거래 클러스터링** |

**핵심 미활용**: ①CSV에 `R_MAE`가 있는데 fitness/scoring 어디서도 안 읽음(MDD제어 직접신호) ②290세대 캠페인 DB가 있는데 PBO(과적합확률) 미산출 ③세대선택(우승자) 레벨 다중검정 보정 전무.

## PART B — 우선순위 TOP-8 (구현 권장순)

| # | 항목 | 난이도 | 왜(프로젝트 맥락) | 거점 |
|---|------|--------|------|------|
| 1 | **MFE/MAE Edge Ratio + R_MAE 효율** | 저 | R_MAE 미사용 = 최대 미활용. edge_ratio>1이면 "진입엣지 OK, 청산이 문제"를 분리 → refine 방향 데이터화 | fitness/score.py exit_quality 확장 |
| 2 | **PBO via CSCV (과적합 확률)** | 중 | 프로젝트 핵심 실패모드의 정답 진단. "IS우승의 OOS실패"를 단일 확률로. holdout보다 강건 | 신규 fitness/overfitting.py(read-only) |
| 3 | **Deflated/Probabilistic Sharpe** | 중 | 세대선택 다중검정 보정 전무 = 우승자 상향편의. DSR이 "N시도 중 운인가" 보정 | score.py Sharpe + overfitting.py |
| 4 | **분포 기술통계: skew/kurtosis/PF/VaR/CVaR/연속손실** | 저 | read-only 한 패스. 과발화 fat-tail/음의 skew 즉시 노출 | autopsy/analyze.py |
| 5 | **낙폭 해부: duration/recovery/Ulcer/TUW** | 저 | 현 MDD는 깊이 1점만. 참고자료 강점="깊은골 없는 매끄러운 우상향"=깊이×지속 | fitness/equity_series.py(데이터 기보유) |
| 6 | **부트스트랩 CI/MC 정식 승격 + 블록부트스트랩** | 중 | 소표본 graded CI 매우 넓음. 블록부트스트랩이 iid 손실군집 한계 보정 | 신규 fitness/resampling.py |
| 7 | **Purged Walk-Forward 정식화** | 중 | 현 holdout은 OOS 1구간뿐. WF는 다중OOS 일관성(거래 재슬라이스=재백테0) | fitness/holdout.py 확장 |
| 8 | **다변량 진입피처 importance + 거래 클러스터링** | 중 | 현 importance 단변량뿐. 조합엣지(체결강도×거래대금) → 생성측 피처주입 근거화 | 신규 autopsy/feature_importance.py |

## 권고 순서
- **즉시(저난이도·고가치·read-only·게이트무변경)**: #1 MFE/MAE → #4 분포/CVaR → #5 낙폭해부
- **핵심 전략과제(중난이도·최고가치)**: #2 PBO/CSCV → #3 DSR — 프로젝트 정체성("정직한 과적합평가")의 정답
- **공통 안전장치**: 모든 신규 지표는 진단필드/토글 기본OFF, 하드게이트·graded byte-identical 유지. R_MFE/R_MAE 한글-영문 이중표기 통일(침묵실패 차단).

> 전문 워크플로 결과: 세션 transcript / 본 문서가 압축본. 이번 세션 신규 `_temp_montecarlo`(bootstrap MC)·`_temp_ensemble`·`_temp_adaptive_multiyear`·`fitness/adaptive_timing.py`(커밋 `487156be`)가 강건성 항목 일부를 이미 메움.
