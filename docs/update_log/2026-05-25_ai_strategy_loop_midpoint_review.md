# AI 자율 조건식 루프 — 중간 점검 자료 (2026-05-25)

> 브랜치: `STOM_Version_2U_C-ai-strategy-loop` (off `STOM_Version_2U_C`)
> 관련 커밋: `fd68ef7f`(runner 버그픽스), `82f89621`(ai_strategy_loop 기능)
> 정본 계약: `ai_strategy_loop/controller/STATE_CONTRACT.md`
> 작업 상태(상세 로그): `.omc/progress.txt`(gitignore), 사양: `.omc/specs/deep-interview-ai-strategy-loop.md`, 합의 계획: `.omc/plans/2026-05-23_ai_strategy_loop_consensus_plan.md`

## 0. 결론 (한 줄)
백엔드 시스템 빌드는 **~90%** 완료됐고 충실히 합의안을 따랐으나, **궁극 목적("AI가 목표에 도달하는 좋은 조건식을 자율로 산출")은 아직 증명되지 않았다(~65%)**. 핵심 잔여 3: ① 수렴/가치증명 ② 프론트엔드 생성 ③ holdout 배선.

---

## 1. 원래 목적 & 방향 (재확인)
사람이 수동으로 하던 **조건식(매수/매도 전략) 연구 → 생성 → 백테 → 분석 → 개선**의 반복을, **AI(선호: gpt auth)** 를 두뇌로 **목표 도달까지 자율 수행**하게 하고, 전 과정을 **웹 대시보드(Claude Design 제작)에서 실시간 관찰·제어**한다. 새 브랜치에서, 실제 백테를 직접 돌려가며 단계별로 검증·개발한다.

## 2. 합의한 설계 결정 — 반영 현황
| 결정 | 반영 |
|------|------|
| 생성 단위 = 매수/매도 전략 코드 | ✅ |
| LLM 자유 작문 | ✅ |
| 적합도 = 위험조정(CAGR/MDD) + 복합(우상향·거래수·MDD) | ✅ |
| 완전 자율 + 최종 승인만 사람 | ✅ |
| provider = GPT-5.5 gpt auth (라이브) | ✅ |
| 대시보드 모니터+제어 / 시작설정 CLI=GUI 공유 스키마 | ✅ (백엔드) |
| exec 안전은 가볍게(과한 AST 가드 거부) | ✅ |
| MVP = 분봉(min) | ✅ |
| 과적합 가드 holdout 기본 OFF 토글 | ⚠️ 구현했으나 루프 미배선 → 토글 숨김(후속) |

## 3. 구축 완료 (검증 증거)
- **Phase 0** AI 전략 사전(`utility/ai_agent/system_prompt/v1`) — SetGlobalsFunc 181변수 기계검증.
- **Phase 1** provider(gpt auth Newsletter_AI 이식 + openrouter 추상화; 라이브 호출 성공) + 생성 브레인(timeframe-aware + token/variable-scope 가드 + compile/dry-run).
- **Phase 2** 복합 적합도(graded 선택압력 + 하드 게이트 졸업) + 자율 루프(상태 WAL·종료·견고성 백스톱·우승 export) + 수렴 메커니즘(graded·누적 히스토리·에러원인 피드백).
- **Phase 3** 부검(손익 거래 B_* 표준화평균차 진단 → 다음 세대 프롬프트 피드백).
- **Phase 4 백엔드** 상태계약(v1)·시작설정(CLI=GUI)·FastAPI/WS/제어/헬스·`python -m ai_strategy_loop` 진입점 + Claude Design 프론트 프롬프트(`dashboard/FRONTEND_PROMPT.md`).
- 검증: 100+ 신규 단위테스트, 회귀 baseline 7 유지(신규 0), 브랜치 게이트 `verify_nonrelease_sync` EXIT 0, 실제 백테(204 trades) + 부검 + 6세대 자율 실행 실거동, 코드리뷰(opus) HIGH 3/MEDIUM 5 반영.
- 부수: **baseline CLI 백테 버그(`runner:543 'len'→'shape'[0]`) 수정** — 9384bc98(V2.79 전파) 회귀, 정본 GUI와 동일하게 정정.

## 4. 정직한 드리프트/갭
1. **"백테 엔진 최초1회 시작"(상시 엔진)** 원안 vs 현재 **세대별 백테 서브프로세스**(~45초/세대). STOM 엔진이 일회성 설계라 상시 엔진은 .pyd/엔진 수정 필요(레인 비용 큼). 기능은 동등. → 현재 세대별 수용으로 진행.
2. **"GUI에서 실행"** — CLI 진입만(레인 규칙). 웹 대시보드가 GUI 역할.
3. **holdout 졸업 가드 미배선** — 토글 숨김(후속).
4. **프론트엔드 미생성** — 프롬프트 제공, 생성은 사용자 단계.
5. ⭐ **궁극 목적 미증명** — 루프 메커니즘은 작동하나 단기(6세대) 실험에서 게이트 통과 0. "좋은 전략을 실제로 찾는다"는 미입증.

## 5. 수렴 실험 결과 & 레버
- 실험1(6세대): 거래하는 유효 전략 생성됨(49·121거래) 그러나 전부 게이트 실패(손실/거래수/MDD), best_score 0(하드 게이트=선택압력 0).
- 실험2(graded+히스토리, 6세대): gradient·히스토리 주입 작동 확인(gen1 graded 0.859 기록·주입). 그러나 백테 exit=2 67%(=0거래, 진입 과엄격) + 6세대 표본 부족으로 미수렴. → 에러원인 피드백 추가(0거래→완화 지시).
- **수렴 레버(권장순)**: (1) 평가 스코프 안정화(단일종목5일=노이즈 → 소수 종목/긴 윈도우) (2) 15–20세대+ 장기 실행 (3) holdout 배선·게이트 튜닝.

## 6. 핵심 진행률 (2축)
| 축 | 진행률 |
|----|--------|
| 시스템 빌드 | **~90%** (7/8 스토리 + 수렴엔진 + 리뷰·커밋) |
| 운용·목적 달성 | **~65%** (프론트 미생성 / 수렴 미증명 / holdout 미배선) |

## 7. 남은 단계 — 담당별
### 🤖 Claude
| # | 할 일 | 진행 |
|---|------|------|
| C1 | **US-008 수렴**: 평가 스코프 안정화(소수 종목/긴 윈도우) + 15–20세대 장기 실행 + 분석 | 0% (진행 시작) |
| C2 | holdout 졸업 가드 배선 + 토글 재노출 + 테스트 | 0% |
| C3 | 프론트 연동 검증(사용자 zip 생성 후) | 대기 |
| C4 | LOW 5건 보안 하드닝(선택) | 0% |
| C5 | 푸시/PR(지시 시) | 0% |
| C6 | 좀비 PID 48480 정리, MEMORY.md 브랜치 갱신 | 0% |

### 🙋 사용자
| # | 할 일 | 진행 |
|---|------|------|
| U1 | **프론트엔드 생성**: `dashboard/FRONTEND_PROMPT.md` → Claude Design → zip → 브라우저 | 진행 중 |
| U2 | 방향 결정: (a) 상시 엔진 원안? (현재 세대별 수용) (b) PyQt GUI 버튼? (c) 푸시/PR? | — |
| U3 | 운용 파라미터·최종 전략 승인 | — |

## 8. 실행 방법
```powershell
python -m ai_strategy_loop --port 8770                  # 대시보드 백엔드 (/health)
python -m ai_strategy_loop.controller.loop --max-gen 12 # 헤드리스 자율 루프
```

## 9. 다음 행동 (병행)
- Claude: **C1(스코프 안정화 + 장기 실험)** 헤드리스 진행.
- 사용자: **U1(Claude Design 프론트 생성)**.
- 이후: C3 연동 검증 → C2 holdout 배선 → U3 운용·승인.
