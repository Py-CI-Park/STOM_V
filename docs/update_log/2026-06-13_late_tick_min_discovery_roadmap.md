# 2026-06-13 후속 로드맵 — 09:20~09:25 tick + 09:00~15:00 min 발굴

## 1. 현재 결정 순서

1. **THETA V6 결정이 먼저다.**
   - 현재 사용 가능 조건식은 `THETA_seed_902905_06_B/S` 1개다.
   - V1~V5 증거는 충분하지만 최종 사용/보류/PROMOTE 기록은 `/ui/verdict.html`에서 사용자가 남겨야 한다.
   - 승격 시 병행 운용이 아니라 기존 시드 대체 관점으로 본다. 거래 중복도가 높아 보완 운용은 동일 베팅 중복에 가깝다.

2. **V6 이후 새 발굴은 두 갈래로 분리한다.**
   - tick 후반: 09:20~09:25를 시드 09:00~09:05와 분리해 별도 니치로 검증한다.
   - min 풀세션: 09:00~15:00까지 분봉 데이터를 쓰되, 시간대별 블록을 나눠 과발화와 마감 리스크를 따로 본다.

## 2. 새 개발 자산

### 2.1 tick 09:20~09:25 템플릿

- 템플릿: `ai_strategy_loop/tmap/templates/tick_late_0920_0925_continuation.json`
- 목적: 시드의 09:00~09:05 초반 스캘프와 다른 **후반 안정화/재가속** 신호 검증
- 기본 진입: `92000 <= 시분초 < 92500`
- 핵심 축:
  - 진입 시작/종료: 09:15~09:30 주변 민감도
  - 시총/가격/등락률/당일거래대금/전일동시간비/회전율
  - 평균 대비 초당거래대금 재유입
  - 체결강도, 초당 매수우위, 호가 지지, 이동평균 회복

### 2.2 min 09:00~15:00 템플릿

- 템플릿: `ai_strategy_loop/tmap/templates/min_session_0900_1500_rotation.json`
- 목적: tick 시드와 저상관인 **오전 이후/점심/오후 수급 지속** 구조 발굴
- 기본 진입: `90000 <= 시분초 <= 150000`
- 강제 청산: `시분초 >= 150000`
- 핵심 축:
  - 진입 시작: 09:00, 09:30, 10:00, 11:30, 13:00, 14:00
  - 진입 종료: 10:00, 11:30, 13:00, 14:00, 14:50, 15:00
  - 분당거래대금/분당매수수량/누적분당매수수량
  - 체결강도 평균 대비 개선, 이동평균 회복, 등락율각도

### 2.3 실행 프리셋

- 스크립트: `ai_strategy_loop/scripts/research_presets.py`
- tick 프리셋:
  ```powershell
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.research_presets tick_late_0920_0925 --out ai_strategy_loop/state/run_tick_late_0920_0925_config.json
  ```
- min 프리셋:
  ```powershell
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.research_presets min_full_0900_1500 --out ai_strategy_loop/state/run_min_full_0900_1500_config.json
  ```

## 3. 연구 실행 로드맵

### A. V6와 기준선 고정

1. 대시보드 실행:
   ```powershell
   PYTHONUTF8=1 python -m ai_strategy_loop --port 8770
   ```
2. `/ui/verdict.html`에서 THETA 판정 기록.
3. 판정 후 `theta_decision_card_20260611.md`와 이번 로드맵을 기준 문서로 묶는다.

### B. tick 09:20~09:25 지도 작성

1. 템플릿 스윕:
   ```powershell
   PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_sweep --template tick_late_0920_0925_continuation --config-json <train-config> --out-prefix tick_late_0920_0925
   ```
2. 기본 판단:
   - 09:20~09:25 기본점이 0건이면 시간/거래대금/전일동시간비를 완화한다.
   - 기본점이 과발화하면 시총/거래대금/체결강도/호가 조건을 조인다.
   - 09:20~09:25가 09:25~09:30보다 안정적인지 분리 평가한다.
3. 통과 후보만 동결 후 OOS:
   - 2022 전체
   - 2026-01~02
   - walk-forward 4창

### C. min 09:00~15:00 지도 작성

1. min 프리셋 생성 후 full-session warm 설정으로 실행한다.
2. 먼저 템플릿 스윕:
   ```powershell
   PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_sweep --template min_session_0900_1500_rotation --config-json <min-config> --out-prefix min_0900_1500
   ```
3. 시간대별로 분리 판정:
   - 09:00~10:00: 시초 확장형
   - 10:00~11:30: 오전 지속형
   - 11:30~13:00: 점심 전후 수급 재형성
   - 13:00~14:50: 오후 수급 지속
   - 14:50~15:00: 마감 전 리스크 구간
4. 15:00 이후 데이터는 사용하지 않는다. 청산도 15:00 강제 청산을 기본으로 둔다.

### D. 승격 기준

새 후보는 다음을 모두 통과해야 “사용 가능 후보”가 된다.

- train 양수 + MDD가 시드/THETA 대비 과도하지 않을 것
- 연도/구간별 붕괴가 없을 것
- 2022 OOS와 2026 OOS 모두 흑자 또는 최소한 한쪽 HOLD 사유가 사전선언돼 있을 것
- walk-forward에서 기권/붕괴가 반복되지 않을 것
- 슬리피지 1~2틱 스트레스에서 마진이 남을 것
- THETA와 거래 중복도가 너무 높으면 보완이 아니라 대체 후보로만 본다

## 4. 즉시 다음 명령

```powershell
PYTHONUTF8=1 python -m pytest tests/unit/test_time_cap_bucket_generation.py tests/unit/test_late_tick_and_min_templates.py tests/unit/test_research_presets.py -q
PYTHONUTF8=1 python -m ai_strategy_loop.scripts.research_presets tick_late_0920_0925 --out ai_strategy_loop/state/run_tick_late_0920_0925_config.json
PYTHONUTF8=1 python -m ai_strategy_loop.scripts.research_presets min_full_0900_1500 --out ai_strategy_loop/state/run_min_full_0900_1500_config.json
```

그 다음은 V6 판정 상태에 따라 tick late 또는 min full 중 하나를 먼저 실제 스윕한다.
