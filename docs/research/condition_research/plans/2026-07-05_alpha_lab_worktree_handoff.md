# 알파 랩 워크트리 착수 핸드오프 (2026-07-05)

> **이 문서 하나만 읽고 새 세션에서 바로 구현을 시작할 수 있도록 작성됨.**
> 여기는 신규 알파 발굴(규칙 채굴 + 이벤트 스터디) 전용 워크트리다. 기존 AI 루프(생성-테스트)와 직교하는 데이터-우선 발굴을 구현한다.

---

## 0. 지금 상태 (TL;DR)

| 항목 | 값 |
|---|---|
| 워크트리 | `C:\System_Trading\STOM\STOM_V.wt-alpha` |
| 브랜치 | `research/alpha-lab-20260704` (base: `loop/process-research-pipeline` @ `f5ddc248`) |
| `_database` | ✅ junction 설정 완료 → `wt-dev/_database` (tick 952일 read-only 확인) |
| 의존성 | sklearn 1.8.0 ✅ / pandas 3.0.2 ✅ / numpy 2.4.4 ✅ / **pyarrow ❌ (v1은 npz로 무설치 시작)** |
| 엔진 상태 | tick warm64 스윕 완료(12/12), 엔진 유휴. **min 레인 스윕은 config만 준비·미실행** |
| 설계 문서 | 이 워크트리에 전부 존재 (아래 §1) |
| 다음 할 일 | **§4 모듈 1 (registry.py) 부터 TDD로 구현 시작** |

**핵심**: MVP 구축(모듈 1~6 + 대시보드)은 **백테스트 엔진이 전혀 필요 없다** — 읽기 전용 sqlite + CPU 계산뿐. 지금 즉시 시작 가능. 백테스트 엔진이 필요한 건 맨 마지막 검증(ρ 게이트·OOS)뿐이며, 그때만 min 스윕과 시간을 겹치지 않게 조율하면 된다.

---

## 1. 먼저 읽을 문서 (순서대로)

1. **`plans/2026-07-05_new_alpha_implementation_design.md`** ← 실행 설계서(알고리즘·코드 구조·대시보드). **이게 구현 스펙이다.**
2. `plans/2026-07-04_new_alpha_research_program.md` ← 5패러다임 심사·우선순위·봉인 판정(왜 규칙 채굴·이벤트 스터디가 1순위인가, MVP 성공/포기 3분지 기준)
3. 참고: `plans/2026-07-02_plan_B_research_execution_roadmap.md`(공식 warm64 프로파일·게이트 체인), `docs/update_log/2026-07-04_quant_midreview_gate_zero_diagnosis_handoff.md`(격자 시드가 "지도용"이라 게이트 통과가 수학적으로 어렵다는 교훈 — 알파 랩은 이 함정을 피해야 함)

---

## 2. 착수 전 sanity check (그대로 실행)

```bash
cd C:/System_Trading/STOM/STOM_V.wt-alpha
git branch --show-current          # research/alpha-lab-20260704 여야 함
python -c "import sklearn,pandas,numpy; print('ok')"
python -c "import sqlite3,glob; d=sorted(glob.glob('_database/stock_tick_2*.db')); \
c=sqlite3.connect('file:'+d[-1]+'?mode=ro',uri=True); \
print('tick DBs:',len(d),'cols:',[x[1] for x in c.execute('PRAGMA table_info(\"085660\")')][:6]); c.close()"
```
기대: 브랜치 일치, deps ok, tick DB 952개 + 54컬럼 접근. 실패 시 junction 재설정:
`cmd //c mklink //J "C:\System_Trading\STOM\STOM_V.wt-alpha\_database" "C:\System_Trading\STOM\STOM_V.wt-dev\_database"`

---

## 3. tick DB 54컬럼 실명 (설계서 §1.1과 동일 — 피처 정의 시 이 이름 그대로 사용)

```
index, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량,
거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내,
VI해제시간, VI가격, VI호가단위, 초당거래대금, 고저평균대비등락율, 저가대비고가등락율,
초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격,
매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5,
매도잔량5..1, 매수잔량1..5, 매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목
```
- 진입가 = `매도호가1`(t0+1초), 청산가 = `매수호가1`(t0+지평) → 스프레드 비용 내재화(설계서 §3.1).
- E1 VI 해제 사건 = `VI해제시간` 저장 컬럼 직접 사용(추정 불필요).
- moneytop 테이블 = `index`+`거래대금순위`(초당 point-in-time 유니버스) → "그 초에 관측된 종목만 표본화"로 유니버스 소급 불가(갭4) 자연 해결.

---

## 4. 구현 순서 (설계서 §5 — TDD, 모듈당 신규 파일 + 테스트 1쌍)

**모든 모듈은 `alpha_lab/` 신규 패키지에 만든다. 기존 코드 수정 금지(읽기 전용 import만).**

| 순서 | 모듈 | 첫 작업 요지 | 백테 필요 |
|---|---|---|---|
| **1 (지금 시작)** | `alpha_lab/registry.py` | 사전등록 봉인(JSON + sha256) + n_trials 원장(JSONL append-only). 봉인 후 피처·임계·사건정의 변경 거부. 테스트: 봉인 sha 결정성/변경 거부/n_trials 합산 | ❌ |
| 2 | `alpha_lab/dataset/reader.py` + `labels.py` | read-only sqlite 스트리머 + L1(고정지평 60/180/300초, tick2·수수료 차감) / L2(트리플배리어). 테스트: 합성 1일 DB로 라벨 수기 검증 | ❌ |
| 3 | `alpha_lab/dataset/cache.py` | float32 npz 샤드 캐시(pyarrow 없이) | ❌ |
| 4 | `alpha_lab/mining/trees.py` + `stats.py` | DecisionTree(depth≤4, leaf≥2000) 리프 추출 + 일 블록 부트스트랩 + BH-FDR q<0.05. **양성 대조: rr8_12 진입 절 주입 → lift 검출 확인** | ❌ |
| 5 | `alpha_lab/translate/idioms.py` + `codegen.py` | 리프→STOM 조건식(피처 25종 사전) + compile·금지토큰·스코프·원리게이트 통과 | ❌ |
| 6 | `alpha_lab/events/detectors.py` + `outcomes.py` | E1~E5 인과 감지기(불응기 120초) + 층화 셀 EV + 이중 플라시보. **양성 대조: 합성 확실사건 주입** | ❌ |
| 7 | `alpha_lab/bridge/registrar.py` + `receipts.py` | `ALP_` 접두 INSERT-only 등재(백업·멱등·충돌보고) + provenance | (등재만, 실행 아님) |
| 8 | 대시보드 `/api/alpha/*` 5종 + `frontend/alpha.html` | 설계서 §6 (기존 FastAPI additive) | ❌ |
| **9 (엔진 필요)** | MVP 검증 | ρ 게이트 백테 10회 + OOS 봉인 1회 (`claude_candidate_batch_eval` + 공식 warm64) | ✅ **min 스윕과 조율** |

피처 v1 25종 실명 목록은 설계서 §3.2에 확정돼 있음 — registry 봉인 파일에 그대로 열거.

---

## 5. 불변 조건 (반드시 지킬 것)

1. **DB 읽기는 전부 `file:...?mode=ro` URI** — junction이 read-write라 실수로 쓰면 wt-dev 공유 DB가 깨진다. 절대 mode=ro 없이 열지 말 것.
2. **채굴 표본에 거래 CSV 사용 금지** — 현직 조건식이 만든 거래는 선택 편향(06-14 "사후 슬라이스" 함정). 라벨은 tick DB 원본 시점에서만 생성.
3. **미래 누수(lookahead) 차단** — 피처는 저장 54컬럼 + "같은 초 안의 사칙연산"만. 롤링/이동평균(엔진 재계산 파생 19항)은 v1 금지, v2로 이월.
4. **사전등록 봉인 우선** — registry 봉인 파일 sha를 커밋에 남긴 뒤에만 채굴 실행. 봉인 후 임계값·피처·사건정의 변경은 새 n_trials로만.
5. **연구 레인 전용** — 최종 조건식은 기존 게이트(스모크→train→OOS→슬리피지 tick2)를 무특혜 통과해야 인정. can_promote/export/live 무관, `backtest/graph/` 불가침.
6. **전략 DB 쓰기(모듈 7)는 백업 선행 + INSERT-only + 충돌 보고** — chart_sulsa `scripts/register_chart_sulsa_conditions.py` 패턴 재사용.

---

## 6. 커밋·운영 규율

- 커밋 메시지 한글, 게이트(신규 테스트 + 관련 회귀) 통과 후 커밋. 이 브랜치는 wt-dev의 `loop/process-research-pipeline`과 **독립** — 서로 push/merge 강제 없음.
- **index.lock 주의**: 이 환경에서 GitKraken이 `.git/worktrees/*/index.lock`(0바이트)을 반복적으로 남긴다. `git` 실패 시 `tasklist | grep -i git.exe`로 실행 중 git 부재 확인 후 해당 lock 파일 `rm -f`, 커밋은 직렬로.
- 산출물 경로: `docs/research/condition_research/research_runs/alpha_lab_20260705/` (preregistration·dataset receipt·mining report·translation receipt·ρ 게이트 verdict). 실패 실험도 전부 커밋(실패도 자산).

---

## 7. min 레인 스윕과의 조율 (모듈 9 도달 시에만 중요)

- 현재 min 레인 스윕은 config(`smoke_config_min_official_full_warm64_20260704.json`)만 준비되고 미실행. 누군가 이걸 시작하면 warm64 엔진을 재점유한다.
- **모듈 1~8은 백테 불요라 min 스윕과 무관하게 지금 진행.**
- **모듈 9(ρ 게이트·OOS)만** 엔진이 필요하니, 그 시점에 wt-dev의 boulder/ledger로 min 스윕 실행 여부를 확인하고 겹치지 않는 창에 배치. 겹치면 알파 검증을 뒤로 미루거나 별도 조율.

---

## 8. 착수 첫 명령 (요약)

```bash
cd C:/System_Trading/STOM/STOM_V.wt-alpha
# 1. §2 sanity check 실행
# 2. 설계서 §1.1, §3, §5 정독
# 3. mkdir alpha_lab && registry.py + tests/unit/test_alpha_registry.py 부터 TDD
# 4. 피처 25종(설계서 §3.2)을 preregistration_v1.json에 봉인, sha 커밋
```
목표: 약 1.5~2주에 MVP-1(규칙 채굴)·MVP-2(이벤트 스터디) 판정 도달. 두 MVP는 `dataset/reader.py`를 공유하므로 모듈 2까지 함께 만든 뒤 갈라진다.
