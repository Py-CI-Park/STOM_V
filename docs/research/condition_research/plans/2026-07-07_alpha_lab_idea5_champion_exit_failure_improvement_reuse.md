# 아이디어 5 — 챔피언 청산 실패·개선·재사용 기록 (2026-07-07)

관련 문서: `2026-07-07_alpha_lab_initial_five_synthesis_to_profitable_stom_conditions.md`, `2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_idea4_regime_gate_failure_improvement_reuse.md`, `2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`, `2026-07-07_alpha_lab_idea5_research_foundation.md`.

## 1. Verdict

아이디어 5(챔피언 증류·청산 최적화)는 **전역 청산 교체로는 기각**됐다. 원안 점수는 75점, 초기 5개 중 4위였고, 목적은 OOS 통과 챔피언의 실거래 원장에서 진입 필터와 청산 정책을 증류하는 것이었다(C-001). 리플레이 게이트는 강했지만, 전역 후보 `hard_stop -5 + time_stop 300`은 엔진 확인에서 거부됐다(C-008).

기각 이유는 명확하다. ΔEV 신뢰구간이 0을 가로질렀고, 2024/2025에서 방향이 역전됐으며, MDD가 5개 창 중 4개에서 악화했다. 따라서 현직 sell은 기준선으로 유지해야 한다(C-009). 다만 아이디어 5 전체가 사망한 것은 아니다. 향후에는 전역 교체가 아니라 조건부 time-stop 패치, 현직 절의 국소 임계값 이동, 병렬 청산 변종, cross-champion loss-tail veto 같은 가설만 별도 승인 후 검토할 수 있다(C-014). 본 문서 패키지는 소스 변경, DB 쓰기, 엔진 실행, 전략 등록을 승인하지 않는다(C-015).

## 2. Evidence claims

- C-001: 아이디어 5는 초기 75점, 4위였고 챔피언 거래 원장에서 진입 필터·청산 정책을 증류하는 제안이었다.
- C-002: 공통 원칙은 오프라인 발견을 먼저 하고 백테스트/엔진을 최종 심판으로 두는 것이다.
- C-008: P5 replay gate는 강했지만, global exit candidate `hard_stop -5 + time_stop 300`은 엔진 확인에서 기각됐다.
- C-009: P5 기각 사유는 CI가 0을 포함, 2024/2025 reversal, 5개 창 중 4개 MDD 악화이며, incumbent sell이 기준선으로 남는다.
- C-010: v4 등가중 4챔피언 앙상블은 2025-01~2026-02에서 수익 약 2,608,362, MDD 약 493,590/493,591, calmar 약 5.28을 기록했다.
- C-013: 2025-01~2026-02는 알려진 감사 증거이지 향후 연구의 fresh blind OOS가 아니다.
- C-014: 향후 Idea5는 replay를 최종 증거가 아니라 triage로 취급하고, 별도 승인된 엔진 확인을 최종 심판으로 둬야 한다.
- C-015: 이 문서 패키지로 소스 변경, DB 쓰기, 엔진 실행, 전략 등록은 승인되지 않는다.

증거와 추론을 분리하면, **증거**는 리플레이 통과와 엔진 기각이 동시에 존재한다는 점이다. **추론**은 리플레이가 폐기 대상이 아니라 후보 압축 도구로 재사용될 수 있다는 점이며, 이 추론은 어떤 청산 규칙의 현재 채택을 의미하지 않는다.

## 3. Failure/root cause

1. **리플레이와 엔진의 목적 차이**: fixed-entry replay는 진입 집합을 고정한다. 엔진은 청산 변경으로 슬롯 점유, 재진입, 체결 순서, 다음 기회 집합이 바뀐다. 리플레이 우위가 엔진 우위로 자동 이전되지 않는다.
2. **현직 매도식 과소모델링**: 오프라인 대조군은 현직 sell 전체가 아니라 단순 아날로그에 가까웠다. incumbent sell의 비격자 절, 절 순서, 상황별 방어 기능이 under-modeled 됐다.
3. **연도별 역전**: time_stop 300은 일부 과거 구간에서 도움처럼 보였지만 2024/2025에서 역전됐다. 전역 청산 교체는 레짐 의존성을 숨겼다.
4. **위험 지표 악화**: EV 점추정이 조금 좋아 보여도 CI가 0을 가로지르고 MDD가 4/5 창에서 나빠지면 배포 후보가 아니다(C-009).
5. **Winner’s curse**: 약 192개 조합 중 최상 후보를 고르는 구조는 다중비교와 승자의 저주에 취약하다. 최상 1개는 반복 측정에서 기대치가 낮아질 가능성이 크다.

따라서 실패의 본질은 “리플레이가 쓸모없음”이 아니라 “리플레이 최상 전역 후보를 현직 청산 교체로 바로 승격한 설계가 위험함”이다.

## 4. Reusable assets

- **강한 replay gate 자체**: 현직 청산 재현이 충분히 강했으므로, replay 인프라는 후보 triage로 재사용할 수 있다(C-008, C-014).
- **기각 기준선**: CI crossing zero, 2024/2025 reversal, MDD worse 4/5는 향후 후보 탈락 기준으로 재사용한다(C-009).
- **현직 sell 기준선**: incumbent sell은 과소모델링하면 안 되는 load-bearing baseline이다. 충분한 엔진 증거 전에는 교체 대상이 아니다.
- **v4 포트폴리오 맥락**: v4 등가중 앙상블 성과는 청산 변종을 단일 전략이 아니라 포트폴리오 MDD·calmar 기여로 평가해야 함을 시사한다(C-010).
- **감사창 구분**: 2025-01~2026-02는 이미 알려진 증거로만 쓰고 새 블라인드 OOS라고 주장하지 않는다(C-013).

## 5. Disallowed claims

- `hard_stop -5 + time_stop 300` 전역 교체를 채택하거나 재권고할 수 없다(C-008, C-009).
- replay 통과만으로 청산 후보가 성공했다고 말할 수 없다. replay는 triage이고 엔진 확인이 최종 심판이다(C-014).
- incumbent sell보다 새 청산이 우월하다고 주장할 수 없다. 현재 기준선은 incumbent sell이다(C-009).
- 2025-01~2026-02를 새 블라인드 OOS로 재사용할 수 없다(C-013).
- 문서만으로 엔진 실행, 전략 등록, DB 변경, 소스 변경을 진행할 수 없다(C-015).

## 6. Future hypotheses requiring approval

1. **조건부 time-stop**: 모든 거래에 300초 제한을 걸지 말고, 장기 보유 중 최고수익률이 낮고 현재 수익률도 부진한 거래만 자르는 패치를 검토한다.
2. **현직 절 국소 임계값 이동**: incumbent sell의 구조와 절 순서는 유지하고, 작은 범위의 threshold movement만 별도 봉인 후 측정한다.
3. **병렬 청산 변종**: 현직을 교체하지 않고 별도 소액 variant로 병렬 편입해 포트폴리오 MDD를 줄이는지 본다.
4. **Cross-champion loss-tail veto**: rr8_12 하나가 아니라 RR8_0, RR8_21, GPTAUTH_G8까지 공통 손실 꼬리에서 반복되는 조건만 후보로 남긴다.
5. **Replay as triage only**: replay는 후보 수를 줄이는 1차 필터로만 쓰고, 최종 판정은 별도 승인된 엔진 확인으로 한다(C-002, C-014, C-015).
6. **Winner’s curse 방어**: 후보군 수를 사전 제한하고, 최상 후보 하나가 아니라 연도별 방향성·손실 꼬리 감소·포트폴리오 MDD 개선의 반복성을 요구한다.
