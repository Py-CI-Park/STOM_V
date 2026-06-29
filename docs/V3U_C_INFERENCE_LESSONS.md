# V3U_C lane 결함 기록 진실 원천 (지속 관리)

- 최초 작성: 2026-05-22
- 대상 lane: `STOM_Version_3U_C`
- 본 문서 정책: V3U_INFERENCE_LESSONS.md와 동일 4단계 워크플로우 적용
- 갱신 주기: 결함 발견 즉시
- 상위 진실 원천: `docs/V3U_INFERENCE_LESSONS.md` (V3U pyd-free 결함 #1~#15 누적)

## 1. 본 문서의 목적

3U_C lane에서 발견되는 결함·근본 원인·재발 방지 액션을 누적 기록한다.

V3U lane의 `V3U_INFERENCE_LESSONS.md`가 pyd-free 추론 결함을 다룬다면, 본 문서는 **3U_C custom 작업 사이클**(E1~E4)에서 발견되는 결함을 다룬다.

## 2. 사이클 인벤토리

### 사이클 7 (2026-06-29): V3.34 흡수 (V3U lane 따라잡기) — 결함 0건

- 산출: merge commit `352a3838` (`git merge --no-ff STOM_Version_3U`)
- 흡수: V3.34 (해외주식 주문체결 처리 오류 수정, 바이낸스선물 감시종목제한 설정 추가) + V3U data-layer test adjustment
- 테스트: tests/v3u 49 + tests/v3uc 32 = 81 PASS, 통합 게이트 8/8, lane V3.34
- 발견 결함: 0건 (V3U runtime 보정 0건 순수 overlay 상속, merge 충돌 0)
- 사이클 5 hop 메커니즘 명문화 재사용 (V3U→3U_C는 git merge)

### 사이클 6 (2026-06-13): V3.33 흡수 (V3U lane 따라잡기) — 결함 0건

- 산출: merge commit `705fb7fd` (`git merge --no-ff STOM_Version_3U`)
- 흡수: V3.33 (전략탭 백테 시작 분리·명언 리스트 분리·빌트인 print 정리) + V3.32 tail fcc626a5
- 테스트: tests/v3u 49 + tests/v3uc 32 = 81 PASS, 통합 게이트 8/8, lane V3.33
- 발견 결함: 0건 (V3U 보정 0건 순수 overlay 상속, merge 충돌 0)
- 사이클 5 hop 메커니즘 명문화 재사용 (V3U→3U_C는 git merge)

### 사이클 5 (2026-06-13): V3.19~V3.32 흡수 (V3U lane 따라잡기) — 결함 0건

- 산출: merge commit `32900141` (`git merge --no-ff STOM_Version_3U`)
- 흡수: V3.19~V3.32 + 결함 #16 fix + A5 proc_chqs spawn + V3.32 TTS/homepg
- 테스트: tests/v3u 49 + tests/v3uc 32 = 81 케이스 PASS, 통합 게이트 8/8
- 발견 결함: 0건 (merge 충돌 0 + 런타임 소스는 V3U 검증분 그대로 상속)
- 핵심 교훈: **V3U→3U_C hop은 git merge, V3공식→V3U hop은 overlay/E1**. 혼동 금지
  (상세 docs/update_log/2026-06-13_v3uc_v319_v332_absorption.md "흡수 방식" 절)
- pyttsx_sound.py 삭제는 upstream 제거 전파(custom 손실 아님)
- 문서: docs/update_log/2026-06-13_v3uc_v319_v332_absorption.md

### 사이클 4 (2026-05-30): E2 V3U/3U_C 통합 CLI 도입

- 산출: scripts/v3uc_cli.py (~330 라인, 7 subcommand, 디스패처 패턴)
- 테스트: tests/v3uc/test_cli.py (16 케이스 PASS, 누적 32)
- 문서: docs/V3U_C_CLI_GUIDE.md (운영 매뉴얼)
- 발견 결함: 2건 (도구 자체 결함, V3 official 영향 없음) — §3 결함 #1·#2 참조
- V3U lane cross-link: V3U_NEXT_STEPS.md §5 사이클 12 등록

### 사이클 1 (2026-05-22): E1 V3.X 흡수 자동화 파이프라인 도입

- 산출: scripts/v3uc_ingest_pipeline.py (250+ 라인, 5 T-step)
- 테스트: tests/v3uc/test_ingest_pipeline.py (4 케이스 PASS)
- 문서: docs/V3U_C_INGEST_PIPELINE.md (운영 매뉴얼)
- 발견 결함: 0건 (신규 custom 작업이라 외부 호출 없음 + dry-run 안전)

## 3. 결함 기록 (지속 갱신, V3U lane과 같은 형식)

```
### 결함 #N (YYYY-MM-DD): 한 줄 제목

- 카테고리: V3U lane 카테고리(A/B/C/D/E) 또는 3U_C-specific
- 발견 경로: dry-run / live 사용자 / 자동 회귀 / V3.X 흡수 시
- 외부 호출 site: 파일:줄
- 우리 누락 위치: 파일:줄
- 수정 커밋: <hash>
- 회귀 테스트: tests/v3uc/...::...
- 근본 원인 매핑: V3U LESSONS §3-N
- 재발 방지 액션 매핑: V3U LESSONS §5-N 또는 신규
```

### 결함 #1 (2026-05-30): argparse `parents=` 시 subparser default가 부모 namespace를 None으로 덮어씀

- 카테고리: 3U_C-specific (도구 자체 결함, 외부 호출 없음)
- 발견 경로: pytest `test_main_gui_missing_stom_returns_2` 타임아웃 (subprocess 실행됨 → 실 stom.py 호출)
- 외부 호출 site: 없음 (CLI 신규 도구)
- 우리 누락 위치: `scripts/v3uc_cli.py:build_parser` — `common = ArgumentParser(add_help=False)`에 `--workspace`/`--dry-run` 등록 후 `parents=[common]`을 main parser와 subparser 모두에 전달했을 때, argparse가 subparser 처리 단계에서 `args.workspace` 를 None으로 reset → `_resolve_workspace(None) = Path.cwd()` → 실제 wt-3uc 작업 디렉터리에 stom.py 가 존재해 subprocess 실행 → 행
- 수정 커밋: 사이클 4 commit (V3U_C_NEXT_STEPS.md §5 참조)
- 회귀 테스트: `tests/v3uc/test_cli.py::test_main_gui_missing_stom_returns_2`, `test_main_gui_offscreen_sets_env`, `test_parser_dry_run_global`, `test_main_ingest_dispatches_with_version`
- 근본 원인: argparse known gotcha — `parents=` 가 child parser의 action default를 적용할 때 부모 namespace에 이미 설정된 값을 덮어씀
- 재발 방지 액션: 공유 옵션은 `default=argparse.SUPPRESS` 로 등록 + main()에서 `if not hasattr(args, X): args.X = default` 정규화

### 결함 #2 (2026-05-30): Windows cp949 콘솔에서 em-dash 등 비-cp949 글자 UnicodeEncodeError

- 카테고리: 3U_C-specific (도구 자체 결함, OS 환경 인코딩)
- 발견 경로: `python v3uc_cli.py --help` 실행 시 traceback (`'cp949' codec can't encode character '—'`)
- 외부 호출 site: 없음
- 우리 누락 위치: argparse description의 em-dash 출력 + Windows 기본 콘솔 codepage cp949
- 수정 커밋: 사이클 4 commit
- 회귀 테스트: `python v3uc_cli.py --help` 수동 smoke (자동 회귀는 monkeypatch로 sys.stdout 변경 없이 동작 검증)
- 근본 원인: Python 기본 sys.stdout 인코딩이 OS locale 따라 결정 — Windows 한글 환경에서 cp949가 됨
- 재발 방지 액션: 모든 v3uc 스크립트 헤드에 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` 가드 (try/except로 안전)

(추가 결함 발견 시 본 절에 누적)

## 4. 통계 (지속 갱신)

| 측정 | 값 (사이클 7 종료 시점, 2026-06-29) |
|---|---|
| 총 발견 결함 | 2 (#1 argparse parents, #2 cp949 인코딩) — 사이클 5~7 신규 0건 |
| 자동 회귀 테스트 | 3U_C custom 32 + V3U 안전망 상속 49 = 81 |
| 신규 자동 도구 | 4 (ingest_pipeline, db_compatibility_check, strategy_migration, cli) |
| 신규 문서 | 6 + 흡수 감사 2 (V3U V3.33/V3.34 pyd-free update logs 상속) |
| 활성 custom 작업 | E1·E5·E7·E2 완료, E3/E4/E6 미진행 |
| lane 버전 | **V3.34** (사이클 7, 사이클 6에서 V3.33 → V3.34) |
| custom 작업 카테고리 카탈로그 | E1~E7 (V3U_C_NEXT_STEPS.md) |

## 5. 운영 규칙

### 5.1 새 결함 발견 시 4단계 워크플로우

V3U lane과 동일:
1. 발견·진단 (사용자 보고 또는 자동 fail)
2. **V3U_C 전용 파일에서만 수정** (V3U 안전망 + V3 official 모두 0줄)
3. 회귀 테스트 추가 (`tests/v3uc/`)
4. 본 문서 §3 결함 기록 + §4 통계 갱신

### 5.2 V3U 안전망과의 경계

- V3U 안전망(`tests/v3u/`, `scripts/v3u_*`, `ui/main_window.py`) 변경이 필요하면
  **V3U lane(wt-3u)에서 별도 사이클로 fix 후 3U_C로 merge**
- V3U_C에서 V3U 안전망을 직접 수정하면 carry-forward registry 위반

### 5.3 cross-link 유지

- `docs/V3U_INFERENCE_LESSONS.md` (V3U pyd-free 결함, 상위)
- `docs/V3U_C_NEXT_STEPS.md` (V3U_C decision tree)
- `docs/CARRY_FORWARD_REGISTRY.md` (V3U_C custom allowlist rule)
- (V3U lane) `CLAUDE.md` 결함 발견·수정 4단계 워크플로우

## 6. 관련 문서

- `docs/V3U_C_INGEST_PIPELINE.md` E1 운영 매뉴얼
- `docs/V3U_C_NEXT_STEPS.md` 미래 결정 진실 원천
- `docs/CARRY_FORWARD_REGISTRY.md` V3U_C custom allowlist rule
- (V3U lane) `docs/V3U_INFERENCE_LESSONS.md` pyd-free 결함 진실 원천
- (V3U lane) `docs/V3U_NEXT_STEPS.md` V3U decision tree
- (V3U lane) `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` 3U_C 생성 전 중간 점검
