# STOM 자동 조건식 탐색 시스템 — 구현 체크리스트

- 작성일: 2026-03-10
- 브랜치: `research/auto-condition-discovery`
- 기준 문서:
  - `docs/research/auto_condition_discovery_research.md`
  - 커밋 `2636e66` (`docs: auto condition discovery research 정합성 및 검증 설계 보강`)
- 목적: 연구 문서를 **실제 코드 작업 가능한 체크리스트**로 전환

---

## 1. 목표와 범위

이번 체크리스트의 목표는 아래 2가지를 구현 가능한 작업 단위로 쪼개는 것이다.

1. **Phase 0 — 코드베이스 정합성 정리**
2. **Phase 1 — 백테스트 결과 데이터 확장(B_*, S_*, R_*) + CSV 저장**

이번 체크리스트에서 **바로 구현하지 않는 것**:

- 자동 분석기(`analyzer.py`)
- 조건식 생성기(`condition_generator.py`)
- WFO 자동화(`wfo.py`)
- ML/RL 통합

즉, 이번 범위는 **데이터 수집 기반 구축**까지다.

---

## 2. 핵심 원칙

### 2.1 데이터 분리 원칙

- `B_*`: 매수 시점 feature
- `S_*`: 매도 시점 diagnostic
- `R_*`: 거래 결과 label / outcome

조건식 자동 생성 단계에서는 **B_*만 피처로 사용**한다.

### 2.2 구현 우선순위 원칙

1. 엔진이 실제로 값을 생성한다.
2. subtotal이 그 값을 깨지지 않게 전달한다.
3. dataframe이 컬럼을 보존한다.
4. GUI/DB/CSV 저장 경로가 그 값을 잃지 않는다.

### 2.3 정합성 원칙

`backengine_base.py`만 수정하면 불완전하다.  
반드시 **OMS 경로(`backengine_base_oms.py`)도 함께 반영**해야 한다.

---

## 3. 작업 대상 파일

### 3.1 필수 수정 파일

- `backtest/backengine_base.py`
- `backtest/backengine_base_oms.py`
- `backtest/back_subtotal.py`
- `backtest/back_static.py`
- `backtest/backtest.py`

### 3.2 영향도 확인 필요 파일

- `backtest/optimiz.py`
- `backtest/rolling_walk_forward_test.py`

### 3.3 참고 파일

- `trade/strategy_base.py`
- `utility/setting.py`
- `utility/static.py`
- `cli/report.py`
- `stom_backtest.py`

---

## 4. Phase 0 — 코드베이스 정합성 체크리스트

### 4.1 현재 데이터 흐름 파악

- [ ] `CalculationEyun()`의 현재 tuple 구조를 일반 엔진/OMS 엔진 각각 기록
- [ ] `BackSubTotal.CollectData()`의 언패킹 구조 기록
- [ ] `GetResultDataframe()`의 `columns1`, `columns2` 구조 기록
- [ ] `Total.Report()`의 DB 저장 / GUI 상세기록 / CSV 후보 위치 기록
- [ ] `optimiz.py`, `rolling_walk_forward_test.py`가 동일 스키마를 기대하는지 확인

### 4.2 공식 CLI vs library-only 경계 기록

- [ ] `stom_backtest.py`가 공식 shipped CLI임을 문서화
- [ ] `cli/ai_controller.py`, `cli/report.py`, `cli/optimizer.py`, `cli/sweep.py`를 library-only로 구분
- [ ] 이번 작업에서 새 CLI 옵션 추가 여부를 결정
- [ ] 새 CLI를 만들지 않는다면 `backtest.py` 저장 경로 우선 구현으로 확정

### 4.3 B_ / S_ / R_ 컬럼 명세 확정

- [ ] 주식 min / tick 공통 컬럼 목록 확정
- [ ] 주식 min 전용 컬럼 목록 확정
- [ ] 코인 / 선물과의 공통화 여부 결정
- [ ] `B_*`, `S_*`, `R_*` naming rule 문서화
- [ ] 1차 구현에서는 너무 큰 컬럼 폭을 피하기 위해 “핵심 우선 컬럼 세트” 선정

#### 권장 1차 핵심 우선 컬럼 세트

**B_***
- [ ] `B_현재가`
- [ ] `B_등락율`
- [ ] `B_당일거래대금`
- [ ] `B_거래대금증감`
- [ ] `B_체결강도`
- [ ] `B_시가총액`
- [ ] `B_회전율`
- [ ] `B_전일동시간비`
- [ ] `B_매수총잔량`
- [ ] `B_매도총잔량`
- [ ] `B_시분초`

**분봉 전용 B_***
- [ ] `B_분봉시가`
- [ ] `B_분봉고가`
- [ ] `B_분봉저가`

**S_***
- [ ] `S_현재가`
- [ ] `S_등락율`
- [ ] `S_체결강도`
- [ ] `S_매수총잔량`
- [ ] `S_매도총잔량`

**R_***
- [ ] `R_매수후최고수익률`
- [ ] `R_매수후최저수익률`
- [ ] `R_MFE`
- [ ] `R_MAE`

### 4.4 완료 기준

- [ ] 수정 대상/영향 대상 파일이 문서로 정리됨
- [ ] 1차 컬럼 세트가 확정됨
- [ ] 구현 우선순위가 명확함

---

## 5. Phase 1 — 데이터 확장 체크리스트

### 5.1 엔진: 매수 시점 스냅샷 저장 구조 추가

### `backtest/backengine_base.py`

- [ ] 매수 체결 시점에 B_* 스냅샷을 저장할 구조 설계
- [ ] `curr_trade_info` 또는 별도 dict에 B_* 저장 위치 결정
- [ ] tick/min 공통 필드 추출 helper 설계
- [ ] min 전용 필드 누락 시 기본값 정책 결정
- [ ] 매도 시점 `CalculationEyun()`에서 B_*를 tuple에 포함

### `backtest/backengine_base_oms.py`

- [ ] OMS 경로에도 같은 B_* 저장 구조 반영
- [ ] 추가매수 / 부분매도 시 B_* 기준을 “최초 진입”으로 할지 확정
- [ ] `추가매수시간`, `잔고없음` 로직과 충돌 없는지 확인
- [ ] `최고수익률`, `최저수익률`를 R_*로 연결

### 5.2 엔진: 매도 시점 및 결과 변수 추가

- [ ] 매도 시점 S_* 추출 helper 설계
- [ ] `R_매수후최고수익률`, `R_매수후최저수익률` 연결
- [ ] `R_MFE`, `R_MAE` alias 또는 동일값 처리 방침 결정
- [ ] 1차 구현에서 고점/저점 기반 R_*는 보류 여부 판단

### 5.3 subtotal 경로 동기화

### `backtest/back_subtotal.py`

- [ ] `CollectData()` 언패킹 구조 확장
- [ ] `opti_turn != 2` 경로가 기존처럼 요약용 데이터만 유지하는지 결정
- [ ] `opti_turn == 2` 경로에서 상세 데이터 확장
- [ ] subtotal 집계가 신규 컬럼 때문에 깨지지 않는지 확인

> 주의: 요약 통계용 ndarray는 계속  
> `보유시간, 매도시간, 수익률, 수익금, 수익금합계`  
> 중심으로 유지하는 편이 안전하다.

### 5.4 DataFrame 스키마 확장

### `backtest/back_static.py`

- [ ] `columns1`에 신규 raw tuple 컬럼 추가
- [ ] `columns2`에 최종 상세기록 컬럼 추가
- [ ] 기존 상세기록 컬럼 순서와 신규 컬럼 순서 규칙 확정
- [ ] `df_tsg['수익금합계']` 생성 이후 컬럼 정렬 확인

#### 권장 컬럼 순서

1. 기존 거래 기본 컬럼
2. `B_*`
3. `S_*`
4. `R_*`

### 5.5 저장 경로 확장

### `backtest/backtest.py`

- [ ] `Total.Report()`에서 확장된 `df_tsg` 유지 확인
- [ ] `backtest.db` 저장 시 신규 컬럼 보존 확인
- [ ] `./backtest/csv/` 디렉터리 자동 생성 추가
- [ ] UTF-8-SIG CSV 저장 추가
- [ ] GUI 상세기록 큐로 전달되는 DataFrame에 신규 컬럼 포함 확인

### 영향도 확인 파일

- [ ] `backtest/optimiz.py` 저장 경로가 같은 컬럼을 처리할 수 있는지 확인
- [ ] `backtest/rolling_walk_forward_test.py`도 동일 점검

### 선택 사항

- [ ] 가능하면 `cli/report.py`의 `save_csv()` 재사용 여부 검토

---

## 6. 구현 순서 권장안

### Step A — 최소 안전 리팩토링

- [ ] B_* / S_* / R_* 추출 helper 함수 이름만 먼저 정의
- [ ] 공통 helper를 일반 엔진 / OMS 엔진에 같은 방식으로 연결

### Step B — 엔진 tuple 확장

- [ ] `backengine_base.py` 반영
- [ ] `backengine_base_oms.py` 반영

### Step C — subtotal / dataframe 확장

- [ ] `back_subtotal.py`
- [ ] `back_static.py`

### Step D — 저장 및 노출

- [ ] `backtest.py`
- [ ] 필요 시 `optimiz.py`, `rolling_walk_forward_test.py`

### Step E — 검증

- [ ] 최소 smoke 실행
- [ ] 상세기록 DataFrame 컬럼 확인
- [ ] CSV 생성 확인
- [ ] backtest.db 신규 테이블 컬럼 확인

---

## 7. 검증 체크리스트

### 7.1 정적 검증

- [ ] `rg "CalculationEyun" backtest -n` 로 일반/OMS 경로 모두 반영 확인
- [ ] `rg "CollectData" backtest/back_subtotal.py -n` 로 언패킹 일치 확인
- [ ] `rg "GetResultDataframe" backtest/back_static.py -n` 로 columns 일치 확인

### 7.2 실행 검증

- [ ] 기존 백테스트 1회 실행 시 크래시 없음
- [ ] GUI 상세기록 DataFrame에 `B_*`, `S_*`, `R_*` 컬럼 노출
- [ ] `backtest.db` 저장 테이블에 신규 컬럼 포함
- [ ] `./backtest/csv/` CSV 파일 생성
- [ ] CSV를 pandas로 다시 읽었을 때 컬럼 누락 없음

### 7.3 회귀 방지 검증

- [ ] 기존 요약 통계(`수익금합계`, `MDD`, `TPI`) 동일 계산 유지
- [ ] `optimiz.py` / `rolling_walk_forward_test.py`가 깨지지 않음
- [ ] OMS on/off 모두 기본 동작 유지

---

## 8. 구현 시 의사결정 포인트

### 8.1 추가매수 전략의 B_* 기준

선택지:

1. **최초 매수 시점 기준만 유지**  
   - 장점: 학습 피처 해석이 쉬움
   - 단점: 추가매수 상황 반영 약함

2. **최종 평단 형성 시점으로 갱신**
   - 장점: 실제 포지션 형성 반영
   - 단점: 해석이 어려워짐

**권장:** 1차 구현은 **최초 매수 시점 기준**.

### 8.2 S_* 범위

1차 구현에서는 모든 S_*를 다 넣기보다:

- 가격
- 체결강도
- 잔량
- 매도조건

정도부터 시작하는 것이 안전하다.

### 8.3 R_* 범위

1차 구현은 `curr_trade_info`에서 바로 얻을 수 있는 값 위주로 간다.

- `R_매수후최고수익률`
- `R_매수후최저수익률`
- `R_MFE`
- `R_MAE`

보유기간 중 고가/저가 기반 excursion은 2차 확장으로 미뤄도 된다.

---

## 9. 완료 정의 (Definition of Done)

이번 체크리스트 범위 완료 조건:

- [ ] 일반 엔진 + OMS 엔진 모두 B_*, S_*, R_*를 생성
- [ ] subtotal / dataframe / report 경로가 신규 컬럼을 보존
- [ ] GUI 상세기록에서 신규 컬럼 확인 가능
- [ ] CSV 파일로 외부 분석 가능
- [ ] 기존 백테스트 핵심 성과지표 계산은 유지
- [ ] 영향 파일(`optimiz.py`, `rolling_walk_forward_test.py`) 검토 완료

---

## 10. 다음 단계 예고

Phase 0/1 완료 후 다음 우선순위:

1. `analyzer.py`
   - 분위수 분석
   - 시간대 분석
   - 시총 구간 분석
   - 최소 샘플 수 / FDR 적용

2. `condition_generator.py`
   - B_* 기반 자동 필터 코드 생성
   - 사람이 읽을 수 있는 근거 주석 포함

3. `wfo.py`
   - Purged Walk-Forward
   - out-of-sample 성과 검증

즉, **지금은 “자동 생성”보다 “좋은 학습 데이터셋 생산”이 우선**이다.
