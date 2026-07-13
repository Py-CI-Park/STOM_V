# 다음 단계 실행 계획서 — Opus/Sonnet 구동용 (2026-07-13)

> 지위: **현행 실행 계획 정본.** 라운드 3 종결(온셋 축 지형 확정) 이후의 모든 작업을 이 문서로 구동한다.
> **독자 = 집행 모델(Opus/Sonnet).** 이 문서는 "판단 없이 따라 할 수 있는 수준"으로 쓰였다. 판단이 필요한 지점은 전부 §9 에스컬레이션 표로 넘긴다 — **집행 모델은 §9의 금지 항목을 절대 스스로 결정하지 않는다.**
> 모델 라우팅(사용자 지시 2026-07-13): **연구(사전등록 초안 검토·봉인 결정·판정 해석·새 가설) = Fable** / **집행(코드 구현·측정 기동·감시·원장 기입·커밋·주기 운영) = Opus(복잡)·Sonnet(정형)**.
> 읽기 순서(새 세션): ① 본 문서 ② `2026-07-12_program_handoff_v3.md`(프로그램 현황 정본) ③ 해당 트랙의 봉인 문서 ④ `2026-07-10_window_status_ledger.md`(창-지위 — 모든 측정의 관문).

---

## 0. 한 줄 상태 (2026-07-13 라운드 3 종결 시점)

**확정**: 온셋 축(전이 D5·돌파 O-3)은 kill — 서지가 시초 30분의 지배 축. **엣지는 절 조합(압력 5절 + 조건부 가드 시너지 16×37/38)과 출구**에 있다. B1은 실전 인계 완료(운용 개시만 사용자 몫). WBS P0~P3 완료(P4만 go 대기). **다음 주력 = 트랙 A(O-4 생성 문법)**.

## 1. 현재 상태 스냅샷 (집행 모델은 착수 전 이 표와 실물을 대조하라)

| 항목 | 값 | 확인 명령 |
|---|---|---|
| 브랜치 | `research/alpha-lab-idea5-foundation-20260707` | `git branch --show-current` |
| 라운드 3 커밋 체인(말단) | `1ca2c7aa`(B1) → `99944213`(D5 봉인) → `505d5010`(d9lab) → `0e863b01`/`b866fc23`/`0fc6c512`/`21bfecdf`(P0~P3) → `fd643228`(초안 2종) → `91e943b0`(D5 kill-3) → `6f51645d` → `96a37d28`(O-3 봉인) → `e1c12697`(2절 봉인) → `7551f3c7`(2절 구현) → `c7869aa4`(o3lab) → `f74c97b0`(2절 양성) → `b79649bf`(O-3 kill) | `git log --oneline -20` |
| n_trials 원장 | **85행** (D1 38·D1_PAIR 19·D5-R 12·O-3 10·D5 3·S-트랙 2·O-1G 1) | `python -c "from alpha_lab.discipline import ledger; print(ledger.aggregate()['total'])"` (환경변수 필요 §2-1) |
| 전략 DB | `_database/strategy.db` stockbuy 165·stocksell 110 (`ALP_D5R_B1_S` 등록 완료) | read-only URI로만 조회 |
| 테스트 배터리 | 신규 모듈 6종 130+ 전부 green | §7 SOP-O 참조 |
| 미커밋 잔여 | `.gjc/`·`.omo/evidence/…` 2건 — **도구 잔재. 커밋 금지·삭제 금지·방치**(§8) | `git status --short` |

**핵심 자산(측정 재료)**: 출구 은행 `research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet`(863,446행, sha `0b6268e0…`) · 절 비트 행렬 `stats_map/d1_onset_clause_bits.parquet`(sha `4df57b77…`) · 돌파 은행 `o3/o3_breakout_onset_bank.parquet`(702,613행, variant 컬럼) · 카탈로그 `research_assets.db`(재생성: `python scripts/build_research_catalog.py`).

**확정 판정(번복 금지)**: 칸-조준 KILL · O-1G 0/144 · D5 kill-3(겹침 63.5%) · O-3 kill(전 단위 음EV) · RR8 병합 무가치 · D1 양성(압력 5절) · 2절 시너지(16×37 I=+0.129%p CI[+0.078,+0.195] / 16×38 **+0.157** CI[+0.090,+0.230] — 판정 json 정본, 초기 산문 +0.124는 오기) · B1 엔진 A/B 4/4 PASS.

## 2. 불변 규율 (모든 트랙 공통 — 위반 시 산출물 폐기)

1. **환경**: 모든 python 실행에 `STOM_ALLOW_MINIMAL_SETTING=1`. `python`(pandas 포함 환경)이며 `python3` 아님. 콘솔 한글 깨짐(cp949)은 표시 문제 — 파일 산출물은 UTF-8 정상. 필요 시 `python -X utf8`.
2. **데이터**: 신규 시장 데이터 수집/백필 절대 금지(존재하는 DB만). 원천 DB는 read-only URI. `backtest/graph/`는 보호 결과 데이터.
3. **창-지위**: known 창(2025-01-01~2026-02-27, **청산 레버·v4 계열은 2024도**)으로 어떤 측정도 금지 — veto/감사 전용. 측정창은 발견창 2022-03-23~2023-12-31.
4. **봉인 선행**: 측정은 사전등록 **봉인 커밋 이후에만**. 봉인 문서 헤더가 "봉인본"이고 §14(결정 기록)가 있어야 한다. 초안 상태(§13만 있음)면 측정 금지 → Fable 에스컬레이션.
5. **원장 단일 경로**: n_trials 기입은 `alpha_lab.discipline.ledger.append_trial`만. jsonl 직접 append 금지.
6. **커밋 주체**: git 명령은 **메인 세션만**(서브에이전트 git 전면 금지 — index.lock 충돌 방지). 커밋 규약은 §7.
7. **실전·레인 경계**: 전략 DB 쓰기(registrar 등록)·실계좌·GUI 운용·wt-dev 레인 코드 변경은 사용자 승인 필수(§9).
8. **엔진 예산**: `stom_backtest.py` 실행은 해당 봉인 문서의 type-a 예산 안에서만. 대량 스윕은 U-7(사용자 승인) 필요.

## 3. SOP-M: 측정 사이클 표준 절차 (모든 측정 공통 — 집행 모델용 체크리스트)

```
[1] 봉인 확인      git log --oneline -3 -- <봉인문서.md> 에 봉인 커밋 존재 + 문서 헤더 "봉인본"/§14 존재
[2] 코드 게이트    STOM_ALLOW_MINIMAL_SETTING=1 python scripts/measure_gate.py --repo-root . \
                     --sealed-doc <봉인문서> --code <측정파일1> --code <측정파일2> ...
                   → 출력 verdict "기동 허용" 필수. "거부"면 사유 해결(코드 미커밋이면 §7-1로 선커밋) 후 재시도
[3] 인자 대조      봉인 문서의 게이트 요건(예: 스팟 재검 일자)을 CLI --help와 대조해 필요한 인자를 빠짐없이 구성
                   ※ 실측 사고: O-3 최초 기동 때 --spot-days 누락으로 G3 미실행 → 스팟 재추출로 보완했음.
                     measure_gate는 코드 무결성만 검사하고 인자 완전성은 안 본다 — 이 단계가 그 구멍을 막는다
[4] 분리 기동      STOM_ALLOW_MINIMAL_SETTING=1 python -m alpha_lab.runlab.detached_runner \
                     <run_dir> <스크립트> -- <인자...>
                   (run_dir 권장: 산출 디렉토리 아래 run_ctl/runN — .gitignore에 run_ctl/ 포함 확인)
[5] 감시           python scripts/batch_watch.py <run_dir>  (보고 전용 — 자동 재시작 금지)
                   RUNNING=정상 / STALLED·DEAD·WRAPPER_ERROR=로그(log.txt)·진행 파일 확인 후 원인 규명.
                   재기동은 체크포인트 재개로만(완료 일자는 자동 skip). 판단 애매하면 §9 에스컬레이션
[6] 게이트 검수    산출 게이트 json에서 전 게이트 pass 확인. 하나라도 fail이면 판정 진입 금지 → Fable
[7] 원장 기입      python 인라인으로 alpha_lab.discipline.ledger.append_trial(...) — 봉인 문서의 시행 계상
                   규칙(분모·행수) 그대로. 기입 후 ledger.aggregate()로 행수 확인
[8] 산출물 커밋    md/json 리포트 + n_trials_ledger.jsonl + 핸드오프 갱신을 §7 규약으로 커밋
                   (parquet·parts·run_ctl·progress는 .gitignore 확인 — 커밋 금지)
[9] 판정 해석      수치 기입까지가 집행 몫. 경계 사례 해석·다음 연구 결정은 Fable 에스컬레이션
```

## 4. 트랙 A — O-4 생성 문법 (주력 · 다음 착수)

**왜**: 라운드 3까지는 부품 검사였다. 이제 합격 부품(압력 5절 + 결합 규칙 + 함정 지도 + 닫힌 축 목록)이 완비 — 부품 검사가 수익이 되는 유일한 경로는 조립·시험이다. **목적**: 챔피언(RR8_12)과 다른 구조 또는 개선형 매수식 후보를 만들어, 오프라인 대량 선별 → 소수 엔진 확인 → 우위 시 감독형 소액 실전(U-4) 인계. 목적함수 = **총수익 최대**(MDD는 킬스위치 제약), 실전 형태 = 매수1+매도1. **예상 효과**: 낙관=신규 수익원(챔피언과 저상관), 중립=아류 판정(무가치 확정 — RR8 병합 전례), 비관=엔진 전멸("가산 조합 문법 한계" 확정 지식). 세 경우 모두 봉인된 자로 잰 확정 지식이 남는다.

| 단계 | 담당 | 내용 | 완료 기준 |
|---|---|---|---|
| A-0 사전등록 초안 | **Fable**(에이전트 초안 허용) | 생성 문법 공간(압력 4족 절 ± 조건부 가드 #16계열은 압력 동반 규칙으로만 ± 함정 회피 조건), **임계 재도출 규약**(원-임계 이식 금지 딱지 이행 — 후보 임계 격자를 사전 고정하고 격자 크기만큼 n_trials 계상), 오프라인 선별 기준(온셋 은행 조건부 EV·표본 하한·BH-FDR·효과 하한 — 관문: 왕복 비용 0.61~1.21% 초과), kill 기준, **엔진 예산 상한 봉인**(type-a ≤16 권장), U-7/U-4 연결 조항, §13 미결 목록 | 초안 md 존재 + §13 권고안 완비 |
| A-1 봉인 | **Fable 전용** | §13 전건을 §14로 확정, 원장 갱신, 봉인 커밋 | 헤더 "봉인본" + §14 + 커밋 |
| A-2 측정 코드 | Opus 권장(Sonnet 가능 — clause_lab/o3lab 미러 수준) | `alpha_lab/o4lab/`(가칭) — 기존 자산 재사용(은행·비트·d9lab/o3lab 패턴). 기존 파일 무수정. 테스트 필수. **본 측정 실행 금지** | 테스트 green + 메인 재실행 검증 + §7-1 선커밋 |
| A-3 오프라인 선별 | 집행 | SOP-M 전체 적용(비용 0 — 엔진 아님) | 게이트 pass + 선별 결과 json |
| A-4 판정 | 수치=집행 / 해석=**Fable** | 봉인 문구 그대로 판정, 원장, 커밋 | SOP-M [7][8] |
| A-5 엔진 확인 | 집행(예산 내) | 생존 후보만 `STOM_ALLOW_MINIMAL_SETTING=1 python stom_backtest.py --buy <후보> --sell <출구> --start 20220101 --end 20221231 --timeframe tick`(연도별, betting5/avg30, scratch strategy.db — B1 전례 `research_runs/alpha_restart_20260710/d5r_b1_live/` 스크립트 참조). **2024/2025 금지.** 런당 원장 type-a 1행 | 봉인 예산 내 + 4런 판정 표 |
| A-6 인계 | **사용자(U-4)** | 우위 후보의 등록(registrar)·실전 개시는 사용자 승인 후에만 | — |

**백업 대기열**(A가 kill로 끝나면 Fable이 선택): 3절 조합(2절 결과 입력, 표본 희소성 주의) · 절 재도출 트랙(압력 절 임계의 독립 재탐색) · B1 30거래일 후 청산 후속(실전 잔차 데이터 입력).

## 5. 트랙 B — B1 실전 채점 지원 (사용자 운용 개시 후 활성)

전제: **사용자가** GUI에서 정본 페어링(매수 `ALP_V4_RR8_12` + 매도 `ALP_D5R_B1_S`)으로 운용 개시. 절차서 = `2026-07-12_b1_supervised_live_protocol.md`(킬스위치·채점표·기록 양식 §4).

| 단계 | 담당 | 내용 |
|---|---|---|
| B-1 | 집행(Sonnet) | 사용자가 실전 기록(절차서 §4 양식)을 제공하면: 채점 집계 스크립트(`scripts/b1_scorecard.py` 신규) — 실현율·일거래수·손익비·킬스위치 소진율·절 발동률(>0.5면 경보)·tick2 잔차 분포 산출. 데이터 계약 §6 예약 스키마(`b1_live_trades`/`b1_live_days`) 준수 |
| B-2 | **Fable** | 30거래일 채점 판정(승격 rank5 / 유지 / 강등 rank3) — 절차서 §3 기준. **채점 전 성공 주장 금지** |

## 6. 트랙 C — P4 대시보드 구현 (사용자 go 대기)

전제 2건: ① **사용자 go** ② 기존 V4 대시보드 PR(base=`loop/process-research-pipeline`, push 47981e3c)과 조율. go 전에는 어떤 wt-dev 파일도 만지지 않는다.

go 이후(집행 — Sonnet designer/executor 적합): 명세 2종이 계약이다 — `2026-07-12_dashboard_data_contract.md`(API 4종, SELECT-only, 카탈로그 경로는 env `STOM_RESEARCH_ASSETS_DB`) + `2026-07-12_dashboard_view_specs.md`(V1~V5, 딱지 렌더링 강제 R1~R11). 검수는 계약 §7 수용 기준 7항 그대로(구현 코드에 산술 SQL 0건·label_tag 바이트 동일 등). 라우터는 신규 모듈 분리(`research_api.py` 관례 참조 — `alpha_api.py`는 실존하지 않음에 주의).

## 7. 커밋 규약 + 주기 운영 (SOP-O)

### 7-1. 커밋 규약 (전 트랙 공통)

- **논리 단위 분리**: 봉인 커밋(문서+원장 갱신만) / 측정 코드 커밋(측정 전 — measure_gate 통과 조건) / 판정 커밋(리포트+원장+핸드오프) — 라운드 3의 실제 체인(§1)이 모범 사례.
- 메시지: 한국어, 제목 = 판정/행위 선언(예: "O-3 판정 — kill: …"), 본문 = 핵심 수치·게이트 결과·근거 봉인 커밋 해시. 말미 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`(집행 모델도 실제 모델명으로 병기).
- 커밋 전 확인: ① `git status`로 의도 파일만 스테이징(§8 잔재 2건 제외) ② parquet/run_ctl/progress가 안 딸려오는지 ③ 판정 커밋이면 핸드오프 v3 §0·§5 갱신 포함.
- **index.lock 오류 시**(9회 실측된 GitKraken 잔재): `ls -la <메인repo>/.git/worktrees/STOM_V.wt-alpha/index.lock`으로 0바이트 확인 + `powershell Get-CimInstance Win32_Process -Filter "Name='git.exe'"`에서 쓰기성 git 부재 확인 → `rm -f <lock>` → 재시도. 쓰기 git이 실제로 돌고 있으면 대기.

### 7-2. 주기 운영 (판정 커밋 직후마다 실행)

```
[O-1] 테스트 배터리   STOM_ALLOW_MINIMAL_SETTING=1 python -m pytest tests/unit/test_alpha_catalog.py \
                       tests/unit/test_alpha_discipline.py tests/unit/test_alpha_gates.py \
                       tests/unit/test_alpha_runlab.py tests/unit/test_onset_bank_v2.py \
                       tests/unit/test_d9lab.py tests/unit/test_o3lab.py tests/unit/test_d1_pairwise.py -q
[O-2] 브랜치 게이트    python scripts/verify_nonrelease_sync.py  (+ 필요 시 python -m pytest tests/unit/ -q)
[O-3] 카탈로그 재빌드  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/build_research_catalog.py
                       → 영수증 diff 확인 후 research_assets_build_receipt.json만 커밋(DB는 git 제외)
[O-4] 원장 린트        STOM_ALLOW_MINIMAL_SETTING=1 python scripts/ledger_lint.py  (보고 전용 —
                       신규 플래그가 진짜 known-창 측정이면 즉시 Fable 에스컬레이션)
[O-5] prereg-diff      신규 판정이 있으면: python scripts/prereg_diff.py로 봉인↔결과 대조(보고 전용)
```

## 8. 미커밋 파일 정책 (체계적 처리 — 현재 잔여 전수)

| 경로 | 정체 | 처리 |
|---|---|---|
| `.gjc/` | GitKraken CLI 잔재 | **커밋 금지·삭제 금지·방치**(도구 소유물). 루트 .gitignore 수정도 하지 않는다(공유 파일 최소 접촉) |
| `.omo/evidence/tmap-walkforward/_discovery_feedback.txt` | oh-my-claudecode 플러그인 산출 | 동일 — 방치 |
| `*/run_ctl/`·`parts/`·`*.parquet`·`*progress.txt`·`*.log` (d5_d9·o3 등 측정 산출) | 재생성 가능 대용량 | 각 산출 디렉토리 `.gitignore`가 차단(본 커밋에서 o3에 run_ctl/·*.log 보강). 새 측정 디렉토리를 만들면 **같은 5줄 .gitignore를 먼저 생성**하는 것이 규약 |
| 판정 md/json·원장·봉인 문서 | 연구 정본 | 반드시 커밋(§7-1) |
| 스크래치(`C:\Temp\claude\...\scratchpad\`) | 세션 임시 | repo 밖 — 커밋 대상 아님. 보존 가치가 생기면 research_runs로 복사 후 커밋(B1 전례) |

## 9. 에스컬레이션 표 (집행 모델의 경계 — 이 표 밖의 판단 금지)

| 상황 | 넘길 곳 |
|---|---|
| 사전등록 봉인 결정(§14 작성)·확정 판정 번복·경계 사례 해석·새 가설 설계·kill 수용 | **Fable** |
| known 창 접촉이 필요해 보이는 모든 경우("veto 확인"이라도) | **Fable**(원장 §2 해석) |
| 엔진 예산 초과·대량 스윕(O-5) | **사용자(U-7)** |
| 전략 DB 등록(registrar)·실전 운용·자본/킬스위치 수치 확정 | **사용자(U-4)** |
| wt-dev 레인 파일 변경(P4 포함)·타 워크트리 접촉 | **사용자 go** |
| STALLED/DEAD/WRAPPER_ERROR 원인이 코드 결함으로 의심 | **Fable**(수정은 봉인 정합 검토 필요) |
| 도구가 서로 모순된 보고(예: gate pass인데 prereg-diff MISMATCH) | **Fable** |

## 10. 실측 함정 목록 (라운드 1~3 누적 — 재발 시 이 표부터)

1. **index.lock**(9회) → §7-1 절차. 2. **배치가 세션과 동반사**(2회) → 반드시 detached_runner 경유(§3-[4]), 메인 세션 배시 백그라운드로 감시. 3. **기동 인자 누락**(O-3 G3) → §3-[3] 인자 대조 의무. 4. **cp949 콘솔 깨짐** → 파일 산출물 기준 판단. 5. **`&&` 체인이 파일 부재 확인에서 중단** → 상태 점검은 `;`. 6. **`/tmp` 부재** → 스크래치 디렉토리 사용. 7. **에이전트 "idle" ≠ 완료** → 진행 파일·프로세스로 확인. 8. **세션 한도로 에이전트 사망** → 산출물은 파일로 남아 있으니 파일 기준으로 이어받기(재실행 아님). 9. **측정 코드 미커밋 측정**(O-1G 사고) → measure_gate가 차단하나, 우회 금지.

---

*본 계획의 연구 순서·판정 기준의 정본은 각 봉인 문서와 핸드오프 v3다 — 상충 시 봉인 문서가 우선한다. 집행 모델은 이 문서에 없는 재량을 만들지 않는다: 막히면 §9로 넘기고, 넘긴 기록을 핸드오프에 남긴다.*
