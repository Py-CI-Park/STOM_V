# QSP7 구현·성과·후속 연구 통합 핸드오프

> 작성일: 2026-08-03
> 저장소: `C:/System_Trading/STOM/STOM_V.wt-dev`
> 브랜치: `codex/qsp7-trade-episode-research`
> 문서 작성 직전 HEAD: `9d5b3c0b`
> 출발 커밋: `e4ac882a32cdfc38e31ee85515a61c3c188ad4fb`
> 문서 역할: 이전 대화 없이도 현재 구현, 증거, 한계, 다음 작업을 그대로 이어받는 최상위 핸드오프
> 안전 경계: 운영 DB 쓰기, 실거래 반영, 전체청산 이후 시세 사용, OOS 재학습, 후보 자동 채택 금지

이 문서는 `HANDOFF_2026-08-01_QSP7_매도식연구.md`를 대체한다. 이전 문서는 초기 손실 해부와 당시 가설을 보존하는 역사 자료이며, 현재 구현 상태와 다음 순서는 이 문서를 우선한다.

---

## 0. 🧭 1분 요약

| 질문 | 현재 답 |
|---|---|
| 무엇을 만들었는가? | 공식 백테스트 결과를 매수·매도·잔여 가격 경로로 해부하고, 해석 가능한 매도 가설을 가상 재생한 뒤 공식 설계/OOS로 검증하는 QSP7 연구 워크벤치 |
| 페이지는 완료됐는가? | **10/10 완료**. 데이터 계약부터 History까지 화면 흐름과 핵심 API가 연결됨 |
| tick/min DB를 실제로 썼는가? | **예.** tick control 4,399건, min control 6,577건의 경로를 공식 거래와 결합함 |
| 매도식 변경 수익이 증명됐는가? | **아니오.** 현재는 control 재현과 후보 축소까지다. 변경 후보의 공식 설계/OOS 개선은 아직 0건 |
| 지금 시스템의 가장 큰 성과는? | “손실이 많은 매도 조건을 지우면 좋아진다”는 잘못된 인과 결론을 차단하고, 같은 진입의 이후 경로와 다른 조건의 최초 발동을 검토할 수 있게 된 것 |
| 지금 가장 큰 미완성은? | 연구 sidecar DB, 사람 전략 pattern catalog, 전체 DSL parity, 변경 후보 공식 설계/OOS 실행 |
| 현재 점수 | 방향성 8.5/10 · 구현 성숙도 7.8/10 · 실제 전략 개선 증명 2.5/10 |
| 다음 기본 개발 작업 | 기존 저장소를 재사용하는 멱등 sidecar 원장과 사람 pattern 검색 연결 |
| 다음 기본 연구 작업 | 사람 선택 후보 4~8개를 공식 설계구간에서 pair 실행하고, 통과 후보만 잠긴 OOS 실행 |

핵심 판정은 다음 한 문장이다.

> **연구 프로세스와 10개 화면은 구현됐지만, 수익성 성공은 아직 증명되지 않았다. 다음 단계는 더 많은 화면이 아니라 증거를 보존하는 원장과 실제 공식 설계/OOS 실행이다.**

---

## 1. 🎯 프로그램 목적과 QSP7의 역할

### 1.1 프로그램의 본래 목적

이 프로그램은 머신러닝이 정답 조건식을 자동 선포하는 시스템이 아니다. 사람의 경험과 기존 전략 문법을 보존하면서, AI가 방대한 공식 백테스트 결과와 tick/min 가격 경로를 더 빠르고 일관되게 해부해 **사람이 이해할 수 있는 조건식 가설**을 만들고 공식 엔진으로 검증하는 연구 시스템이다.

| 원칙 | 의미 |
|---|---|
| 인간 해석 가능성 | 최종 후보는 사람이 읽을 수 있는 STOM 조건식과 매매 시나리오여야 함 |
| AI의 역할 | 원인 후보 탐색, 증거 정리, 반증 제시, 조건 조합 제안, 반복 실험 자동화 |
| 공식 엔진의 역할 | 가상 분석을 채택 증거로 승격시키는 유일한 최종 권위 |
| 사람의 역할 | 전략 의도 확인, 후보 선택, 설계/OOS 승인, 운영 반영 승인 |
| ML/DL의 위치 | 선택적 발견 도구일 수 있으나 최종 판단·설명·승격 권위가 아님 |

### 1.2 목표 연구 흐름

| 단계 | 입력 | 계산·판단 | 출력 권위 |
|---:|---|---|---|
| 1 | 완료된 공식 백테스트 CSV | 파일 hash, schema, 전략, 비용, 기간, 전체청산 경계 확인 | 공식 원본 계약 |
| 2 | 실제 매수시각과 `B_*` | 수익·손실군, 분산·결측·0-only, 구간별 구분력 분석 | 관측 진단 |
| 3 | 실제 매도시각·사유와 `S_*`, `R_*` | 매도사유별 손익, MFE/MAE, giveback 분석 | 관측 진단 |
| 4 | 해당 종목 tick/min DB | 실제 매도 뒤부터 전체청산 전까지만 회복·악화·검열 계산 | 사후 경로 진단 |
| 5 | 원본 매도식과 진입 고정 경로 | 조건절별 최초 발동과 다른 매도조건의 선행 가능성 재생 | 자문 replay |
| 6 | 여러 매도·매수 가설 | 동일 진입 가상 결과, 근거·반증·위험 비교 | 후보 축소 자문 |
| 7 | 사람이 선택한 완전한 조건식 | 공식 설계구간 재백테스트와 baseline pair 비교 | 공식 설계 증거 |
| 8 | 설계에서 잠근 후보 | 비중첩 OOS 재백테스트와 사람 승인 | 공식 채택 증거 |

### 1.3 반드시 분리할 세 가지 권위

| 권위 | 가능한 표현 | 금지 표현 |
|---|---|---|
| 관측 attribution | “이 매도사유에서 손실이 많이 실현됐다” | “이 조건을 제거하면 그만큼 이익이 난다” |
| 가상·반사실 advisory | “동일 진입 가정에서는 60초 지연 정책이 후보 가치가 있다” | “공식 전략 수익이 이만큼 증가한다” |
| 공식 design/OOS | “완전한 후보 정책이 설계와 OOS에서 모두 통과했다” | OOS를 다시 학습에 사용하거나 자동 운영 반영 |

---

## 2. 🔒 바뀌면 안 되는 연구 경계

| 경계 | 현재 결정 | 위반 시 처리 |
|---|---|---|
| 전체청산 | 장 마감 강제청산은 유지하며 그 이전 청산 품질을 개선 | 전체청산 이후 가격을 사용한 결과는 폐기 |
| 미래정보 | `R_*`, 실제 매도 뒤 회복, 미래 최고·최저는 조건식 입력 금지 | 누출 후보로 차단 |
| tick/min | 초와 분의 시간 창, 함수, 후보 family를 분리 | 혼용 후보는 문법·단위 gate에서 차단 |
| CSV | 공식 결과의 불변 영수증으로 유지하고 SHA256 기록 | CSV 삭제·덮어쓰기 금지 |
| 시장 DB | 기존 tick/min DB는 read-only | 운영 `_database/` 쓰기 금지 |
| 전략 DB | 후보를 운영 전략 DB에 자동 등록하지 않음 | 사람 승인 전 저장·승격 금지 |
| 매수 고정 replay | 후보 축소용이며 포트폴리오·재진입 변화는 증명하지 못함 | 최종 채택에 단독 사용 금지 |
| 공식 비교 | matched/new/lost, 자금 점유, 재진입, 전체 포트폴리오를 함께 봄 | matched 거래만으로 채택 금지 |
| OOS | 설계에서 잠근 설정을 변경 없이 비중첩 기간에 실행 | OOS 재사용 시 최종 OOS 자격 박탈 |
| 실패 기록 | 0건·실패·미지원·차단 결과도 원장에 남김 | 실패 은폐·자동 삭제 금지 |

---

## 3. 🧾 현재 Git·런타임 스냅샷

### 3.1 Git 상태

| 항목 | 값 |
|---|---|
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `codex/qsp7-trade-episode-research` |
| 문서 작성 직전 HEAD | `9d5b3c0b` |
| QSP7 출발점 | `e4ac882a32cdfc38e31ee85515a61c3c188ad4fb` |
| QSP7 작업 파일 범위 | 문서 작성 직전 clean |
| 저장소 전체 | 기존 삭제 보고서와 다수 미추적 `.omo/`, `.gjc/`, `artifacts/`가 존재하며 사용자 소유로 간주 |
| 주의 | `git add -A`, 광역 정리, 삭제 복구, unrelated artifact 커밋 금지 |

### 3.2 대시보드 상태

| 항목 | 마지막 검증 | 현재 핸드오프 작성 시점 |
|---|---|---|
| dashboard release | `v5.14.0` | 소스에 존재 |
| app build | `44f84913` | 소스에 존재 |
| 연구 CSS cache key | `20260803a` | 소스에 존재 |
| 마지막 브라우저 QA | 2026-08-03, 8771, 콘솔 오류 없음 | 현재 8770/8771 listener 없음 |
| 재실행 주소 | `http://127.0.0.1:8771/?tab=backtest&ui=20260803a` | 서버 재기동 후 사용 |

현재 서버가 떠 있다고 가정하지 않는다. 다음 명령으로 현재 상태를 먼저 확인하고 필요할 때만 실행한다.

```powershell
Set-Location -LiteralPath 'C:\System_Trading\STOM\STOM_V.wt-dev'
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -in 8770, 8771 } |
  Select-Object LocalPort, OwningProcess
python -m ai_strategy_loop --host 127.0.0.1 --port 8771
```

8770/8771에 다른 프로세스가 있으면 PID와 명령행을 확인하기 전 종료하지 않는다.

---

## 4. 🧱 커밋별 작업 이력

| 순서 | 커밋 | 성격 | 핵심 내용 | 현재 의미 |
|---:|---|---|---|---|
| 1 | `e4ac882a` | 초기 핸드오프 | 매도 손실 해부 문서와 분석 스크립트 | 역사적 출발점, 현재 핸드오프가 대체 |
| 2 | `b6484549` | 설계 | 거래 에피소드·잔여 경로·반사실 권위 설계 | 인과 과장 방지 기준 확정 |
| 3 | `3dda4cb3` | 구현 | 실제 매도→전체청산 경로, 가상 매도, 공식 전이, History 수직 슬라이스 | QSP7 분석 골격 |
| 4 | `b316a11f` | 보정 | 전체청산 경계, tick/min 시간, 공식 pair 호환성, UI 표기 | 시간·비교 오류 방지 |
| 5 | `bf8deb5c` | 문서 | 방향성 점검, CSV/변수/조건 생성/UX/OOS 로드맵 | 최상위 판단 근거 |
| 6 | `324b4fea` | 문서 | 하이브리드 CSV+DB와 단일 파이프라인 실행 계획 | 저장 구조·순서 확정 |
| 7 | `24b4cbac` | 구현 | 공식 데이터 계약 페이지와 BacktestJobSpec 경계 연결 | 입력 신뢰성 표시 |
| 8 | `cb3b0d7e` | 구현 | 매수시점 `B_*` 전수 가용성·효과 해부 화면 | 매수 분석 누락 보완 |
| 9 | `203110aa` | 구현 | 매도 DSL replay, 5개 후보군, 공식/OOS gate, 폴링 보정 | 10단계 핵심 기능 완성 |
| 10 | `1318dee7` | 문서 | 실제 결과·점수·미증명 항목 갱신 | 구현과 수익 증명 분리 |
| 11 | `9d5b3c0b` | UI 보정 | 최신 연구 CSS cache key 갱신 | 브라우저 캐시 혼선 방지 |

---

## 5. 🖥️ 10개 페이지 상세 인수인계

> 페이지 10/10 완료는 “화면과 핵심 분석 흐름이 연결됐다”는 뜻이다. sidecar 저장과 공식 후보 성과가 완료됐다는 뜻은 아니다.

| # | 페이지 | 목적 | 주요 입력 | 화면에서 보는 결과 | 사람이 확인할 것 | 상태·남은 차이 |
|---:|---|---|---|---|---|---|
| 1 | 데이터 계약 | 잘못된 CSV·전략·비용·시간 경계로 연구하지 않게 함 | job, CSV, 전략 코드, 비용 정책, 전체청산시각 | SHA256, 행·열, schema, 기간, 비용, 전략 hash, 경계 출처·신뢰도 | 선택 job과 실제 전략·기간·전체청산이 일치하는지 | ✅ 화면 완료 · sidecar artifact registry 미완료 |
| 2 | 매수 해부 | 매수시점 변수를 빠짐없이 점검하고 손익군 구분력을 탐색 | `B_*`와 허용된 실행시점 `D_*` | available/nonzero/0-only/missing, 분포·손실구간 | 0과 missing을 구분하고 사후 라벨이 입력에 없는지 | ✅ 1차 완료 · FDR·fold·조건절 funnel 미완료 |
| 3 | 매도 해부 | 실제 손익이 어느 매도사유에서 실현됐는지 관측 | 실제 매도시각·사유, `S_*`, `R_MFE/R_MAE`, 비용 후 손익 | 매도사유별 건수·손익·승률·MFE/MAE | 손실 집중을 제거 효과로 오해하지 않는지 | ✅ 완료 · 인과 증명 아님 |
| 4 | 거래 경로 | 실제 매도 이후 전체청산 전 회복·악화·검열 확인 | 매수/매도시각, tick/min DB, 전체청산 경계 | 경로 chart, 후행 horizon, 회복/추락/검열 | 경계 밖 데이터와 데이터 공백 여부 | ✅ 완료 · 대규모 분석 성능 최적화 여지 |
| 5 | 매도식 추적 | 원본 `if/elif` 조건 중 실제 최초 발동을 재생 | 원본 매도식, 진입 전 lookback, 보유 중 시장 경로 | 조건절별 hit/false/unsupported, 최초 발동, 공식 시각 비교 | 미지원 함수를 추정하지 않았는지, tick/min 단위가 맞는지 | ✅ 핵심 완료 · 181개 런타임 함수 전체 parity 아님 |
| 6 | 가상 매도 | 동일 진입에서 여러 보유·회복·이익보존 가설을 후보 축소용으로 비교 | 고정 진입과 전체청산 전 경로 | 가상 exit·delta·MFE/MAE·검열 | 가상 delta를 공식 수익으로 읽지 않는지 | ✅ 완료 · 포트폴리오/재진입 효과 미반영 |
| 7 | 조건식 후보 | 인간이 이해할 수 있는 서로 다른 가설 family를 생성 | 매수·매도·경로 evidence | 손실 방어, 이익 보존, 수익 반납, 시간 가치, 마감 관리 후보 | 근거·반증·위험·timeframe·변경절 | ✅ 5개 family · 사람 pattern/LLM evidence pack 미연결 |
| 8 | 공식 pair | baseline과 완전한 후보 정책의 공식 결과 비교 | 공식 job 2개 | matched/new/lost, 손익 delta, 기간·전략 호환성 | 동일 매수/기간/timeframe인지, 재현성 오차가 없는지 | ✅ 비교 경로 완료 · 변경 후보 공식 실행 미완료 |
| 9 | OOS 채택 | 설계와 비중첩 OOS가 모두 개선될 때만 채택 가능 표시 | design pair와 OOS pair | READY/BLOCKED, 기간 겹침, 개선 여부, blocker | OOS가 설계에 재사용되지 않았는지 | ✅ gate 완료 · 실제 통과 후보 0건 |
| 10 | History | 진단·후보·공식 비교·기각을 숨기지 않고 추적 | 분석 event와 공식 pair | append-only 연구 기록 | 실패·0건·unsupported가 보존되는지 | ✅ 1차 완료 · 정규 SQLite 원장·migration 미완료 |

### 5.1 페이지의 올바른 사용 순서

| 순서 | 사용자 행동 | 다음으로 넘어가는 조건 |
|---:|---|---|
| 1 | 공식 job을 선택하고 데이터 계약 확인 | CSV·전략·비용·기간·경계가 모두 설명 가능 |
| 2 | 매수 해부에서 변수 가용성과 손실 구간 확인 | 사후정보 없는 유효 변수만 남음 |
| 3 | 매도 해부에서 손실·이익 실현 구조 확인 | 연구할 cohort와 매도 가설을 선택 |
| 4 | 거래 경로에서 회복·악화·검열 확인 | 실제 시세 coverage와 경계가 충분 |
| 5 | 매도식 추적에서 원본 최초 발동 검증 | 공식 시각과 replay가 일치하거나 차이가 설명됨 |
| 6 | 가상 매도로 후보 축소 | 비용·검열·반증을 통과한 소수 후보만 남음 |
| 7 | 조건식 후보를 사람이 검토 | 서로 다른 family 4~8개, 숫자만 다른 복제 제외 |
| 8 | 공식 설계 pair 실행·비교 | 비용 후 손익·MDD·거래수·전이가 gate 통과 |
| 9 | 설정을 잠그고 비중첩 OOS 실행 | 설계와 OOS가 모두 통과 |
| 10 | 채택 또는 기각 사유를 History에 확정 | 사람 승인 전 운영 반영 없음 |

---

## 6. 🧩 구현된 코드와 책임 경계

| 영역 | 주요 파일 | 책임 |
|---|---|---|
| 거래 경로 모델 | `ai_strategy_loop/autopsy/trade_path_models.py` | 공식 거래·시장 point·경계·전략 source typed 계약 |
| 시장 경로 로더 | `ai_strategy_loop/autopsy/market_path.py` | tick/min DB read-only 조회와 경로 변수 로딩 |
| 경로 분석 | `ai_strategy_loop/autopsy/trade_path_analysis.py` | 회복·악화·검열·coverage 계산 |
| 매도 DSL replay | `ai_strategy_loop/autopsy/sell_dsl_replay.py` | 원본 조건절, 파생 대입, first-trigger, 미지원 차단 |
| 데이터 계약 | `ai_strategy_loop/dashboard/trade_contract.py` | CSV/schema/전략/비용/전체청산 경계 계약 |
| 연구 API | `ai_strategy_loop/dashboard/trade_path_api.py` | 분석·후보·비교·History route 조정 |
| 매도 trace API | `ai_strategy_loop/dashboard/sell_dsl_api.py` | typed first-trigger 응답과 실제 exit 비교 |
| 공식/OOS API | `ai_strategy_loop/dashboard/trade_path_official_api.py` | pair 비교와 설계/OOS 채택 blocker |
| 후보 생성 | `ai_strategy_loop/revision/sell_proposer.py` | tick/min별 5개 가설 family 생성 |
| 연구 UI 조정 | `ai_strategy_loop/dashboard/frontend/bt-trade-path-tab.jsx` | 10단계 상태·폴링·탭 흐름 |
| 신규 UI | `bt-data-contract.jsx`, `bt-entry-autopsy.jsx`, `bt-sell-dsl-trace.jsx`, `bt-oos-gate.jsx` 등 | 페이지별 증거와 경고 표시 |
| UI 스타일 | `ai_strategy_loop/dashboard/frontend/trade-path.css` | 경로·trace·OOS·반응형 레이아웃 |
| 테스트 | `tests/unit/autopsy/test_sell_dsl_replay.py`, `tests/unit/dashboard/test_trade_path_api.py` 등 | 경계·API·UI·보안 회귀 계약 |

---

## 7. 📊 현재까지 확인한 실제 결과

### 7.1 초기 손익·비용 해부

| 구간 | 거래수 | 비용 후 건당 | 비용 전 건당 | 평균 비용 | 판정 |
|---|---:|---:|---:|---:|---|
| 설계 2022-04-01~2024-03-31 | 13,718 | -6,079원 | +4,411원 | 10,490원, 약 0.210% | 비용 전 흑자이나 비용 후 적자 |
| 초기 표본외 2024-04-01~2026-02-27 | 10,755 | -11,875원 | -1,396원 | 10,480원 | 비용 전에도 소폭 적자 |

이 표는 문제 위치를 찾는 관측 결과다. 당시 손실 매도조건을 제거하면 같은 금액이 개선된다는 뜻이 아니다.

### 7.2 tick/min 경로 결합 control

| 항목 | tick control | min control |
|---|---:|---:|
| 공식 job | `20260727_112426_ResearchTestTickB0900000_66061` | `20260802_063342_MinBStudy251227_22848` |
| 공식 거래 | 4,450 | 6,659 |
| 경로 분석 | 4,399 | 6,577 |
| coverage | 98.85% | 98.77% |
| 제외 | 51 | 82 |
| 매도 뒤 회복 관측 | 2,315 | 1,389 |
| 전체청산 경계 검열 | 2,608 | 5,675 |
| 분석분 실제 손익 | -22,963,621원 | -45,811,646원 |

**증명된 것:** 기존 tick/min DB로 실제 매도 뒤 경로를 전체청산 전까지 결합할 수 있다.

**증명되지 않은 것:** 이 회복을 이용한 변경 조건식이 공식 포트폴리오에서 수익을 개선한다.

### 7.3 매수시점 변수 점검

| 항목 | min control 결과 | 해석 |
|---|---:|---|
| `B_*` 전체 | 31 | 공식 CSV의 매수시점 snapshot 전수 표시 |
| 비0 변수 | 26 | 최소한 분포 분석 가능 |
| 0-only | 5 | “값 0”과 “수집 실패”를 구분할 필요 |
| 분산 있는 `B/D` 분석 변수 | 38 | 1차 후보 진단 입력 |

아직 FDR, fold 안정성, 중복 변수, 조건절 funnel을 한 화면에서 완결하지 않았다. 또한 STOM 런타임 함수 181개는 CSV 열 181개가 아니므로 pre-entry 경로 재구성이 필요하다.

### 7.4 원본 매도식 replay

| 검증 | 결과 | 판정 |
|---|---|---|
| 예시 거래 공식 매도 | 10:55 | 기준 |
| 원본식 replay 첫 발동 | 10:55 | 시각 일치 |
| 자문 손익 차이 | +1,866원 | 공식 체결가·슬리피지 차이로 채택 증거 아님 |
| 미지원 처리 | `unsupported` 명시 | 임의 추정하지 않는 fail-closed 방식 |

### 7.5 공식 pair control

| 항목 | 결과 |
|---|---:|
| 동일 조건 공식 거래 매칭 | 6,659건 전수 |
| baseline-only | 0 |
| candidate-only | 0 |
| 손익 delta | 0원 |
| MDD 차이 | 212.23% vs 211.95%, 0.28%p |

pair 경로는 정상 작동했지만 MDD 재현성 차이는 승격 전에 원인을 규명해야 한다.

### 7.6 현재 후보 다양성

| family | 연구 질문 | 대표 evidence |
|---|---|---|
| 손실 방어 | 회복 가능한 정상 흔들림과 계속 하락하는 거래를 구분할 수 있는가 | 손실 거래의 회복/비회복 cohort |
| 이익 보존 | 2.5~5% 이익을 비용 후 더 자주 보존할 수 있는가 | MFE·실현수익·trailing 경로 |
| 수익 반납 | 이익이었다가 손실로 전환되는 경로를 더 일찍 포착할 수 있는가 | MFE→exit giveback |
| 시간 가치 | 1~2분 구간을 무조건 제외하지 않고 조건부로 좋은 구간으로 바꿀 수 있는가 | 시간대·보유시간·경로 cohort |
| 마감 관리 | 강제청산은 유지하되 그 전에 수익·위험을 더 잘 정리할 수 있는가 | forced cohort와 마감 전 경로 |

### 7.7 검증 증거

| 검증 | 마지막 결과 |
|---|---|
| QSP7 집중 Python 테스트 | **143 passed** |
| frontend 계약 테스트 | **13 passed** |
| runtime JSX graph | **107 JSX / 557 graph files PASS** |
| nonrelease verifier | PASS |
| scoped `git diff --check` | PASS |
| 직접 브라우저 QA | v5.14.0 / build 44f84913, 분석 완료·OOS 차단·콘솔 오류 없음 |

---

## 8. 💡 결과를 어떻게 해석해야 하는가

| 질문 | 올바른 결론 |
|---|---|
| 손실이 많은 매도조건을 제거하면 되는가? | 아니다. 같은 진입은 다음 매도조건, 더 큰 손실, 강제청산으로 이동할 수 있어 완전한 정책 재백테스트가 필요하다. |
| 매도 이후 가격을 보는 것이 유용한가? | 유용하다. 조기청산·늦은청산·회복 가능성의 가설을 만들 수 있다. 단, 전체청산 전 경로만 사용하고 조건식 입력으로 누출하지 않는다. |
| 강제청산이 많으면 강제청산을 없애야 하는가? | 아니다. 강제청산은 안전 경계다. 그 이전에 더 좋은 이익실현·위험축소가 가능한지 연구한다. |
| 1~2분이 최악이면 제외해야 하는가? | 아니다. 관측 bucket일 뿐이다. 매수시점·경로 조건으로 1~2분을 좋은 구간으로 바꿀 수 있는지 공식 실험해야 한다. |
| 가상 delta가 크면 채택할 수 있는가? | 아니다. 후보 순위와 축소에만 사용한다. 공식 설계/OOS 결과가 필요하다. |
| DB가 있으면 반사실을 완전히 알 수 있는가? | 아니다. 실제 시장 경로 기반 동일 진입 replay는 가능하지만 주문 충격, 자금 점유, 재진입 변화는 공식 백테스트에서만 평가된다. |
| CSV 대신 DB만 쓰면 좋은가? | 아니다. 공식 CSV는 불변 영수증으로 유지하고 DB는 재구축 가능한 sidecar 인덱스·원장으로 사용한다. |

---

## 9. 📈 현재 성숙도 점수

| 평가축 | 점수 | 근거 | 9점 이상 조건 |
|---|---:|---|---|
| 방향성 | 8.5/10 | 공식 결과 출발, 미래 누출 차단, 인간 해석 가능성, OOS gate | sidecar·pattern·공식 후보 연구까지 단일 흐름으로 운영 |
| 데이터 계약 | 8.0/10 | CSV hash/schema/비용/경계/전략 표시 | 멱등 ingest·schema migration·availability mask 원장화 |
| 매수 해부 | 7.0/10 | `B_*` 전수 가용성 1차 화면 | FDR·fold·중복·조건절 funnel 및 pre-entry 함수 parity |
| 매도 경로 분석 | 8.5/10 | tick/min 98%대 coverage, 검열·회복 계산 | 대규모 성능·오류 cohort·calibration 자동화 |
| 매도 DSL replay | 7.5/10 | 대표 거래 first-trigger 일치, unsupported 차단 | 공식 함수 parity 확대와 다표본 일치율 보고 |
| 후보 생성 | 6.5/10 | 5개 서로 다른 연구 family | 사람 pattern catalog, 4-arm 품질 비교, 복제 탐지 |
| 공식 비교/OOS UI | 7.5/10 | pair와 비중첩 OOS gate 연결 | 변경 후보의 실제 design/OOS 통과 증거 |
| 실제 전략 개선 | 2.5/10 | control만 재현 | 비용 후 손익·MDD·안정성을 함께 개선한 설계/OOS 후보 |
| 종합 구현 성숙도 | **7.8/10** | 10개 화면과 핵심 분석 연결 | 저장·생성·공식 연구가 반복 가능한 하나의 원장으로 닫힘 |

---

## 10. ⚠️ 미증명·미완성 위험 원장

| 우선 | 항목 | 현재 상태 | 왜 중요한가 | 해결 증거 |
|---:|---|---|---|---|
| P0 | 변경 매도식 공식 설계 개선 | 미실행 | 현재 시스템 효과가 실제 수익으로 이어졌는지 모름 | baseline 대비 공식 pair 통과 |
| P0 | 잠긴 OOS 개선 유지 | 미실행 | 설계 과최적화 가능성 | 비중첩 OOS와 재현 실행 통과 |
| P0 | 가상↔공식 오차 분포 | 미측정 | advisory delta 과신 위험 | 여러 후보의 가상/공식 calibration 표 |
| P1 | sidecar 연구 DB | 미완료 | 분석·후보·실패·공식 판정이 분절됨 | schema_version, migration, 멱등 ingest, rebuild 검증 |
| P1 | 전체청산 경계의 공식 보존 | 신규 job 지원, legacy는 보수 추론 | `legacy_csv_latest_exit`는 공식 설정이 아님 | 신규 job manifest의 exact boundary |
| P1 | 전체 DSL 함수 parity | 부분 지원 | 복잡한 사람 조건식의 trigger가 unsupported일 수 있음 | 대표 tick/min 조건식 회귀 일치율 |
| P1 | 사람 pattern catalog | 미연결 | 후보가 여전히 단순 template처럼 보일 수 있음 | 4 QSP seed+사람 DB AST card 검색 |
| P2 | 매수 변수 통계 gate | 1차만 | 우연한 구분력과 중복 변수 선택 위험 | FDR·fold·중복·funnel 보고 |
| P2 | 4-arm 생성 비교 | 미실행 | pattern retrieval이 실제로 더 사람다운지 모름 | 같은 예산 품질·다양성·공식 안정성 비교 |
| P2 | 1~2분 구간 개선 | 가설 | 나쁜 bucket을 필터링으로 뒤집을 수 있다는 증거 없음 | 실행 가능한 조건의 공식 design/OOS 결과 |
| P2 | tick/min 최종 조건식 | 없음 | 연구 흐름은 있어도 채택할 전략이 없음 | 각각 독립 설계/OOS 통과 |
| P2 | MDD control 0.28%p 차이 | 원인 미확인 | 완전 재현성에 의문 | seed·체결·정렬·동률 규칙 감사 |

---

## 11. 🛠️ 다음 작업 전체 계획

### 11.1 두 개의 다음 lane

| lane | 목적 | 언제 선택하는가 | 공통 최종 권위 |
|---|---|---|---|
| 플랫폼 고도화 | sidecar 원장·pattern 검색·DSL parity로 연구를 반복 가능하게 만듦 | 다음 개발 작업을 이어갈 때 | 공식 백테스트와 OOS |
| 전략 연구 실행 | 현재 화면으로 실제 후보를 만들고 design/OOS 효과를 증명 | 사용자가 기준 전략·기간을 확정했을 때 | 공식 백테스트와 OOS |

서로 다른 파이프라인이 아니다. 같은 QSP7 안에서 연구 질문이 다를 뿐이며 결과는 같은 데이터 계약·History·공식 gate로 돌아온다.

### 11.2 권장 실행 순서

| 순서 | 작업 | 구체 산출물 | 완료 gate | 대략 시간* |
|---:|---|---|---|---:|
| N0 | 기준점 잠금 | baseline buy/sell hash, tick/min, 설계/OOS 기간, 비용, 전체청산시각 manifest | 페이지 1 데이터 계약 모두 확인 | 30~60분 |
| N1 | sidecar 원장 | artifact/run/trade/feature/trigger/hypothesis/comparison/verdict schema와 migration | 같은 CSV 두 번 ingest해 중복 0, rebuild hash 일치 | 1~2일 |
| N2 | 매수·replay 신뢰도 확대 | FDR/fold/funnel, lookback 추출, DSL supported/unsupported coverage | 대표 tick/min 다표본 first-trigger 일치율 보고 | 1~2일 |
| N3 | 사람 pattern·생성 연결 | QSP 4시드+사람 전략을 threshold 제거 pattern card로 색인, evidence pack 출력 | 숫자 복제 아닌 4~8 family와 AST 복제 경고 | 1~2일 |
| N4 | 설계 후보 실행 | 한 라운드 한 축 변경, baseline+4~8 후보 공식 design pair | 비용 후 손익·MDD·거래수·matched/new/lost gate | 엔진 1~3시간 + 검토 |
| N5 | 잠긴 OOS | N4 통과 후보를 변경 없이 OOS 실행 | 설계/OOS 동시 개선, 기간 비중첩, 재현성 | 엔진 1~3시간 + 검토 |
| N6 | calibration·보고 | 가상/공식 오차, 기각 사유, 최종 verdict를 History에 고정 | 실패 포함 재구축 가능한 evidence pack | 0.5~1일 |
| N7 | 사용자 승인 | 조건식 diff·위험·OOS·재현성을 사람이 검토 | 명시적 승인 전 운영 미반영 | 사용자 결정 |

\* 시간은 개발 환경과 공식 백테스트 큐 상태에 따른 거친 추정이다. 성과 보장 시간이 아니다.

### 11.3 가장 먼저 할 실제 작업

| 상황 | 첫 작업 |
|---|---|
| 다음 목표가 “프로그램 완성도” | N1 sidecar 원장부터 시작 |
| 다음 목표가 “현재 프로세스가 실제로 돈을 개선하는지” | N0 기준점 잠금 후 N4 공식 설계 후보 실행 |
| 기준 전략·설계/OOS 기간이 아직 미확정 | 코드를 바꾸지 말고 사용자에게 baseline과 기간 확정을 요청 |
| 공식 job이 없거나 전체청산 경계가 legacy 추론 | 신규 공식 control job부터 생성 |

---

## 12. 👤 대시보드 사용자 확인 체크리스트

| 단계 | 확인 질문 | 실패하면 |
|---:|---|---|
| 1 | 내가 선택한 공식 job·전략·기간이 맞는가? | 분석 중단, job 재선택 |
| 2 | 전체청산시각이 공식 값인가, legacy 추론인가? | 추론이면 제한을 기록하거나 신규 control 실행 |
| 3 | 비용 후 손익이며 비용을 이중 차감하지 않았는가? | 채점식 수정 전 결과 폐기 |
| 4 | 모든 `B_*`가 available/nonzero/0-only/missing으로 보이는가? | 데이터 수집·schema 문제 조사 |
| 5 | 매도사유 손실을 인과 개선으로 표현하지 않았는가? | 표현과 후보 논리를 수정 |
| 6 | 경로가 전체청산 전까지만 표시되는가? | 미래 누출로 결과 폐기 |
| 7 | 원본식 first-trigger와 공식 매도시각 차이가 설명되는가? | DSL parity 또는 체결 차이 조사 |
| 8 | 후보가 5개 family 중 서로 다른 가설인가? | 숫자만 다른 후보를 family로 합침 |
| 9 | 가상 delta 옆에 advisory 경고가 있는가? | 공식 후보로 승격 금지 |
| 10 | design/OOS 기간이 겹치지 않고 둘 다 개선됐는가? | OOS gate가 BLOCKED여야 정상 |
| 11 | History에 실패·0건·unsupported가 남았는가? | 원장 저장 문제 해결 후 다음 실험 |

---

## 13. ✅ 재개 직후 검증 명령

```powershell
Set-Location -LiteralPath 'C:\System_Trading\STOM\STOM_V.wt-dev'
git branch --show-current
git log -5 --oneline
git status --short -- `
  ai_strategy_loop/autopsy `
  ai_strategy_loop/dashboard `
  ai_strategy_loop/revision `
  tests/unit/autopsy `
  tests/unit/dashboard `
  docs/research/quant_scoring_pipeline

python -m pytest `
  tests/unit/autopsy/test_sell_dsl_replay.py `
  tests/unit/dashboard/test_qsp7_data_contract.py `
  tests/unit/dashboard/test_trade_path_frontend.py `
  tests/unit/dashboard/test_trade_path_api.py `
  tests/unit/test_sell_proposer.py -q

python scripts/verify_nonrelease_sync.py
node ai_strategy_loop/dashboard/webui-build/build-app.mjs
node ai_strategy_loop/dashboard/webui-build/runtime-jsx-check.mjs
```

서버가 필요할 때:

```powershell
Set-Location -LiteralPath 'C:\System_Trading\STOM\STOM_V.wt-dev'
python -m ai_strategy_loop --host 127.0.0.1 --port 8771
```

브라우저 주소:

```text
http://127.0.0.1:8771/?tab=backtest&ui=20260803a
```

---

## 14. 🤖 어디서든 재개 가능한 마스터 프롬프트

아래 프롬프트는 이전 대화를 전달할 수 없는 새 Codex 작업, 다른 worktree, 또는 다른 컴퓨터에서도 사용할 수 있다. 저장소가 다른 위치에 있으면 첫 줄의 경로만 바꾼다.

```text
STOM QSP7 통합 연구 시스템 작업을 이어서 진행하세요.

저장소 기준:
- 우선 경로: C:/System_Trading/STOM/STOM_V.wt-dev
- 목표 브랜치: codex/qsp7-trade-episode-research
- 기준 커밋 계열: e4ac882a 이후 QSP7 작업
- 저장소가 다른 위치에 있으면 같은 브랜치와 문서를 찾아 절대경로를 다시 확인하세요.

가장 먼저 할 일:
1. 저장소의 AGENTS.md와 하위 AGENTS.md를 읽으세요.
2. 다음 문서를 순서대로 읽으세요.
   - docs/research/quant_scoring_pipeline/HANDOFF_2026-08-03_QSP7_통합연구시스템.md
   - docs/research/quant_scoring_pipeline/2026-08-02_qsp7_integrated_direction_scorecard_and_roadmap.md
   - docs/research/quant_scoring_pipeline/2026-08-02_qsp7_hybrid_db_and_unified_pipeline_master_plan.md
   - docs/research/quant_scoring_pipeline/2026-08-01_qsp7_trade_episode_exit_research_system_design.md
3. 조건식 생성 작업이면 utility/ai_agent/strategy.txt와 utility/ai_agent/rules.txt를 반드시 읽으세요.
4. git branch, HEAD, scoped status, 8770/8771 listener를 실제로 확인하고 문서의 런타임 상태를 그대로 믿지 마세요.
5. 기존 unrelated 삭제·미추적 .omo/.gjc/artifacts를 수정·삭제·stage하지 마세요.

프로그램 최상위 목적:
공식 백테스트 결과를 매수·매도사유별로 해부하고, 기존 tick/min DB에서 실제 매도 이후 전체청산 전 경로를 확인하며, 원본 매도식과 여러 가설을 동일 진입에서 자문 재생합니다. 그 증거로 사람이 이해할 수 있는 STOM 조건식 후보를 만들고, 완전한 후보 정책을 공식 설계구간과 비중첩 OOS에서 다시 검증해 둘 다 통과한 조건만 사람 승인 대상으로 남깁니다.

현재 완료 상태:
- 연구 화면 10/10 완료: 데이터 계약, 매수 해부, 매도 해부, 거래 경로, 매도식 추적, 가상 매도, 조건식 후보, 공식 pair, OOS 채택, History.
- tick/min 실제 경로 결합과 대표 매도식 first-trigger replay가 작동합니다.
- 5개 후보 family와 공식 pair/OOS 차단 gate가 연결됐습니다.
- 마지막 검증: QSP7 집중 Python 143 passed, frontend 13 passed, runtime JSX 107/557 PASS, nonrelease verifier PASS.
- 구현 성숙도는 약 7.8/10이지만 변경 전략의 수익 개선 증명은 2.5/10이며 공식 design/OOS 통과 후보는 아직 0건입니다.

절대 불변식:
- 공식 CSV는 불변 영수증이며 삭제하거나 DB로 대체하지 않습니다.
- 기존 _database tick/min/strategy DB는 read-only입니다.
- 전체청산 이후 가격은 읽거나 추정하지 않습니다.
- 장 마감 강제청산은 유지하고 그 이전 청산 품질을 연구합니다.
- R_*, S_*, 매도 뒤 회복, 미래 최고·최저를 매수/매도 조건 입력으로 누출하지 않습니다.
- 손실이 큰 매도조건을 제거하면 좋아진다고 추론하지 않습니다.
- 동일 진입 replay와 가상 delta는 advisory이며 공식 수익이 아닙니다.
- tick과 min 시간 단위·함수·후보 family를 분리합니다.
- 한 라운드에는 buy 또는 sell 한 축만 변경합니다.
- 후보를 운영 전략 DB나 실거래에 자동 반영하지 않습니다.
- 설계와 잠긴 OOS가 모두 통과하고 사람이 승인하기 전 채택하지 않습니다.

재사용해야 할 기존 코드:
- ai_strategy_loop/autopsy/trade_path_models.py
- ai_strategy_loop/autopsy/market_path.py
- ai_strategy_loop/autopsy/trade_path_analysis.py
- ai_strategy_loop/autopsy/sell_dsl_replay.py
- ai_strategy_loop/dashboard/trade_contract.py
- ai_strategy_loop/dashboard/trade_path_api.py
- ai_strategy_loop/dashboard/sell_dsl_api.py
- ai_strategy_loop/dashboard/trade_path_official_api.py
- ai_strategy_loop/revision/sell_proposer.py
- 기존 TradeLedger, analysis_snapshot, loop_runs evidence, official backtest job/pair 경로

작업 모드 선택:
- MODE=platform이면 sidecar 연구 원장을 먼저 구현하세요.
  - artifact/run/trade/feature/trigger/hypothesis/comparison/verdict를 schema_version과 migration으로 관리하세요.
  - source_csv_sha256+row_count 기반 멱등 ingest와 전체 rebuild 검증을 추가하세요.
  - 새로 분리된 또 하나의 파이프라인이나 임시 DB를 만들지 말고 기존 저장 요소를 통합하세요.
- MODE=research이면 실제 성과 검증을 진행하세요.
  - 먼저 사용자에게 baseline buy/sell, tick/min, design/OOS 기간, 전체청산시각을 확인받거나 기존 공식 manifest에서 검증하세요.
  - 서로 다른 family의 후보 4~8개를 만들고 사람이 선택한 후보만 공식 design pair로 실행하세요.
  - 비용 후 손익, MDD, 거래수, matched/new/lost, 자금 점유와 재진입을 비교하세요.
  - design 통과 후보만 설정을 잠가 비중첩 OOS로 실행하세요.

조건식 후보 품질 계약:
- 후보는 market_regime, entry_thesis, confirmation, invalidation, profit_path, evidence, counterevidence, changed_clauses, expected_risk, self_review를 가져야 합니다.
- 손실 방어, 이익 보존, 수익 반납, 시간 가치, 마감 관리 등 서로 다른 가설을 사용하세요.
- 숫자만 다른 후보는 하나의 parameter family로 묶으세요.
- 사람 전략은 전체 식과 threshold를 복사하지 말고 AST 정규화 pattern card로만 검색하세요.
- 지원하지 않는 STOM 함수는 추정하지 말고 unsupported로 기록하세요.

완료 규칙:
- 먼저 현재 상태와 실행 계획을 표로 보고하세요.
- 테스트를 먼저 추가하고 실패를 확인한 뒤 최소 구현하세요.
- schema/API/UI/migration/test/docs를 해당 단계에서 함께 닫으세요.
- 실제 브라우저 QA와 API 증거를 남기세요.
- 파일은 명시적으로 stage하고 한국어 제목·한국어 markdown 본문으로 작게 커밋하세요.
- 관측 결과, advisory 결과, 공식 design/OOS 결과를 각각 별도 표로 보고하세요.
- 미증명·차단·0건 결과를 숨기지 마세요.

이번 작업의 첫 응답에서 반드시 안내할 것:
1. 현재 브랜치와 HEAD
2. QSP7 범위 파일의 clean/dirty 상태
3. 현재 dashboard listener와 실제 접속 주소
4. 10개 페이지 중 회귀 또는 미완료 상태
5. MODE=platform 또는 MODE=research 중 선택한 모드와 이유
6. 이번 작업의 완료 gate와 예상 시간

사용자가 모드를 지정하지 않았다면:
- 프로그램 고도화 요청은 MODE=platform으로 시작합니다.
- 실제 효과·수익 검증 요청은 MODE=research로 시작합니다.
- baseline이나 design/OOS 기간 선택이 결과를 바꿀 정도로 불명확하면 임의로 실행하지 말고 필요한 값만 질문합니다.
```

---

## 15. 🧭 완료 정의

| 수준 | 완료 조건 | 현재 |
|---|---|---|
| 페이지 구현 완료 | 10개 페이지와 API·오류·빈 상태·History 흐름 작동 | ✅ |
| 연구 플랫폼 완료 | sidecar 원장, pattern catalog, DSL coverage, 재구축·migration·calibration | ❌ |
| 후보 생성 완료 | tick/min별 사람다운 4~8개 후보와 품질 비교 | ❌ |
| 전략 연구 완료 | 변경 후보의 공식 design과 잠긴 OOS 통과 | ❌ |
| 운영 채택 가능 | 재현성·위험·사람 승인까지 완료 | ❌ |

다음 작업자는 “페이지가 모두 있으니 QSP7이 끝났다”거나 “가상 delta가 양수이니 전략이 개선됐다”고 보고해서는 안 된다. 현재 성과는 **정확하고 재현 가능한 연구 판단 구조를 만든 것**이며, 다음 성과는 그 구조로 실제 공식 후보를 검증해 얻어야 한다.

---

## 16. 📚 기준 문서와 자산

| 우선 | 자산 | 역할 |
|---:|---|---|
| 1 | `HANDOFF_2026-08-03_QSP7_통합연구시스템.md` | 현재 상태·재개 절차 |
| 2 | `2026-08-02_qsp7_integrated_direction_scorecard_and_roadmap.md` | 전체 감사·점수·미증명 항목 |
| 3 | `2026-08-02_qsp7_hybrid_db_and_unified_pipeline_master_plan.md` | 저장 구조·파이프라인·생성 prompt 계획 |
| 4 | `2026-08-01_qsp7_trade_episode_exit_research_system_design.md` | 반사실·경계·권위 설계 |
| 5 | `2026-08-01_qsp7_trade_path_research_implementation_result.md` | 초기 수직 슬라이스 구현 결과 |
| 역사 | `HANDOFF_2026-08-01_QSP7_매도식연구.md` | 초기 손실 해부·가설 보존 |
| 조건식 문법 | `utility/ai_agent/strategy.txt`, `utility/ai_agent/rules.txt` | STOM 조건식 생성 규칙 |
| 한계 | `docs/research/quant_scoring_pipeline/limitation_ledger.md` | 실패·제약 누적 |
