# 세션 핸드오프 — 재개 컨텍스트 (2026-06-02 대장정)

> **목적**: 매우 긴 세션(야간 캠페인→앙상블/적응형→분석 인프라→밴드 패러다임 P0) compact/새 세션 전 무중단 핸드오프.
> **브랜치**: `STOM_Version_2U_C-ai-strategy-loop` · **워크트리**: `STOM_V.wt-dev`
> **상태**: 트리 클린(전부 커밋) · 대시보드 정상 · 이번 세션 18커밋 · 전부 code-reviewer APPROVE·baseline 신규0·엔진/하드게이트 무수정·토글 기본 OFF.

---

## 0. 🔴 재개 명령어 (compact 후 / 새 세션 첫 메시지)
```
밴드 생성기 P1+P2 이어가자. docs/update_log/2026-06-03_session_handoff_resume.md +
docs/update_log/2026-06-02_band_generator_design.md + MEMORY.md ㉔ 먼저 읽고.
P0 완료됨(커밋 e63c7fc7, 시드902 밴드 round-trip 백테 비트동일 증명).
다음=P1(밴드 생성경로 옵트인+수동밴드 백테=밴드 좁혀서 연구 실증)→P2(Optuna 밴드
최적화=refine 튜닝불가 §3.16-D 직접 해소). 엔진/하드게이트 무수정·토글OFF·
code-reviewer·결정론 baseline 신규0 유지. 대시보드 python -m ai_strategy_loop(새 엔드포인트는 재시작 필요).
```

---

## 1. 🎯 활성 스레드 = 밴드 파라미터화 생성기 (가장 중요)
**무엇**: 조건식을 자유코드가 아닌 *고정 조건집합 위 밴드 벡터*(변수·[lo,hi]·active; 전범위=off, 좁히면=연구)로 표현. 사용자 핵심 통찰. **과발화 구조적 불가 + 튜닝 가능**(gradient 있는 벡터).
- **설계 문서**: `docs/update_log/2026-06-02_band_generator_design.md` (10섹션: 표현·컴파일러·생성기·Optuna 최적화·통합·백파인더 차용·일별승자·P0~P5 롤아웃·위험·정직결론). architect가 코드 검증 기반 작성.
- **✅ P0 완료(커밋 `e63c7fc7`)**: `brain/band_compiler.py`(BandSpec 6 op enum·FixedFragment reject_if 극성·McapBlock·TimeBranch·BandStrategy·compile_to_code 결정론·frozen) + `brain/seed_902_band.py`(시드 BUY를 밴드 인코딩) + 23테스트. **증명: 컴파일코드=시드 로직 md5-identical(98/98) + 백테 비트동일(+740,353·MDD0.88·6거래·graded1.72384 = 원본, run `p0_roundtrip`). 엔진 0수정.** 미배선.
- **다음 P1**: 밴드 생성경로 옵트인(config `band_generation_enabled` OFF) + 수동으로 시드 밴드를 좁혀(예 등락율[1,8]→[3,6]) 백테 = "밴드 조절=연구" 실증.
- **다음 P2**: **Optuna TPE 밴드 최적화**(1개월 탐색·trial cap 30·결정론 seed·objective=기존 graded 무수정). = **refine "튜닝불가"(§3.16-D) 본질 직접 해소** 첫 실험.
- P3: feature importance/일별승자→밴드 시드. P5: 다년 교차 레짐강건 밴드.
- **정직 한계(설계 §9)**: 밴드=축별 박스만 → 변수비율(`초당매수수량>매도총잔량*0.2`)·파생위치·상호작용 못담음→FixedFragment로. 템플릿 고정 천장. 밴드최적화≠레짐강건(holdout/다년 필수). 게이트통과≠수익(불변).
- **902 의미**: 09:02(시분초90200)·905=09:05. 시드=시초5분(09:00~05)을 902(0~2분)+905(2~5분) 분기한 스캘퍼.

---

## 2. 이번 세션 커밋 체인 (최신순, 18개)
| 커밋 | 내용 |
|------|------|
| `e63c7fc7` | **P0 밴드 컴파일러 + 시드 round-trip 증명** |
| `7e5e7a8c` | 밴드 생성기 architect 설계 문서 |
| `6ddec545` | per-segment 승리-변수 feature importance (사용자 아이디어 정식구현) |
| `9aa51e7f` | edge_ratio→청산 프롬프트 환류 (exit_edge_feedback_enabled) |
| `320f9424` | MFE/MAE edge ratio + 파노라마 시간대×시총 횡단분석 (감사 #1) |
| `81fb9b67` | 백테 분석역량 전수 감사 (갭 + top-8) |
| `487156be` | 적응형 레짐타이밍 정식 토글 (adaptive_timing) |
| `c1320696`·`d88f78a6` | 적응형 다년 OOS 2022~2026 통과 (위험조정 3.5배) |
| `d7bf7f05`·`b2645528` | 시드+AI 앙상블 + 2024 OOS + 몬테카를로 |
| `3b21736b` | 대시보드 검은화면 수정 (로컬 번들+ErrorBoundary) |
| `9856816c`~`6f0242ae`·`eacd44da` | 야간 생성연구 캠페인 E1~E19 + classification 토글 |

---

## 3. 핵심 연구 결론 (정직 종합)
1. **생성**: classification(시간×시총×등락률)+filter_gate+few-shot 도메인주입이 fresh 생성을 §3.17 백지붕괴에서 구제. 캠페인 19에피소드(`docs/.../2026-06-02_overnight_generation_research_campaign.md`). 단 AI는 윈도우/레짐 과적합(시드와 동형) — 교차연도/약세레짐서 실패. **시드 Tick_902가 다년강건 골드(2022~2025 연속흑자)**.
2. **🎯 적응형 타이밍(배포가능 최강결과)**: 시드 자기 자본곡선 추종(직전 lookback개월<0이면 OFF, 인과적·AI불필요). **2022~2026 다년 OOS 통과**: 시드 always-on +10.3M/MDD2.37M → 적응 +10.6M/MDD0.69M = **위험조정 3.5배**(고정앙상블 OOS실패와 대비). 분석전용 토글 + 대시보드 /adaptive_timing.
3. **앙상블**: 시드+AI 월별 결합은 2025 H1서 +79%/MDD−58%(MC로 강건)이나 **2024 OOS 전이실패** = 시드 약세조건부·고정캘린더 불가·적응형만 유효.
4. **분석 인프라 도약**: 감사로 갭 식별(Sharpe/CVaR/PBO/DSR 미구현) + edge_ratio·feature_importance 구현. **edge_ratio 발견: 시드 진입엣지 1.54 실재·mae_efficiency 0.20(청산갭)·손실MAE 2.6배(청산규율 비대칭)** = "진입OK·청산이 문제" 데이터 분리.

---

## 4. 신규 분석 도구·엔드포인트 (전부 분석전용·게이트무영향)
- **모듈**: `fitness/adaptive_timing.py`·`fitness/edge_ratio.py`·`fitness/feature_importance.py`·`brain/band_compiler.py`·`brain/seed_902_band.py`.
- **대시보드 엔드포인트(재시작 후 활성)**: `/adaptive_timing`·`/edge_ratio`·`/feature_importance` (run_id/run_ids·옵션). 예: `/feature_importance?run_ids=ens_seed_2022full,...2026full&axis=market_cap`.
- **temp 분석 스크립트(gitignored)**: `_temp_montecarlo.py`(부트스트랩 MC)·`_temp_ensemble.py`·`_temp_adaptive_multiyear.py`·`_temp_campaign_analyze.py`(니치)·`_temp_winning_features.py`(승리변수)·`_temp_band_structure.py`(DB 밴드구조)·`_temp_p0_roundtrip.py`.
- **생성 토글(기본 OFF·byte-identical)**: classification_generation_enabled·exit_edge_feedback_enabled·adaptive_timing_enabled·require_filter_gates·few_shot_enabled·mdd_control_enabled 등.

## 5. 감사 잔여 우선순위 (분석역량 갭, `docs/.../2026-06-02_analysis_capability_audit.md`)
즉시(저난이도 read-only): ✅#1 MFE/MAE(완료) · #4 분포/CVaR · #5 낙폭해부(Ulcer/duration). 핵심전략: **#2 PBO/CSCV(과적합확률)·#3 Deflated Sharpe** = 프로젝트 정체성("정직한 과적합평가")의 정답.

## 6. 운영 주의 (불변식·인프라)
- **OOM**: 3년 풀유니버스 ~5세대 한계(과발화 메모리폭증). 1개월 백테당 24s 안전·3개월 70s·시드 저빈도 1년 안전. 밴드 패러다임은 과발화 구조적 차단=OOM 완화.
- **크래시 시 고아 엔진 정리**: ⚠️ 무관 python.exe(stom_rl·web.main) 상주 → **블랭킷 `taskkill /F /IM python.exe` 금지**. 외과적(loop PID만) 정리. 단 클린 exit은 엔진 자동정리(이번 세션 누적0).
- **대시보드**: `python -m ai_strategy_loop`→`http://127.0.0.1:8770/ui/`. **새 백엔드 엔드포인트는 재시작 필요**(uvicorn 무reload). 프론트(StaticFiles)는 디스크 즉시서빙.
- **불변식**: 엔진(backengine_*)·하드게이트(compute_fitness)·backtest/graph/ 무수정 · 신규 토글 OFF byte-identical · code-reviewer(opus) APPROVE · `PYTHONUTF8=1 pytest tests/unit/ -q -p no:randomly` 기존 7 failed 외 신규0 · git index.lock stale 시 `rm -f .git/worktrees/STOM_V.wt-dev/index.lock`.
