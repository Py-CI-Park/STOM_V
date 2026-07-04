# chart_sulsa 구조론 v7.0 조건식 마스터 카탈로그

> 상태: `hypothesis_seed` | 생성일: 2026-07-02 | 연구 레인 전용 (승격/export/live 사용 금지)
> 원천 문서: `C:/System_Trading/chart_sulsa_stom_quant_insight_report_v7_0.html` (파일명 `chart_sulsa_stom_quant_insight_report_v7_0.html`)
> 원천 문서 sha256: `454715a9faad0f6efcb0f24c12ad7dad0087a3d51afc5f9935c6d49c4b78f5d4`
> 데이터 원천: `ai_strategy_loop/brain/data/chart_sulsa_v7_conditions.json` — 본 카탈로그는 코드를 재추출하지 않고 위 JSON을 그대로 사용했으며, 25개 전 조건식의 `code_sha256` 재계산 일치를 확인했다.

**무근거 가설 시드: 모든 조건식/조합과 임계값은 차트술사 구조론 보고서 v7.0에서 추출한 검증되지 않은 가설이다. 백테스트/OOS 검증 이력이 없으며 검증된 사실로 취급하면 안 된다. 연구 레인 전용 (승격/export/live 사용 금지).**

## §1 연구 요약

차트술사 구조론 보고서 v7.0은 개인 트레이더의 구조론(원문 마스터 프롬프트 0~28장, §1.15)을
STOM 조건식 체계로 재구성한 문서다. 리포지토리에는 이 원리 체계가 **3계층 문서**로 정착되어 있다.

| 계층 | 문서 | 내용 |
|---|---|---|
| 원리층 | `utility/ai_agent/system_prompt/v1/principles.md` | P0~P15 원리 16개 (원문 0~28장 재구성) |
| 제약층 | `utility/ai_agent/system_prompt/v1/constraints_checklist.md` | AI 금지사항 7개조(CSC-01~) + 검증 주의점의 기계 판정 기준 |
| 관용구층 | `utility/ai_agent/system_prompt/v1/idiom_dictionary.md` | 원리 개념 → STOM 변수 관용구 변환 사전 |

P0~P15 원리 개요:

| 원리 | 요지 |
|---|---|
| P0 | 목적과 해석 순서 (체결→거래량→종가→박스→도지→기능선→전환→매매→시나리오) |
| P1 | 체결 → 거래량 → 종가 |
| P2 | 종가 우선 원칙 |
| P3 | 박스/추세 이분법 |
| P4 | 지지대·저항대의 형성 원리 |
| P5 | 지지·저항 스위치 |
| P6 | 도지 = 압축된 박스 |
| P7 | 기능선과 기능선의 격 |
| P8 | 지지선 매수의 두 종류 |
| P9 | 눌림매매 구조와 급등주 생성 |
| P10 | 실패의 정의 = 진입 근거의 상실 |
| P11 | 익절 = 다음 기능선 |
| P12 | 갭 해석 |
| P13 | 사건거래대금 |
| P14 | 실전 적용 순서 |
| P15 | 요약 |

v7.0은 구조론을 세 실행 엔진으로 분리한다 (원문 §14):

- **1tick**: 09:00~09:30 장초반 전용. 미세 박스·미세 도지·초당 사건거래대금 중심.
- **1min**: 09:00~15:18 장중 전용. 1분 종가 기준 박스·도지·기능선 중심.
- **일봉 Quant Insight**: 장마감 후 종가 추천(본 카탈로그 대상 아님).

**경고 — 전 임계값 무근거 가설**: 원문 스스로 백테스트 미검증 가설 체계임을 명시하며,
본 카탈로그의 모든 수치 임계값(예: 돌파율 0.25, 폭 상한 1.2% 등)은 근거 없는 가설이다.
검증된 사실로 취급하거나 그대로 이식하지 말고, 부검(autopsy)/분위수 피드백으로 데이터에서 보정해야 한다.
OOS/스모크 검증 이력은 전부 `none`이다.

## §2 네이밍 체계 정의

| 구분 | 패턴 | 예시 |
|---|---|---|
| 원문 조건식 (25개) | `CSS_V7_{TICK\|MIN}_{B\|S}_{패턴}_{HHMM_HHMM}` | `CSS_V7_TICK_B_MICRO_BOX_BREAKOUT_0900_0930` |
| 최적화 변수형 (원문 §6) | `CSS_V7_OPT_{TICK\|MIN}_{B\|S}_MASTER_{HHMM_HHMM}` | `CSS_V7_OPT_MIN_B_MASTER_0900_1518` |
| 문서 권장 조합 | `CSS_V7_COMBO_{TICK\|MIN}_{NN}_{영문설명}` | `CSS_V7_COMBO_MIN_01_RETEST_PULLBACK_MASTER_SELL` |
| 향후 변형(파생 연구) | 기반 네임 + `_VAR{n}` 접미사 | `CSS_V7_MIN_B_RETEST_PULLBACK_SWITCH_0900_1518_VAR1` |

- `{TICK|MIN}` = 레인(1tick 스냅샷 / 1분봉), `{B|S}` = 매수/매도 side, `{HHMM_HHMM}` = 운영 시간창.
- DB 저장명은 조건식 id와 동일하게 유지한다 (저장 시 이름 충돌이면 저장하지 않고 충돌 보고).
- 변형(`_VAR{n}`)은 임계값/구조 변경 시마다 n을 증가시키고, 원본 id를 provenance에 남긴다.

## §3 조건식 전체 카탈로그 (25개)

아래 표의 25개 항목이 카탈로그 전량이다. **조건식 전문 코드 펜스는 파일당 800줄 제한**을
지키기 위해 본 카탈로그의 일부인 레인별 코드 부록 2개 파일에 수록한다. 부록의 코드는
`chart_sulsa_v7_conditions.json`의 코드 원문 그대로이며 아래 표의 sha256과 1:1 대응한다.

- 코드 부록(tick): [2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md)
- 코드 부록(min): [2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md)

### §3.1 1tick 레인 (09:00~09:30) — 9개

| 체계 네임 (=DB 저장명) | 한국어명 | side | time_window | 원리 | 원천 섹션 | code sha256 | 링크 |
|---|---|---|---|---|---|---|---|
| `CSS_V7_TICK_B_MICRO_BOX_BREAKOUT_0900_0930` | 1tick 매수: 미세 박스 상단 돌파 | buy | `09:00:00-09:30:00` | P1, P3, P13 | §4.1 | `5e1f7b2e5e94741a7a9f3b2bc017f93a63bcae443093ac4bc347d850cab26831` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_b_micro_box_breakout_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_b_micro_box_breakout_0900_0930.md) |
| `CSS_V7_TICK_B_MICRO_RETEST_SUPPORT_0900_0930` | 1tick 매수: 미세 리테스트 지지 | buy | `09:00:00-09:30:00` | P4, P5, P9 | §4.2 | `a5d1e54f5be1195b683bc8efd76cfa4bbd305b90872387b3d95843cb4549a5e4` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_b_micro_retest_support_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_b_micro_retest_support_0900_0930.md) |
| `CSS_V7_TICK_B_MICRO_DOJI_COMPRESSION_0900_0930` | 1tick 매수: 미세 도지 압축 돌파 | buy | `09:00:00-09:30:00` | P6, P13 | §4.3 | `77265a7c2f8d22ba44f7533d1b134fcc76f857950d1432dc06393b96faffde99` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_b_micro_doji_compression_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_b_micro_doji_compression_0900_0930.md) |
| `CSS_V7_TICK_B_MASTER_0900_0930` | 1tick 통합 매수식 | buy | `09:00:00-09:30:00` | P3, P5, P6, P9, P13 | §4.4 | `ba3421962481b8ad895794c11bc75e912dada2161bf2a13f940c71a40b816f25` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_b_master_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_b_master_0900_0930.md) |
| `CSS_V7_TICK_S_FAST_INVALIDATION_0900_0930` | 1tick 매도: 빠른 구조 무효화 | sell | `09:00:00-09:30:00` | P7, P10 | §4.5 | `eafcedd962bd9e45822f8729479b2ecfae833d0d656a8ff2ed6fb340b989505d` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_s_fast_invalidation_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_s_fast_invalidation_0900_0930.md) |
| `CSS_V7_TICK_S_MICRO_DOJI_FAIL_0900_0930` | 1tick 매도: 미세 도지 실패 | sell | `09:00:00-09:30:00` | P6, P10 | §4.6 | `f93b031c4a24d68ab3fb01b02b60150196d73b9f0b34a0d5a51fc19dc54807a0` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_s_micro_doji_fail_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_s_micro_doji_fail_0900_0930.md) |
| `CSS_V7_TICK_S_MASTER_0900_0930` | 1tick 통합 매도식 | sell | `09:00:00-09:30:00` | P6, P7, P10, P11 | §4.7 | `68bedcf47100da014064336f80e31451247902aefba2e2f6e617880de9f7331b` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_tick_s_master_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_tick_s_master_0900_0930.md) |
| `CSS_V7_OPT_TICK_B_MASTER_0900_0930` | 1tick 최적화형 매수식 | buy | `09:00:00-09:30:00` | P3, P5, P9, P13 | §6.1 | `c4775e12f4db4e7f54580c024202d7f8446ce304504c158b36bfcf9718a85179` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_opt_tick_b_master_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_opt_tick_b_master_0900_0930.md) |
| `CSS_V7_OPT_TICK_S_MASTER_0900_0930` | 1tick 최적화형 매도식 | sell | `09:00:00-09:30:00` | P7, P10, P11 | §6.2 | `72549be977ecf17e434b1c671c74180c7409ac3d187c467a3362b811cdaad16b` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_tick.md#css_v7_opt_tick_s_master_0900_0930) · [passport](../condition_passports/chart_sulsa/css_v7_opt_tick_s_master_0900_0930.md) |

### §3.2 1분봉 레인 (09:00~15:18) — 16개

| 체계 네임 (=DB 저장명) | 한국어명 | side | time_window | 원리 | 원천 섹션 | code sha256 | 링크 |
|---|---|---|---|---|---|---|---|
| `CSS_V7_MIN_B_BOX_LOW_SUPPORT_0900_1518` | 1분봉 매수: 박스 하단 지지 | buy | `09:00:00-15:18:00` | P2, P3, P4 | §5.1 | `af96faa1454bbe5fcd252a954c8cb528641917022434d80f79e57e0fe27b7e87` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_box_low_support_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_box_low_support_0900_1518.md) |
| `CSS_V7_MIN_B_BOX_BREAKOUT_EVENT_0900_1518` | 1분봉 매수: 박스 상단 사건봉 돌파 | buy | `09:00:00-15:18:00` | P2, P3, P13 | §5.2 | `439d934d35a8724f63756de210d1d70b5625448d761057ea6e6bdd9514192c9e` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_box_breakout_event_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_box_breakout_event_0900_1518.md) |
| `CSS_V7_MIN_B_RETEST_PULLBACK_SWITCH_0900_1518` | 1분봉 매수: 저항→지지 리테스트 | buy | `09:00:00-15:18:00` | P4, P5, P9 | §5.3 | `33f3b0ee27fac694f0d2844c2f7818448d0dde5533ba4dc5caa772bd033145e6` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_retest_pullback_switch_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_retest_pullback_switch_0900_1518.md) |
| `CSS_V7_MIN_B_DOJI_INTERNAL_SUPPORT_0900_1518` | 1분봉 매수: 도지 내부 지지 | buy | `09:00:00-15:18:00` | P6, P8 | §5.4 | `5b4253e997b470210e63935f3dd716952ab38c38432e3f4facc564014dd221fd` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_doji_internal_support_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_doji_internal_support_0900_1518.md) |
| `CSS_V7_MIN_B_DOJI_UPPER_BREAKOUT_0900_1518` | 1분봉 매수: 도지 상단 돌파 | buy | `09:00:00-15:18:00` | P2, P6, P13 | §5.5 | `6a5577983e88919a267533b54ce1a15f7ad851acdb4de032b71a7ca2ae1c902a` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_doji_upper_breakout_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_doji_upper_breakout_0900_1518.md) |
| `CSS_V7_MIN_B_GAP_RESISTANCE_PULLBACK_0900_1518` | 1분봉 매수: 갭 저항 돌파 후 눌림 | buy | `09:00:00-15:18:00` | P5, P9, P12 | §5.6 | `0b334d2278bfe4244ba9004822a5193ab73cc3fe4b0e7780e7c0930197464bad` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_gap_resistance_pullback_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_gap_resistance_pullback_0900_1518.md) |
| `CSS_V7_MIN_B_LONG_BOX_RAPID_RISER_0900_1518` | 1분봉 매수: 장기 박스 급등주 후보 | buy | `09:00:00-15:18:00` | P3, P9, P13 | §5.7 | `1ac90222b7c32f64a9465e3b47d0690538eef81a1d7113a3021df4f34a492021` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_long_box_rapid_riser_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_long_box_rapid_riser_0900_1518.md) |
| `CSS_V7_MIN_B_MASTER_0900_1518` | 1분봉 통합 매수식 | buy | `09:00:00-15:18:00` | P3, P4, P5, P6, P9, P12, P13 | §5.8 | `a9844ee87061a420672a8dcb5c0f866ca7cdb4fafcfe59d4fa2e44fe7d60173f` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_b_master_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_b_master_0900_1518.md) |
| `CSS_V7_MIN_S_STRUCTURE_INVALIDATION_0900_1518` | 1분봉 매도: 구조 무효화 | sell | `09:00:00-15:18:00` | P7, P10 | §5.9 | `f058b15c25349c0c9e13a145b5b2b57e3a7ddfddad490e70e4058bcd23085984` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_s_structure_invalidation_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_s_structure_invalidation_0900_1518.md) |
| `CSS_V7_MIN_S_BOX_LOWER_BREAKDOWN_0900_1518` | 1분봉 매도: 박스 하단 이탈 | sell | `09:00:00-15:18:00` | P3, P10 | §5.10 | `e5da09eb9e8184f52378c92ee5e32ac29b45028a29ece54a999d9a7d3c2cbfed` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_s_box_lower_breakdown_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_s_box_lower_breakdown_0900_1518.md) |
| `CSS_V7_MIN_S_DOJI_LOWER_BREAKDOWN_0900_1518` | 1분봉 매도: 도지 하단 이탈 | sell | `09:00:00-15:18:00` | P6, P10 | §5.11 | `82e26ce3dadc4c1d20bab4c327f8d263b9ee14183c54545c94bdda88bfe87480` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_s_doji_lower_breakdown_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_s_doji_lower_breakdown_0900_1518.md) |
| `CSS_V7_MIN_S_SUPPORT_TO_RESIST_REJECTION_0900_1518` | 1분봉 매도: 지지→저항 전환 | sell | `09:00:00-15:18:00` | P5, P10 | §5.12 | `fc08184c6bc7d31abdbdd8b8bae51a40e8aa3d8889214f9f71e1f065d12958ff` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_s_support_to_resist_rejection_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_s_support_to_resist_rejection_0900_1518.md) |
| `CSS_V7_MIN_S_TARGET_TRAILING_0900_1518` | 1분봉 매도: 목표선/트레일링 익절 | sell | `09:00:00-15:18:00` | P11 | §5.13 | `ca4263f1a352ca798237f737ed8a4729c0c08684435a81b3ee73b3336ab801b9` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_s_target_trailing_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_s_target_trailing_0900_1518.md) |
| `CSS_V7_MIN_S_MASTER_0900_1518` | 1분봉 통합 매도식 | sell | `09:00:00-15:18:00` | P5, P6, P7, P10, P11 | §5.14 | `1a2c00eb766f11e8db179a83afc44ddc2be35317bf6bdfa115fefa322971f442` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_min_s_master_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_min_s_master_0900_1518.md) |
| `CSS_V7_OPT_MIN_B_MASTER_0900_1518` | 1분봉 최적화형 매수식 | buy | `09:00:00-15:18:00` | P3, P4, P5, P9, P13 | §6.4 | `fed494cac9aab1b4e388458d5a996f275bec254f1cdf260e19a3876d3a27196b` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_opt_min_b_master_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_opt_min_b_master_0900_1518.md) |
| `CSS_V7_OPT_MIN_S_MASTER_0900_1518` | 1분봉 최적화형 매도식 | sell | `09:00:00-15:18:00` | P7, P10, P11 | §6.5 | `4a3e7575bc3ac7397f2543ae3e8a9b58408749e33e28f2f11b338b19d4490db1` | [코드](2026-07-02_chart_sulsa_v7_condition_catalog_code_min.md#css_v7_opt_min_s_master_0900_1518) · [passport](../condition_passports/chart_sulsa/css_v7_opt_min_s_master_0900_1518.md) |

비고:

- `CSS_V7_OPT_*` 4개는 통합(MASTER) 조건식의 최적화 변수형으로, `vars_ranges`
  (tick: `CSS_V7_OPT_VARS_TICK_0900_0930` 27변수 / min: `CSS_V7_OPT_VARS_MIN_0900_1518` 31변수)를 동반한다.
- 전 항목 `status = hypothesis_seed`, `source = chart_sulsa_v7_0`, oos_status = `none`.

## §4 조합 세트 (문서 명시 권장만)

원문 전체를 스캔한 결과, 매수+매도 조건식 조합을 명시적으로 권장하는 곳은 **§12.1 '권장 실행 순서' 한 곳뿐**이며
정확히 2세트를 지정한다(§4.4, §5.8 등 통합식 절에는 조합 산문이 없음). 문서에 없는 조합은 발명하지 않는다는
원칙에 따라 `ai_strategy_loop/brain/data/chart_sulsa_v7_combos.json`에는 아래 2세트만 수록했다.

| priority | combo_id | lane | 매수 조건식 | 매도 조건식 | 원천 |
|---|---|---|---|---|---|
| 1 | `CSS_V7_COMBO_MIN_01_RETEST_PULLBACK_MASTER_SELL` | min | `CSS_V7_MIN_B_RETEST_PULLBACK_SWITCH_0900_1518` | `CSS_V7_MIN_S_MASTER_0900_1518` | §12.1 |
| 2 | `CSS_V7_COMBO_TICK_01_MASTER_EARLY_SESSION` | tick | `CSS_V7_TICK_B_MASTER_0900_0930` | `CSS_V7_TICK_S_MASTER_0900_0930` | §12.1 |

- **CSS_V7_COMBO_MIN_01_RETEST_PULLBACK_MASTER_SELL** — 1분봉 1순위 조합: 저항→지지 리테스트 매수 + 1분봉 통합 매도. 원문 §12.1 '권장 실행 순서'가 명시한 1순위 검증 조합. 원문은 'CSS_V7_MIN_B_RETEST_PULLBACK_SWITCH_0900_1518 + CSS_V7_MIN_S_MASTER_0900_1518 조합부터 검증합니다'라고 기술하며, 일봉 Quant Insight 후보와 1분봉 리테스트 신호가 겹치는 종목을 우선순위 후보로 본다고 덧붙인다.
- **CSS_V7_COMBO_TICK_01_MASTER_EARLY_SESSION** — 1tick 2순위 조합(장초반 전용): 1tick 통합 매수 + 1tick 통합 매도. 원문 §12.1 '권장 실행 순서'가 명시한 2순위 검증 조합. 원문은 '그 다음 CSS_V7_TICK_B_MASTER_0900_0930 + CSS_V7_TICK_S_MASTER_0900_0930 조합을 장초반 전용으로 검증합니다'라고 기술하며, 1tick은 일봉/1분봉 후보 중 장초반 수급이 붙는 종목의 단기 진입 보조 시스템으로 사용한다고 명시한다.

## §5 출처·기록 원칙

- 본 카탈로그(코드 부록 2개 포함)와 combos JSON의 모든 항목은 이후 DB 저장 단계에서 산출되는
  **기계가독 provenance 원장(JSONL)과 1:1 대응**해야 한다. 원장 레코드에 대응 없는 카탈로그 항목,
  카탈로그에 없는 원장 레코드는 모두 프로세스 위반이다.
- 원장 레코드 필수 필드: 원천 문서 경로(`C:/System_Trading/chart_sulsa_stom_quant_insight_report_v7_0.html`), 문서 sha256(`454715a9faad0f6efcb0f24c12ad7dad0087a3d51afc5f9935c6d49c4b78f5d4`),
  원천 섹션, 조건식 code sha256, DB 저장명(=조건식 id), 저장 시각, 대상 DB 파일.
- DB 저장 규칙: INSERT만 허용(기존 행 UPDATE/DELETE 금지), 실저장 전 DB 파일 백업 필수,
  이름 충돌 시 저장하지 않고 충돌 보고. dry-run 기본, `--apply` 명시 시에만 저장.
  (주의: 기존 `strategy_generator.save_strategy_to_db`는 동일 이름에 UPDATE를 수행하므로 연구 레인에서 사용 금지.)
- 모든 항목은 `hypothesis_seed` 라벨을 유지하며 승격/export/live 접근을 하지 않는다.
- 관련 자산: `ai_strategy_loop/brain/data/chart_sulsa_v7_conditions.json`(조건식 원천),
  `ai_strategy_loop/brain/data/chart_sulsa_v7_combos.json`(권장 조합), `docs/research/condition_research/condition_passports/chart_sulsa/`(passport 25개).
