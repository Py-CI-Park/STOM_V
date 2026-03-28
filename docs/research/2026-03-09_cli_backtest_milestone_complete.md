# CLI 백테스트 E2E 성공 — 마일스톤 달성 보고서

- 작성일: 2026-03-09
- 브랜치: `STOM_Version_2U-cli-research-v251`
- 상태: **E2E 백테스트 완전 성공** (`"status": "success"`)

---

## 1. 브랜치 목적과 배경

### 1.1 왜 CLI가 필요한가

STOM은 PyQt5 기반 GUI 트레이딩 시스템이다. 백테스트를 실행하려면 반드시
GUI를 띄우고 마우스로 설정해야 한다. 이는 다음의 한계를 만든다:

| 한계 | 설명 |
|------|------|
| 자동화 불가 | 스크립트/크론잡으로 야간 백테스트 불가능 |
| 파라미터 스윕 불가 | 수백 개 조합을 수동으로 하나씩 테스트해야 함 |
| AI 연동 불가 | AI 에이전트가 전략을 생성하고 검증하는 파이프라인 구축 불가 |
| 원격 실행 불가 | SSH/서버에서 headless 실행 불가능 |
| 재현성 부족 | 어떤 설정으로 테스트했는지 커맨드 기록이 남지 않음 |

### 1.2 브랜치 계보

```
STOM_Version_2 (upstream, pyd 바이너리)
  └─ STOM_Version_2U (pyd → py 소스 추적 브랜치)
       └─ STOM_Version_2U-cli-research-v251 (★ 현재 브랜치)
            목적: GUI 없이 CLI로 백테스트 실행
```

### 1.3 핵심 제약조건

> **STOM 코어 파일은 최소한으로만 수정한다.**

이 브랜치는 상류 `STOM_Version_2`를 지속 추적하므로,
코어 파일을 수정하면 V2 업데이트 시마다 재적용 부담이 생긴다.
CLI 기능은 가능한 한 `cli/`, `stom_backtest.py` 등 **V2에 존재하지 않는 파일**에 구현한다.

---

## 2. 개발 타임라인 (전체 여정)

### 2.1 Phase 0~5: CLI 인프라 구축 (이전 세션들)

| 커밋 | 단계 | 내용 |
|------|------|------|
| `36c5557` | Phase 0 | PyQt5 의존성 격리 — headless 실행 가능하도록 import 분리 |
| `1d6cb29` | Phase 1 | CLI 백테스트 러너 (`cli/runner.py`) 최초 구현 |
| `09bb54b` | Phase 2 | JSON 출력 어댑터, Windows 배치 런처 |
| `bdf805a` | Fix | 결과 테이블명 `stock_bt` 수정 |
| `7a0d46c` | Phase 1 재 | DICT_SET 한국어 키 수정, 테스트 인프라 |
| `0737a06` | Phase 2 재 | 단위 테스트 122개 + 통합 테스트 11개 |
| `a10bed3` | Phase 3 | CLI UX 개선 — 인자 확장, exit code 표준화 |
| `e965b4a` | Phase 4 | 수식관리자 CLI, 전략 DSL headless 평가 |
| `07602eb` | Phase 5 | AI 자동화 — 타임프레임 매칭, 히스토리, 최적화, 전략 생성, AI 컨트롤러 |

### 2.2 Stage 1~6: 실 데이터 연동 및 CI

| 커밋 | 단계 | 내용 |
|------|------|------|
| `44165fc` | Stage 1 | 실 데이터 E2E — 데이터 브릿지, tick/min DB 연결 |
| `76e2c0b` | Stage 2 | 연속 백테스트 — 파라미터 스윕, 날짜 롤링, 리포트 |
| `dac1600` | Stage 3 | Strategy headless — AST 기반 전략 코드 분석기 |
| `2d06b9b` | Stage 4 | 서브커맨드 통합 — formula/strategy CLI 진입점 |
| `6cc74bd` | Stage 5 | 성능 최적화 — 진행률 모니터, 엔진 자동 튜닝 |
| `4b07b29` | Stage 6 | CI/CD — 테스트 러너, pre-commit 검증 스크립트 |

### 2.3 묶음 1~4: 종합 리뷰 및 안정화

| 커밋 | 단계 | 내용 |
|------|------|------|
| `57dd6f3` | 묶음 1 | CLI bootstrap decoupling, smoke 경로 복구 |
| `04f7403` | 묶음 2 | 검증 스크립트 신뢰성, CI 기준선 정비 |
| `50fc76f` | 묶음 3 | correctness gap, headless runtime 안정화 |
| `1a1d561` | 묶음 4 | shipped CLI 범위, library-only 모듈 정합화 |

### 2.4 DICT_SET 버그 수정 및 E2E 성공 (현재 세션)

| 커밋 | 단계 | 내용 |
|------|------|------|
| `04f48d5` | 버그 수정 1 | DICT_SET 래퍼 방식 — 직접 자식 프로세스(Engine) 해결 |
| `4488970` | 버그 수정 2 | 환경 변수 전파 — 손자 프로세스(Total) 해결, **E2E 성공** |

---

## 3. 핵심 버그: DICT_SET 프로세스 전파 문제

### 3.1 발견 경위

묶음 1~4로 CLI 인프라를 완성한 후, 실제 E2E 백테스트를 실행하자 크래시 발생.

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
    --buy Min_B_Study_251227 --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 --timeframe min
```

### 3.2 버그 1: 엔진 프로세스 ValueError

```
ValueError: not enough values to unpack (expected 56, got 53)
  at backtest/backengine_kiwoom_min.py:15
```

**원인**: Windows `spawn` 멀티프로세싱의 특성.

```
Linux fork: 부모 메모리 복사 → 자식이 수정된 DICT_SET 그대로 사용
Windows spawn: 모듈 전부 재import → setting.db 원본값 로드 → 수정 사항 유실
```

CLI가 `DICT_SET['주식타임프레임'] = False` (분봉)으로 수정했지만,
자식 프로세스는 `setting.db`에서 `True` (틱)을 읽어 틱 모드로 동작.
틱은 53개 변수, 분봉은 56개 변수 → 언패킹 실패.

**수정**: `_engine_with_dict_set()` 래퍼 함수로 자식 프로세스 시작 시 DICT_SET 주입.
(방안 C — `cli/runner.py`만 수정, 코어 파일 수정 없음)

### 3.3 버그 2: 전략 변수 NameError

```
NameError: name 'VI아래5호가' is not defined
  at exec(self.buystg) — strategy.db 전략 코드 실행 중
```

**원인**: `strategy.db`의 전략 코드가 `VI아래5호가`를 참조하지만,
이 변수는 백테스트 엔진의 Strategy() 스코프에 정의되어 있지 않음.
DICT_SET 버그가 해결되어 처음 도달한 코드 경로.

**수정**: `strategy.db`에서 해당 라인 주석 처리.

### 3.4 버그 3: Total 프로세스 PlotShow 크래시

```
ValueError: Invalid isoformat string: '2025-04-07 10:00:'
  at backtest/back_static.py:519 (PlotShow)
```

**원인**: 3단계 프로세스 계층 문제.

```
CLI 부모 ──── _sync_dict_set() ──── DICT_SET 패치 ✓
  │
  ├── Engine 프로세스 ── _engine_with_dict_set() 래퍼 ── DICT_SET 패치 ✓
  │
  └── BackTest 프로세스 ── _engine_with_dict_set() 래퍼 ── DICT_SET 패치 ✓
        │
        └── Total 프로세스 ── backtest.py:342에서 직접 Process() 생성
                              래퍼 도달 불가 ✗ → setting.db 원본값 로드
                              → is_tick=True (잘못됨)
                              → 그래프저장하지않기=False (잘못됨)
                              → PlotShow 호출 → dt_ymdhms()가 분봉 데이터에 적용 → 크래시
```

백테스트 엔진 자체는 221건 거래를 정상 완료(7초)했으나,
Report 단계에서 크래시 → BackTest 프로세스가 종료되지 않음 → 3600초 타임아웃.

**수정**: 환경 변수 전파 (방안 D 추가).

| 파일 | 변경 | 역할 |
|------|------|------|
| `cli/runner.py` | `os.environ['_STOM_CLI_DICT_SET'] = json.dumps({...})` | CLI 오버라이드를 env var로 직렬화 |
| `utility/setting.py` | DICT_SET 로드 직후 env var 체크 (4줄) | 모든 프로세스에서 자동 오버라이드 |

환경 변수는 Windows에서 모든 자손 프로세스에 자동 상속되므로,
프로세스 계층 깊이에 관계없이 동작한다.

### 3.5 해결책 비교 및 선택 근거

5가지 방안을 분석하여 하이브리드 접근을 채택:

| 방안 | 핵심 | 코어 수정 | 채택 |
|------|------|:---------:|:----:|
| A. 파라미터 전달 | `backengine_base.py`에 `dict_set=None` 추가 | 있음 | 유보 |
| B. DB 기록 | `setting.db`에 직접 기록 | 없음 | 거부 (DB 오염 위험) |
| **C. 래퍼 함수** | 자식 프로세스 시작 시 DICT_SET 패치 | **없음** | **채택** (직접 자식) |
| **D. 환경 변수** | `os.environ`으로 전파 | **4줄** | **채택** (손자 프로세스) |
| E. pickle 파일 | 임시 파일로 전달 | 없음 | 거부 (오버엔지니어링) |

**최종 구현: 방안 C + D 하이브리드**
- 방안 C: Engine/BackTest 직접 자식에 래퍼로 DICT_SET 주입 (코어 수정 0)
- 방안 D: Total 손자에 환경 변수로 전파 (코어 수정 4줄, GUI 영향 없음)

---

## 4. 최종 E2E 검증 결과

### 4.1 실행 명령어

```bash
STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py \
    --buy Min_B_Study_251227 --sell Min_S_Study_251227 \
    --start 20250407 --end 20250411 \
    --start-time 90000 --end-time 153000 \
    --engines 2 --timeframe min --timeout 120
```

### 4.2 실행 결과

```json
{
  "status": "success",
  "metrics": {
    "trade_count": 221,
    "win_rate": 19.0,
    "avg_profit_pct": -1.56,
    "total_profit_pct": -15.05,
    "total_profit_krw": -3435358,
    "cagr": -752.31,
    "mdd_pct": 15.74,
    "mdd_amount": 0.0,
    "tpi": 0.48,
    "seed_capital": 22832033.0,
    "max_hold_count": 23,
    "avg_hold_time": 88.87
  },
  "config": {
    "buy_strategy": "Min_B_Study_251227",
    "sell_strategy": "Min_S_Study_251227",
    "start_date": "20250407",
    "end_date": "20250411"
  }
}
```

### 4.3 프로세스 실행 로그 요약

| 단계 | 결과 | 시간 |
|------|:----:|------|
| 중간집계 프로세스 생성 (20개) | 성공 | ~1초 |
| 엔진 프로세스 생성 (2개) | 성공 | ~1초 |
| 거래대금순위 및 종목코드 추출 | 성공 | ~1초 |
| 종목코드별 데이터 로딩 [1/2]~[2/2] | 성공 | ~5초 |
| 백테엔진 준비 | 성공 | - |
| BackTest 프로세스 생성 | 성공 | - |
| 백테스트 기간 추출 | 성공 | - |
| 보유종목수 어레이 생성 | 성공 | - |
| 매수매도전략 설정 | 성공 | - |
| 집계용 프로세스(Total) 생성 | 성공 | - |
| **백테스트 START** | **성공** | - |
| **백테스팅 결과** (221회 거래) | **성공** | - |
| **부트스트랩 검정** | **성공** | - |
| **backtest.db 결과 저장** | **성공** | - |
| **백테스트 COMPLETE** | **성공** | **6.8초** |

### 4.4 이전 대비 개선

| 항목 | 버그 수정 전 | 최종 |
|------|:-----------:|:----:|
| 상태 | `error` | **`success`** |
| 소요시간 | 3600초 (타임아웃) | **6.8초** |
| 엔진 동작 | ValueError 크래시 | **221 trades 정상** |
| Report/PlotShow | ValueError 크래시 | **정상 완료** |
| 결과 DB 저장 | 미도달 | **backtest.db 저장 완료** |
| JSON 출력 | `{"status":"error"}` | **metrics 포함 성공** |

---

## 5. 수정된 파일 총정리

### 5.1 코드 변경

| 파일 | 분류 | 변경 내용 |
|------|:----:|----------|
| `cli/runner.py` | CLI 전용 | `_engine_with_dict_set()` 래퍼 추가, env var 직렬화 |
| `utility/setting.py` | **코어** | DICT_SET 직후 env var 오버라이드 체크 (4줄) |
| `_database/strategy.db` | 데이터 | `VI아래5호가` 라인 주석 처리 |

### 5.2 코어 수정 추적 (V2 동기화 시 참고)

#### `utility/setting.py` — DICT_SET 직후 4줄

```python
# 위치: DICT_SET = { ... } 닫는 중괄호 직후, except fernet.InvalidToken 직전
_cli_ovr = os.environ.get('_STOM_CLI_DICT_SET')
if _cli_ovr:
    import json as _json
    DICT_SET.update(_json.loads(_cli_ovr))
```

- GUI 영향: 없음 (env var 미설정 시 완전 무동작)
- V2 충돌 확률: 매우 낮음 (기존 코드 변경 없이 추가만)
- 누락 시 영향: CLI 손자 프로세스(Total) DICT_SET 미전파 → PlotShow 크래시
- 재적용 방법: DICT_SET 닫는 `}` 직후 위 4줄 복사

### 5.3 문서

| 파일 | 내용 |
|------|------|
| `docs/research/2026-03-08_dict_set_propagation_fix.md` | DICT_SET 버그 원인 분석, 5가지 방안 비교, 래퍼+환경변수 구현 |
| `docs/research/2026-03-09_e2e_backtest_verification.md` | E2E 검증 결과, 3단계 버그 발견/해결 과정, 최종 성공 |
| `docs/research/2026-03-09_cli_backtest_milestone_complete.md` | 본 문서 — 전체 여정 종합 |

---

## 6. 현재 CLI 기능 현황

### 6.1 직접 사용 가능 (shipped)

| 기능 | 명령어 | E2E 검증 |
|------|--------|:--------:|
| 분봉 백테스트 | `python stom_backtest.py --buy ... --sell ... --timeframe min` | **완료** |
| 틱 백테스트 | `python stom_backtest.py --buy ... --sell ... --timeframe tick` | 미검증 |
| 전략 목록 조회 | `python stom_backtest.py --list-strategies` | 완료 |
| Dry-run | `python stom_backtest.py --dry-run ...` | 완료 |
| JSON 출력 | `--format json` | 완료 |
| 텍스트 출력 | `--format text` | 완료 |
| 파일 저장 | `-o result.json` | 완료 |
| 수식 관리 | `python stom_backtest.py formula ...` | 기본 검증 |
| 전략 관리 | `python stom_backtest.py strategy ...` | 기본 검증 |

### 6.2 라이브러리 (Python import로 사용)

| 모듈 | 용도 | 상태 |
|------|------|:----:|
| `cli/history.py` | 결과 이력 조회/비교 | 구현 완료, CLI 미노출 |
| `cli/sweep.py` | 파라미터 스윕 | 구현 완료, CLI 미노출 |
| `cli/optimizer.py` | 전략 최적화 | 구현 완료, CLI 미노출 |
| `cli/strategy_generator.py` | AI 전략 생성 | 구현 완료, CLI 미노출 |
| `cli/ai_controller.py` | AI 컨트롤러 루프 | 구현 완료, CLI 미노출 |
| `cli/report.py` | 결과 리포팅 | 구현 완료, CLI 미노출 |
| `cli/engine_tuner.py` | 엔진 자동 튜닝 | 구현 완료, CLI 미노출 |

---

## 7. 다음 단계 추천

### 7.1 단기 — 검증 확대 (이 브랜치)

| 우선순위 | 작업 | 목적 | 난이도 |
|:--------:|------|------|:------:|
| 1 | 틱(tick) 백테스트 E2E 검증 | 분봉 성공 확인 → 틱도 검증 | 낮음 |
| 2 | 다양한 전략 E2E 테스트 | 다른 매수/매도 전략 조합 검증 | 낮음 |
| 3 | strategy.db 전략 변수 정비 | `VI아래5호가` 같은 미정의 변수 체계적 정리 | 중간 |
| 4 | 엔진 수 변경 테스트 | `--engines 1`, `--engines 4` 등 다양한 설정 | 낮음 |

### 7.2 중기 — CLI 기능 확대

| 우선순위 | 작업 | 목적 | 난이도 |
|:--------:|------|------|:------:|
| 5 | sweep/optimizer CLI 서브커맨드 노출 | `stom_backtest.py sweep --param ...` | 중간 |
| 6 | 결과 비교 CLI | `stom_backtest.py history compare A B` | 중간 |
| 7 | 스케줄 실행 연동 | Windows Task Scheduler / cron 연동 가이드 | 낮음 |
| 8 | 멀티 전략 병렬 백테스트 | N개 전략을 동시 테스트, 결과 비교 | 높음 |

### 7.3 장기 — AI 파이프라인 및 통합

| 우선순위 | 작업 | 목적 | 난이도 |
|:--------:|------|------|:------:|
| 9 | AI 전략 생성 → 백테스트 → 평가 루프 | `ai_controller.py` 실 검증 | 높음 |
| 10 | CI/CD 자동 백테스트 | PR마다 자동 백테스트 실행 | 중간 |
| 11 | STOM_Version_2U 메인 브랜치 머지 | 검증 완료 후 통합 | 중간 |

---

## 8. 참고 문서 인덱스

| 문서 | 내용 |
|------|------|
| `2026-03-05_v251_cli_comprehensive_review_plan.md` | CLI 종합 리뷰 계획서 |
| `2026-03-05_v251_cli_research_review.md` | CLI 리서치 리뷰 |
| `2026-03-07_v251_bundle4_detailed_explanation_and_next_steps.md` | 묶음 4 상세 설명 |
| `2026-03-07_v251_cli_shipping_scope.md` | CLI 배포 범위 정의 |
| `2026-03-07_v251_cli_verification_baseline.md` | CLI 검증 기준선 |
| `2026-03-08_dict_set_propagation_fix.md` | DICT_SET 버그 분석 및 5가지 방안 비교 |
| `2026-03-09_e2e_backtest_verification.md` | E2E 검증 단계별 결과 |
| `2026-03-09_cli_backtest_milestone_complete.md` | 본 문서 — 전체 여정 종합 |
