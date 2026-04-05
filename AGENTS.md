# STOM_Version_2 AI 에이전트 가이드

> **상세 가이드**: [`docs/stom_v2_update_guide.md`](docs/stom_v2_update_guide.md)

## Formal Update Entry Points

Read in this order before official update work:
1. `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
2. `docs/UPSTREAM_SYNC_STRATEGY.md`
3. `docs/WORKTREE_STRATEGY.md`
4. `docs/CARRY_FORWARD_REGISTRY.md`
5. latest cycle status under `docs/update_log/`

Current cycle status:
`docs/update_log/2026-04-05_v274_v277_cycle_status.md`

Current promoted state:
`V2 -> 2U -> 2U_C -> research/init`

`STOM_Version_2` remains the release-ingress branch. `STOM_V.wt-dev/` is the active `STOM_Version_2U_C` checkout, and `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/transition lane. Do not restore the retired live CLI child-lane model.

---

## 커밋 작성 언어 규칙

앞으로 이 저장소에서 만드는 신규 커밋은 아래 규칙을 기본으로 사용합니다.

- 커밋 제목 첫 줄은 한글로 작성합니다.
- 커밋 본문은 한글로 작성합니다.
- 커밋 본문은 마크다운 구조를 사용합니다.
- 권장 본문 구조:
  - `## 배경`
  - `## 변경 사항`
  - `## 검증`
  - 필요 시 `## 주의사항`
- 트레일러를 사용할 때도 한글 값을 우선합니다.
  - 예: `제약: ...`, `기각한안: ...`, `신뢰도: 높음`, `범위위험: 좁음`, `검증: ...`
- 영문 타입 접두사만 있는 제목(`docs: ...`, `fix: ...`)은 더 이상 기본 형식으로 사용하지 않습니다.
- 정식 버전 기록처럼 제목이 운영 규칙으로 고정된 커밋만 예외로 두고, 그 경우에도 본문은 한글 마크다운으로 작성합니다.

---

## 핵심 규칙 (필독)

1. **커밋 단위**: 배포 버전 1개 = 커밋 1개
2. **정식 버전 커밋 제목 예외**: `STOM V{major}.{minor}` (예: `STOM V2.50`)
3. **정식 버전 커밋 본문**: `_update.txt`의 해당 버전 섹션 전체
4. **스테이징**: zip 포함 파일만 (`CLAUDE.md`, `AGENTS.md`, `docs/`, `scripts/` 제외)
5. **버전 순서**: 오름차순 유지, 건너뛰기 금지

---

## 새 버전 업데이트 워크플로우

```bash
# 전체 자동 처리
python C:/System_Trading/stom_v2_update.py

# 미리보기 후 실행
python C:/System_Trading/stom_v2_update.py --dry-run
python C:/System_Trading/stom_v2_update.py

# Push
git push origin STOM_Version_2
```

전제: `C:\Users\parkc\Downloads\STOM_temp\STOM_V{버전}.zip` 존재

---

## 에이전트 체크리스트

- [ ] `STOM_Version_2` 브랜치에서 작업
- [ ] `--dry-run`으로 미리보기 확인
- [ ] `git log STOM_Version_2 --oneline -5`로 커밋 검증
- [ ] `git push origin STOM_Version_2` 완료

---

## 절대 금지

- `git add -A` 사용
- 여러 버전을 하나의 커밋으로 합치기
- `git rebase` / `git reset --hard`
- 개발 코드를 STOM_Version_2에 직접 커밋

---

## 현재 상태

- **자동화 스크립트**: `scripts/stom_v2_update.py` / `C:\System_Trading\stom_v2_update.py`
- **상세 가이드**: `docs/stom_v2_update_guide.md`
