# 핸드오프 — Compact 이후 합리적 권장 순서

> **compact 이후 가장 먼저 읽을 문서**
>
> 작업 폴더: `C:\System_Trading\STOM\STOM_V.wt-process-research-restart`
>
> 현재 정본: `loop/process-research-pipeline` @ `35bad5da`
>
> 문서 커밋: `3f85dae3` · 재출발 병합: `b34ad4cd` · 파이프라인 병합: `35bad5da`
>
> 종합 검토: `2026-08-29_전체완료단계_남은단계_필수성_연구상태_종합검토.md`
>
> push: 하지 않음

---

## 0. 30초 요약

```text
플랫폼·UX·분석      상당 부분 완료
기존 <3000> 연구    G0/G1 완료 · DEV 0/7 STOP
새 후보 탐색        현재 중지
Holdout             SEALED
다음 합리적 단계    SYS-04 suite performance
```

| 질문 | 답 |
|---|---|
| 지금 새 연구 중인가 | 아니다. 기존 연구는 STOP, 플랫폼 성숙화 중이다. |
| 수익 후보가 있는가 | 없다. 0/7이다. |
| 바로 G2/OOS 가능한가 | 아니다. |
| 다음은 꼭 SYS-04인가 | 계속 개발한다면 강력 권장, 연구 종료라면 생략 가능 |
| 새 연구를 하려면 | 새 구조 가설과 RES-04 사전등록이 필수 |

---

## 1. 재개 순서

```text
1. git branch/status/log 재확인
2. 본 핸드오프와 종합 검토 읽기
3. SYS-04 전용 branch 생성
4. 18~19% 느린 테스트 파일 측정
5. marker만 분리, assertion/coverage 유지
6. fast Gate와 slow receipt 검증
7. 문서·commit·restart→loop 병합
8. 새 구조 가설 검토로 이동
```

---

## 2. 다음 브랜치와 완료 조건

```text
codex/process-research-sys-04-suite-performance
```

| 완료 조건 | 기준 |
|---|---|
| 병목 식별 | 파일·test ID·소요시간 실제 측정 |
| fast Gate | 느린 통합 테스트 제외 이유가 marker로 명시 |
| slow Gate | 삭제 없이 push/nightly 명령 유지 |
| 정확성 | 기존 assertion·coverage 변경 없음 |
| 보호 | DB·연구 evidence write 없음 |

---

## 3. SYS-04 이후 권장 순서

```text
SYS-04 suite performance
        ↓
RES-04 새 구조 가설 검토 문서
        ↓
RES-04 preregistration
        ↓
새 G0
        ↓
구조 부검
        ↓
조건부 G1
        ↓
Controls/FDR/Posterior
        ↓
후보 있을 때만 Frozen OOS
```

---

## 4. 정확한 재개 명령

```powershell
Set-Location 'C:\System_Trading\STOM\STOM_V.wt-process-research-restart'
git branch --show-current
git rev-parse HEAD
git status --short
git log -8 --oneline
python scripts/build_research_docs_index.py --check
python scripts/verify_nonrelease_sync.py
```

예상 확인값:

```text
branch: loop/process-research-pipeline
HEAD: 35bad5da 또는 그 후속
dirty: tmap feedback 1개만 허용
```

---

## 5. Compact 이후 실행 프롬프트

```text
C:\System_Trading\STOM\STOM_V.wt-process-research-restart 에서
docs/research/quant_scoring_pipeline/HANDOFF_2026-08-29_COMPACT_이후_합리적_권장순서.md 와
2026-08-29_전체완료단계_남은단계_필수성_연구상태_종합검토.md 를 먼저 읽어라.

현재 loop/process-research-pipeline 정본 HEAD와 dirty 상태를 확인하고,
codex/process-research-sys-04-suite-performance 브랜치를 생성한다.

전체 unit suite 89분 중 18~19% 장시간 테스트를 실제 duration으로 식별하고,
assertion과 coverage를 삭제하지 않은 채 fast commit Gate와 slow push/nightly Gate로 분리하라.

연구 실행, G2, Holdout, threshold 변경, 운영 DB write는 하지 마라.
완료 후 기능/문서 커밋을 분리하고 restart→loop 순서로 병합하라.
```

---

## 6. 불변식

- Platform PASS ≠ Economic success ≠ OOS ≠ Live
- Development 0/7 STOP 유지
- Holdout `SEALED_NOT_TOUCHED`
- G2 금지
- 새 연구는 새 구조 가설·사전등록 전 실행 금지
- `git add -A` 금지, 경로 명시 stage
- push는 사용자 별도 지시 전 금지
- tmap feedback과 `STOM_V.wt-dev` dirty 보호
