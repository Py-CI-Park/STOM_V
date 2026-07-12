# 2026-07-12 G3 — per-trade 퀀트 심층 분석 모듈(trade_quant) + /trade_quant 대시보드

## 무엇
- `ai_strategy_loop/autopsy/trade_quant.py::analyze_trade_table(csv_path, *, fine_time, top_n)`
  — 백테 per-trade CSV(back_static.py 헤더 기준, 컬럼 별칭 해석기)에서 확장 퀀트 지표 산출:
  expectancy(%/금액)·profit_factor·승률·payoff, 수익률 분포(왜도/첨도/q05~q95), 승패 streak,
  보유시간-수익 상관+분위 테이블, 매수시각 버킷 성과(5/30분, `pnl_unit` 명시),
  MFE/MAE 효율(실현/MFE 캡처율, 손실 MAE 비율), **최대낙폭 구간 내 손실 거래 기여 top-N**
  (분모=구간 총손실, share 합≤100%), B_* 진입 피처 승패 요약 + 프롬프트 환류용 NL 라인(최대 8줄).
  무예외 계약(status ok/no_data/error), 계산 불가 항목은 None+한국어 사유.
- 대시보드 `GET /trade_quant(run_id, gen_no<0=최신 ok, fine_time, top_n≤50 클램프)` —
  기존 /autopsy 패턴(지연 import·무예외·읽기 전용).

## 설계 결정
- PF/payoff 분모 0 → **None+사유** (fitness/score.py의 999.0 cap은 스코어 수식용 관례 —
  서술/환류용인 이 모듈과 의도적 분기, 코드 주석으로 고정).
- 낙폭 기여 정의(아키텍트 MEDIUM 반영): 최대낙폭 구간(peak+1..trough) 내 **손실 거래만**
  기여자로, share 분모는 구간 총손실 — 반등 거래 오귀속·share>100% 차단.

## 검증
- 단위 24종: 손계산 대조(기대값/PF/streak/낙폭)·적대 입력·pnl_unit·_parse_hhmm 형태별·
  엔드포인트 6종(모듈 부재/실패 시뮬). QA 레드팀: 독립 검산 19지표 오차 0, 적대 6종 무예외,
  실 DB tick/min trade_count 정합, 라이브 엔드포인트 200, numpy 직렬화 누출 0.
- 실 CSV 스모크(`artifacts/g3_trade_quant_real_csv_smoke.json`, 재현 커맨드 포함): 4,365거래 —
  PF 0.55, 최대연패 21, 손실 MAE 2.42배(기존 edge_ratio 부검 ~2.6배와 독립 정합).
