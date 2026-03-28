# B_/S_/R_ 결과 확장 이후 `optimiz.py` / `rolling_walk_forward_test.py` 영향도 검증

- 작성일: 2026-03-13
- 브랜치: `research/auto-condition-validation-pilot`
- 검증 목적: `B_*`, `S_*`, `R_*` 상세 결과 컬럼 확장 이후 기존 최적화/롤링 WFO 경로가 깨지지 않는지 명시적으로 확인한다.
- 관련 기준 문서:
  - `docs/research/2026-03-13_auto_condition_discovery_execution_master_checklist.md`
  - `docs/research/2026-03-13_auto_condition_discovery_code_review_and_improvement_plan.md`

---

## 1. 검증 질문

이번 점검에서 확인하려는 핵심 질문은 아래 3가지다.

1. `optimiz.py`, `rolling_walk_forward_test.py`가 확장된 상세 결과를 직접 tuple 언패킹해서 깨질 가능성이 있는가?
2. 두 파일이 `GetResultDataframe()` 반환값을 사용하는 방식이 B_/S_/R_ 확장 이후에도 안전한가?
3. 최소 정적/회귀 검증 기준에서 import/parse/기존 관련 테스트는 통과하는가?

---

## 2. 수행한 검증

### 2.1 정적 코드 검토

확인 파일:
- `backtest/optimiz.py`
- `backtest/rolling_walk_forward_test.py`

중점 확인 항목:
- `GetResultDataframe()` 호출 위치
- 고정 길이 tuple 언패킹 존재 여부
- `[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']]`처럼 핵심 컬럼만 다시 슬라이스하는지 여부
- `*extra` 같은 추가 컬럼 대응 패턴이 실제로 필요한지 여부

### 2.2 최소 실행 검증

실행 항목:

```bash
python3 -m py_compile backtest/optimiz.py \
  backtest/rolling_walk_forward_test.py \
  backtest/back_static.py \
  backtest/back_subtotal.py

python3 -m pytest -q tests/unit/test_backtest_result_expansion.py
```

### 2.3 보조 확인

실행한 보조 점검:

```bash
python3 - <<'PY'
from pathlib import Path
for path in ['backtest/optimiz.py', 'backtest/rolling_walk_forward_test.py']:
    text = Path(path).read_text(encoding='utf-8')
    print(path)
    print('GetResultDataframe:', text.count('GetResultDataframe('))
    print("core_cols_slice:", "[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']]" in text)
    print('contains_extra_unpack_pattern:', '*extra' in text)
PY
```

---

## 3. 검증 결과

### 3.1 `optimiz.py`

확인 결과:
- `GetResultDataframe()` 호출: **1회**
- 상세 결과를 직접 row 단위로 고정 언패킹하는 코드: **발견되지 않음**
- `GetResultDataframe()` 이후 사용 방식:
  - `self.df_tsg`, `self.df_bct`로 DataFrame 수신
  - 이후 핵심 컬럼만 다시 선택

핵심 코드 패턴:

```python
self.df_tsg, self.df_bct = GetResultDataframe(self.ui_gubun, list_tsg, arry_bct)
arry_tsg = np.array(
    self.df_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy(),
    dtype='float64'
)
```

해석:
- B_/S_/R_ 확장 컬럼이 `df_tsg` 안에 추가로 존재해도,
  최종 성과 계산 경로는 핵심 5개 컬럼만 다시 선택하므로 깨지지 않는다.
- 즉 현재 구조에서는 `*extra` 패턴이 **필수는 아니다**.

### 3.2 `rolling_walk_forward_test.py`

확인 결과:
- `GetResultDataframe()` 호출: **1회**
- 상세 결과를 직접 row 단위로 고정 언패킹하는 코드: **발견되지 않음**
- `GetResultDataframe()` 이후 사용 방식:
  - `self.df_tsg`, `self.df_bct`로 DataFrame 수신
  - 이후 핵심 컬럼만 다시 선택

핵심 코드 패턴:

```python
self.df_tsg, self.df_bct = GetResultDataframe(self.ui_gubun, list_tsg, arry_bct)
arry_tsg = np.array(
    self.df_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy(),
    dtype='float64'
)
```

해석:
- `rolling_walk_forward_test.py` 역시 확장 컬럼을 직접 언패킹하지 않는다.
- 요약 성과 계산용 배열은 핵심 5개 컬럼으로 재구성되므로,
  현재 B_/S_/R_ 확장과 충돌하지 않는다.

### 3.3 py_compile / 회귀 테스트

실행 결과:
- `py_compile` ✅ 통과
- `tests/unit/test_backtest_result_expansion.py` ✅ **4 passed**

의미:
- 결과 확장 핵심 유틸 경로(`GetResultDataframe`, subtotal 연계 등)는 최소 회귀 기준에서 정상 동작한다.

---

## 4. 결론 요약

- `optimiz.py`와 `rolling_walk_forward_test.py`는 현재 구조상
  **B_/S_/R_ 확장 컬럼 때문에 즉시 깨질 가능성이 낮다.**
- 두 파일 모두 상세 결과를 row 단위로 고정 언패킹하지 않고,
  `GetResultDataframe()` 반환 DataFrame에서 핵심 5개 컬럼만 다시 선택한다.
- 따라서 현재 단계에서 이 두 파일에 대해 **즉시 코드 수정은 필요하지 않다.**

즉, 이전 문서에서 `미확인`으로 남아 있던 항목은 이번 점검으로 다음처럼 정리할 수 있다.

- 상태: **명시적 정적 검증 완료**
- 판정: **회귀 징후 없음 / 즉시 수정 불필요**

---

## 5. 남은 주의사항

이번 점검은 "현재 확장 컬럼이 기존 최적화/WFO 경로를 깨뜨리지 않는가"에 대한 검증이다.
아래는 여전히 주의가 필요하다.

1. 향후 `optimiz.py`나 `rolling_walk_forward_test.py`가 B_/S_/R_ 컬럼 자체를 직접 활용하도록 바뀌면,
   그때는 별도 테스트가 추가되어야 한다.
2. 이번 검증은 구조/회귀 중심이며,
   실제 대규모 optimize / rolling WFO long-run 부하 테스트까지 포함한 것은 아니다.
3. 따라서 long-running 안정성은 별도 운영 검증 항목으로 남겨둔다.

---

## 6. 다음 단계

이번 단계가 끝났으므로, 마스터 체크리스트 기준 다음 우선순위는 아래다.

1. `P1-C` — auto-relax 적용 후 promote 재실행 및 성공 조합 탐색
2. 그 다음 `P3` — `analyzer.py` 테스트 보강
3. 그 다음 `P4` — `ml_factor_model.py` 테스트 보강

즉, 이제 가장 중요한 다음 액션은
**실제 promoted 성공 사례 1건 확보를 위한 promote 재실행**이다.
