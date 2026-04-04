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

Canonical propagation order:
`V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`

---

## 핵심 규칙 (필독)

1. **커밋 단위**: 배포 버전 1개 = 커밋 1개
2. **커밋 제목**: `STOM V{major}.{minor}` (예: `STOM V2.50`)
3. **커밋 본문**: `_update.txt`의 해당 버전 섹션 전체
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
