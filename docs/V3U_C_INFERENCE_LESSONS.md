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

(첫 결함이 발견되면 본 절에 추가)

## 4. 통계 (지속 갱신)

| 측정 | 값 (사이클 1 종료 시점) |
|---|---|
| 총 발견 결함 | 0 |
| 자동 회귀 테스트 | 4 (test_ingest_pipeline 4 케이스) |
| 신규 자동 도구 | 1 (v3uc_ingest_pipeline.py) |
| 신규 문서 | 3 (INGEST_PIPELINE + LESSONS + NEXT_STEPS) |
| 활성 custom 작업 | E1 (V3.X 흡수 자동화 파이프라인) |
| custom 작업 카테고리 카탈로그 | E1~E4 (V3U_NEXT_STEPS.md 그룹 E) |

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
