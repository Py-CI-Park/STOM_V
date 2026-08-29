# 핸드오프 — SYS-04 완료 후 새 구조 가설 검토 재개

> 작업 폴더: `C:\System_Trading\STOM\STOM_V.wt-process-research-restart`
>
> SYS-04 기능 commit: `2d73a9f7`
>
> 정본 병합 SHA: 문서 병합 후 이 문서에 확정
>
> push: 하지 않음

---

## 0. 30초 요약

```text
SYS-04              COMPLETE
Fast Gate           7,928 PASS · 27 SKIP · 23m22s
Slow Gate           24 PASS · 19m04s
경제 후보           0/7 STOP
새 연구             NOT STARTED
Holdout             SEALED_NOT_TOUCHED
다음                새 구조 가설 검토 문서
주의                0-byte strategy.db 확인·제거 필요
```

---

## 1. 새 세션에서 읽을 순서

1. `2026-08-30_SYS-04_Fast_Slow_Unit_Gate_구현결과.md`
2. `2026-08-29_전체완료단계_남은단계_필수성_연구상태_종합검토.md`
3. `2026-08-28_ANA-04_Failure_Autopsy_구현결과.md`
4. `2026-08-26_RES-03_G1_구조후보_사전등록.md`
5. 본 핸드오프

---

## 2. 시작 전 안전 확인

```powershell
Set-Location 'C:\System_Trading\STOM\STOM_V.wt-process-research-restart'
git branch --show-current
git rev-parse HEAD
git status --short
python scripts/build_research_docs_index.py --check

$dbPath = 'C:\System_Trading\STOM\STOM_V.wt-process-research-restart\_database\strategy.db'
if (Test-Path -LiteralPath $dbPath) {
    Get-Item -LiteralPath $dbPath | Select-Object FullName, Length, CreationTime, LastWriteTime
}
```

예상 Git dirty는 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt` 하나다. `_database/strategy.db`가 0-byte인 경우 구현 결과 문서의 guarded cleanup 절차를 따른다. 0-byte가 아니면 삭제하지 않는다.

---

## 3. 다음 브랜치

```text
codex/process-research-res-04-hypothesis-review
```

정본 `loop/process-research-pipeline`의 SYS-04 최종 병합 SHA에서 생성한다.

---

## 4. 다음 단계의 목적

| 질문 | 답 |
|---|---|
| 바로 새 G0를 실행하는가 | 아니다 |
| 기존 G1 threshold를 미세조정하는가 | 아니다 |
| 무엇을 먼저 하는가 | ANA-04 실패를 설명하는 새 구조 가설을 비교한다 |
| 필요한 산출물 | 가설 후보·반증 조건·데이터 필요량·누수 위험·비용·중지 규칙 표 |
| 연구 실행 권한 | 가설 검토 문서에는 없음 |

---

## 5. RES-04 hypothesis review 완료 조건

```text
새 구조 가설 3개 이상
├── 기존 G1의 단순 threshold 이동이 아님
├── ANA-04 Family/Fold/MDD/Exit 실패를 설명
├── entry-time 정보만 사용
├── 필요한 데이터·표본·비용 명시
├── 반증 가능한 예측 명시
├── negative control 명시
└── 실행 전 STOP 기준 명시
```

이 검토에서 가장 타당한 가설이 없으면 새 G0를 실행하지 않고 정상 중지한다.

---

## 6. 이후 전체 순서

```text
SYS-04 완료
   │
   ▼
새 구조 가설 비교
   │
   ├── 적합 가설 없음 ──> STOP / 추가 데이터·분석 요청
   │
   └── 적합 가설 있음
          ▼
      RES-04 사전등록
          ▼
        새 G0
          ▼
       구조 부검
          ▼
       조건부 G1
          ▼
 Controls / FDR / Posterior
          ▼
 Robust 후보가 있을 때만 Frozen OOS
```

---

## 7. 다음 실행 프롬프트

```text
C:\System_Trading\STOM\STOM_V.wt-process-research-restart 에서
HANDOFF_2026-08-30_SYS-04_완료_새구조가설_RESTART.md 와
2026-08-30_SYS-04_Fast_Slow_Unit_Gate_구현결과.md 를 먼저 읽어라.

현재 loop/process-research-pipeline 정본 HEAD와 dirty 상태를 확인하고,
0-byte _database/strategy.db가 있으면 크기와 경로를 사용자에게 보여준 뒤
문서의 guarded cleanup 경계를 지켜라.

codex/process-research-res-04-hypothesis-review 브랜치를 생성한다.
ANA-04의 7후보·5Family·28Fold·MDD·Exit 실패를 근거로,
기존 threshold 미세조정이 아닌 새로운 구조 가설을 최소 3개 비교하라.

각 가설에 반증 조건, entry-time 변수, 데이터 필요량, 비용, negative control,
중지 규칙, G0 가능성을 표로 작성하라.

연구 실행, G2, Holdout, 자동채택, 운영 DB write는 하지 마라.
가설 검토 문서만 별도 commit하고 restart→loop 순서로 병합하라.
```

---

## 8. 불변식

- Platform PASS ≠ Economic success ≠ OOS ≠ Live
- Development `0/7 STOP`
- Holdout `SEALED_NOT_TOUCHED`
- 새 연구는 RES-04 사전등록 전 실행 금지
- `git add -A` 금지
- push는 사용자 별도 지시 전 금지
- tmap feedback과 원 `STOM_V.wt-dev` 보호
