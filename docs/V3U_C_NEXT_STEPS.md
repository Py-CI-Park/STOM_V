# V3U_C lane Next Steps Decision Tree (지속 관리)

- 최초 작성: 2026-05-22
- 대상 lane: `STOM_Version_3U_C`
- 갱신 주기: 매 V3U_C 사이클 종료 시 §5 선택 이력 추가
- 상위 진실 원천: `docs/V3U_NEXT_STEPS.md` (V3U lane decision tree, V3U_C 옵션 그룹 E 정의)

## 1. 본 문서의 목적

3U_C lane의 미래 결정 옵션을 정렬한다. V3U lane이 `V3U_NEXT_STEPS.md`로 옵션 카탈로그 운영하는 것과 동일 패턴.

## 2. 현재 상태 (사이클 1 종료, 2026-05-22)

| 지표 | 값 |
|---|---|
| 활성 사이클 | 1 (E1 V3.X 흡수 자동화 파이프라인 도입) |
| 결함 누적 | 0 |
| 회귀 테스트 | 4 |
| 신규 자동 도구 | 1 (v3uc_ingest_pipeline.py) |
| commit 누적 | (사이클 1 commit hash는 §5 기록) |
| V3U 안전망 상속 상태 | 46 pytest + baseline 0 (3U_C 워크트리에서 collect 정상) |

## 3. 옵션 카탈로그

V3U lane V3U_NEXT_STEPS.md 그룹 E의 V3U_C custom 작업 옵션 (E1~E4) + 3U_C-specific 옵션 추가.

### E1: V3.X 흡수 자동화 파이프라인 ✅ **사이클 1 완료**

- 산출: scripts/v3uc_ingest_pipeline.py + tests/v3uc/test_ingest_pipeline.py + docs/V3U_C_INGEST_PIPELINE.md
- 운영: V3.19 발표 시 `--dry-run` → 성공 시 `--live` 호출

### E2: STOM_CLI 자동화 + V3U 통합 ⏳ 미진행

- 후보 작업: 단축키 + 자동화 시나리오 (테스트 실행·verifier·debug 1-key)
- 2U_C `STOM_CLI_AI_AUTOMATION_PLAN.md` 패턴 참고

### E3: 실시간 모니터링 dashboard ⏳ 미진행

- 후보 작업: `ui.web_dashboard` 활성화 (V3U lane 결함 #15에서 placeholder만 부착)
- 자체 web server worker + 사이드카 승인 패턴 (2U_C 참고)

### E4: 고급 백테 자동화 ⏳ 미진행

- 후보 작업: 백테 결과 자동 분석 + GA + Optuna 자동 ranking
- 2U_C V3K mapping 지도 패턴 참고

### E5: DB 마이그레이션 호환성 진단·자동 PK 추가 도구 ✅ **사이클 2 완료** (2026-05-22)

- 산출: scripts/v3uc_db_compatibility_check.py + tests/v3uc/test_db_compatibility.py + docs/V3U_C_DB_MIGRATION_PLAN.md
- 동작: --scan (read-only PK 매트릭스) / --add-pk (자동 추가, 백업 검증) / --analyze-extra (기타 DB)
- 운영: 사용자가 update_db_20260418.bat 후 호출 (V3.08+ 호환성 검증)

### E6 (신규 후보): T-step extension (T06 pre-flight + T07 notification)

- E1 운영하며 발견되는 패턴을 본 옵션으로 흡수
- T06: V3 upstream fetch + delta 미리 보기 (사용자 결정 보조)
- T07: 흡수 완료 후 Telegram/email 알림

### E6 (신규 후보): multi-version 흡수

- E1을 V3.19 + V3.20 연속 처리 가능하도록 확장
- 각 버전별 audit JSON 누적

## 4. 우선순위 추천 매트릭스

| 우선순위 | 옵션 | 사유 |
|---|---|---|
| 🟢 1 | E1 운영 dry-run (V3.19 발표 시) | 사이클 1 산출물 첫 실 사용 |
| 🟡 2 | E2 STOM_CLI 자동화 | V3U 동작 단축키화 — 일상 사용 편의 |
| 🟠 3 | E3 실시간 dashboard | web_dashboard 활성화 + 사이드카 패턴 도입 |
| 🔵 4 | E4 고급 백테 자동화 | 백테 자동 최적화 — 사용자 trading workflow 핵심 |
| ⚪ 5 | E5·E6 (E1 운영 후 확장) | E1 실 운영 사이클 후 자연 발견 |

## 5. 선택 이력 (지속 갱신)

```
### 사이클 N (YYYY-MM-DD): 선택 옵션 / 결과 요약

- 사용자 선택: <옵션 ID>
- 실행 결과: <commit hash, pytest 케이스 변화, 결함 N건 fix>
- 발견 신규 결함: <카테고리·#번호 또는 "없음">
- 본 문서 갱신: <§3·§4 변경 요약>
- 다음 사이클 후보: <다음 우선순위 옵션>
```

### 사이클 1 (2026-05-22): E1 V3.X 흡수 자동화 파이프라인 도입

- 사용자 선택: "E1 진행"
- 실행 결과:
  - scripts/v3uc_ingest_pipeline.py (5 T-step, ~270 lines)
  - tests/v3uc/test_ingest_pipeline.py (4 unit test 케이스, 모두 PASS)
  - docs/V3U_C_INGEST_PIPELINE.md (운영 매뉴얼)
  - docs/V3U_C_INFERENCE_LESSONS.md (결함 진실 원천 신규)
  - 본 문서 (NEXT_STEPS 신규)
- 발견 신규 결함: 0건 (dry-run 안전, 단위 테스트로 검증)
- 다음 사이클 후보:
  - E1 실 운영 (V3.19 발표 시 dry-run → live)
  - E2/E3/E4 중 선택 (3U_C lane 발전)

## 6. 운영 규칙

### 6.1 사이클 종료 시점의 정의

V3U lane과 동일 (V3U_NEXT_STEPS.md §6.1).

### 6.2 본 문서 갱신 의무

각 사이클 종료 시 다음 수행:
1. §2 현재 상태 표 갱신
2. §5 선택 이력에 본 사이클 항목 추가
3. §3 옵션 카탈로그에 신규 옵션 추가 또는 완료 옵션 표시
4. §4 우선순위 매트릭스 재평가

### 6.3 V3U lane과의 진실 원천 동기화

- V3U lane V3U_NEXT_STEPS.md §5 사이클 이력에도 V3U_C 사이클 진행을 간략히 기록
- 본 문서가 V3U_C 상세 기록의 진실 원천

## 7. 관련 문서

- `docs/V3U_C_INGEST_PIPELINE.md` E1 운영 매뉴얼
- `docs/V3U_C_INFERENCE_LESSONS.md` 결함 진실 원천
- `docs/CARRY_FORWARD_REGISTRY.md` V3U_C custom allowlist rule
- (V3U lane) `docs/V3U_NEXT_STEPS.md` V3U decision tree (V3U_C 옵션 그룹 E 정의)
- (V3U lane) `docs/V3U_INFERENCE_LESSONS.md` pyd-free 결함 진실 원천
- (V3U lane) `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` 3U_C 생성 전 중간 점검
