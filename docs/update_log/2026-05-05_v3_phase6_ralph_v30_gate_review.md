# V3 Phase 6 Ralph fallback: V3.0 gate 보정 검토

작성일: 2026-05-05  
대상 lane: `STOM_Version_3` 공식 V3 intake 준비  
작성 위치: `STOM_Version_2` 운영/문서 기준선  
관련 문서:

- `docs/update_log/2026-05-05_v3_official_intake_plan.md`
- `docs/update_log/2026-05-05_v3_phase6_preflight_dry_run.md`
- `docs/update_log/2026-05-05_v3_phase6_team_runtime_attempt.md`

---

## 1. 결론

Phase 6에서 바로 `STOM V3.0` source apply를 진행하지 않는다.

이유는 두 가지다.

1. Phase 5 문서의 `V3.0` 기준 commit `f6cb505720252be14849bb9c962ec75d29852cf5`는 **V3.0 marker가 처음 등장한 commit**으로는 유효하지만, 최신 upstream `_update.txt`의 `V3.0` section 전문과는 byte 단위로 일치하지 않는다.
2. Phase 6 dry-run 이후 upstream `refs/heads/V3.00`가 `9c8b3a16`에서 `e42dcfd9`로 추가 이동했다. 단, 최신 `_update.txt`의 V3 marker 범위는 여전히 `V3.0`부터 `V3.17`까지 18개이며, 추가 upstream commit 2개에는 새 V3 marker가 확인되지 않았다.

따라서 다음 `STOM V3.0` formal commit을 만들기 전 기준은 다음처럼 보정한다.

| 구분 | 기존 Phase 5/6 기준 | 보정 기준 |
| --- | --- | --- |
| upstream 최신 ref | `9c8b3a166b1fce77691a022d9521cb7833cad0ad` | `e42dcfd9e94731f09724c64c7568830854e1433d` |
| `V3.0` marker 최초 등장 | `f6cb505720252be14849bb9c962ec75d29852cf5` | marker 최초 등장 증거로만 유지 |
| 최신 `V3.0` section 전문과 최초 byte 일치 | 미확정 | `ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb` |
| `STOM V3.0` commit body | 최신 `_update.txt`의 `2026-04-18 V3.0` section 전문 | 동일. 단, 추출 기준 commit/body hash를 이 문서의 증거로 재고정 |
| source apply 진행 | 보류 | `ec7db11c` 기준 dry-run을 먼저 수행한 뒤 진행 |

---

## 2. 사용한 명령

```powershell
git status --short --branch
git worktree list
git rev-parse STOM_Version_2
git rev-parse STOM_Version_3
git rev-parse refs/remotes/devstom_tmp/V3.00_latest
git log --oneline --decorate --date=iso -5 refs/remotes/devstom_tmp/V3.00_latest
```

V3.0 section 검증은 `_update.txt`를 byte 단위로 읽어 다음 규칙으로 수행했다.

- header pattern: `^YYYY-MM-DD Vx.y$`
- `V3.0` section 시작: `2026-04-18 V3.0` header 시작 위치
- `V3.0` section 끝: 다음 version header 시작 위치
- 비교 기준: 최신 `refs/remotes/devstom_tmp/V3.00_latest:_update.txt`에서 추출한 `V3.0` section의 SHA-256

---

## 3. 현재 ref 상태

| ref | commit |
| --- | --- |
| `STOM_Version_2` | `04532cb554bbd8e883ddd202b9db800bd2d96647` |
| `STOM_Version_3` | `04532cb554bbd8e883ddd202b9db800bd2d96647` |
| `refs/remotes/devstom_tmp/V3.00_latest` | `e42dcfd9e94731f09724c64c7568830854e1433d` |
| `refs/remotes/devstom_tmp/tags/V3.0` | `d21e42425cfc6f2254431e8622b1bbf0dd89303e` |
| `refs/remotes/devstom_tmp/tags/V2.0` | `873d51eed3f581daa1925bcd9e3672254f525f0a` |

`STOM_Version_3` worktree 상태:

```text
## STOM_Version_3
!! _database/
```

즉, V3 source apply는 아직 시작하지 않았고, `_database/`는 runtime seed로만 존재하며 git staging 대상이 아니다.

---

## 4. 최신 `_update.txt` V3 marker gate

최신 upstream `_update.txt`의 V3 marker는 다음과 같다.

| 항목 | 값 |
| --- | --- |
| top V3 marker | `2026-05-04 V3.17` |
| oldest V3 marker | `2026-04-18 V3.0` |
| V3 marker count | `18` |
| formal commit order | `V3.0 -> V3.01 -> V3.02 -> V3.03 -> V3.04 -> V3.05 -> V3.06 -> V3.07 -> V3.08 -> V3.09 -> V3.10 -> V3.11 -> V3.12 -> V3.13 -> V3.14 -> V3.15 -> V3.16 -> V3.17` |

중요: 전체 `_update.txt`에는 V2 section도 함께 있으므로 전체 version header 수는 V3 marker 수와 다르다. V3 formal intake 판단에는 V3 marker 18개만 사용한다.

---

## 5. V3.0 section body 보정 증거

최신 upstream의 `2026-04-18 V3.0` section:

| 항목 | 값 |
| --- | ---: |
| bytes | `2490` |
| lines | `36` |
| SHA-256 | `d3560b7c970dca3d489375e18da55feaa5d1cd06a2c0e2d2a81046f5edb0d173` |

`_update.txt` 변경 이력에서 `V3.0` section이 최신 section과 처음으로 byte 단위 일치한 commit:

| 판정 | short | commit | 일시 | bytes | subject |
| --- | --- | --- | --- | ---: | --- |
| DIFF | `f6cb5057` | `f6cb505720252be14849bb9c962ec75d29852cf5` | 2026-04-18T11:40:40+09:00 | 2452 | DB 업데이트 파일 일자 수정 |
| DIFF | `93d0d8c8` | `93d0d8c89b583b1821a60ee38c3abb341bebf46d` | 2026-04-18T12:01:37+09:00 | 2450 | DB 업데이트 파일 일자 수정 |
| MATCH | `ec7db11c` | `ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb` | 2026-04-18T12:02:31+09:00 | 2490 | 업데이트 파일 갱신 |

결론:

- `f6cb5057`은 “V3.0 marker first-seen” 증거로만 사용한다.
- `STOM V3.0` formal commit body의 최신 section 일치 증거는 `ec7db11c`로 사용한다.
- source apply도 `f6cb5057` 단독 기준으로 진행하지 말고, 먼저 `STOM_Version_3..ec7db11c` 또는 더 정교한 version-boundary dry-run을 수행해야 한다.

---

## 6. Phase 6 이후 upstream drift

Phase 5/6 문서의 dry-run 기준은 `9c8b3a166b1fce77691a022d9521cb7833cad0ad`였다. 이후 upstream `V3.00`에는 다음 2개 commit이 추가되었다.

```text
e42dcfd9 분석시스템 실시간 매매용 넘바 함수에서 prange 삭제 - 조금 빠른 속도를 위해서 CPU 사용률이 90%이상 되는 현상 제거
9a71fc9f LS증권 실시간시세용 웹소켓 체결과 호가 두개로 분리
```

`9c8b3a16..e42dcfd9` file delta:

```text
M	strategy/analyzer_microstructure.py
M	strategy/analyzer_risk.py
M	strategy/analyzer_volatility_pattern.py
M	strategy/analyzer_volatility_stop_take.py
M	trade/base_strategy.py
M	trade/restapi_upbit.py
```

이 drift는 즉시 source apply 대상이 아니다. 새 `_update.txt` V3 marker가 없으므로 다음 중 하나가 확인될 때까지 stop line으로 둔다.

1. upstream `_update.txt`에 `V3.18` 또는 이에 준하는 새 section이 추가된다.
2. 운영자가 marker 없는 post-`V3.17` upstream commit을 어떤 formal commit에 포함할지 명시적으로 결정한다.
3. 별도 “post-marker intake” decision record를 작성하고 예외로 반영한다.

---

## 7. 다음 작업 지시

다음 페이지에서 수행할 일은 source apply가 아니라 **`STOM V3.0` 적용 전용 dry-run**이다.

권장 순서:

1. 최신 upstream ref를 다시 fetch한다.
2. `STOM_Version_3`가 깨끗한지 확인한다.
3. `ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb`를 `STOM V3.0` commit body 기준 commit으로 사용한다.
4. `STOM_Version_3..ec7db11c` name-status를 산출한다.
5. 다음 보호 목록을 제외/보존한다.
   - `.gitignore`
   - `AGENTS.md`
   - `CLAUDE.md`
   - `docs/`
   - `_database/`
   - `_log/`
   - `*.db`
   - `backtest/graph/`
6. source 후보 파일 목록과 protected/runtime 제외 목록을 문서화한다.
7. dry-run 결과가 안전하면 그 다음 페이지에서만 `STOM V3.0` source apply와 formal commit을 진행한다.

---

## 8. 중단 조건

다음 조건 중 하나라도 발생하면 `STOM V3.0` formal commit을 만들지 않는다.

- `STOM_Version_3` worktree에 예상하지 못한 tracked 변경이 있다.
- `ec7db11c` 기준 diff에 governance/runtime 파일이 섞여 있고 제외 정책이 불명확하다.
- `_update.txt`의 `V3.0` section 추출 결과가 이 문서의 SHA-256과 다르다.
- upstream `V3.00`가 다시 이동했고 새 V3 marker가 추가되었다.
- formal commit body가 `_update.txt` section 전문과 byte/line boundary 기준으로 불일치한다.

---

## 9. 다음 OMX 명령 후보

Team runtime은 현재 tmux pane 유지 실패가 재현되었으므로 fallback은 Ralph 단일 owner loop가 안전하다.

```powershell
omx ralph --no-deslop --prompt "V3 Phase 6 continuation: do not apply source yet. First run STOM V3.0-only dry-run using ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb as the corrected V3.0 body/source boundary candidate. Protect .gitignore, AGENTS.md, CLAUDE.md, docs/, _database/, _log/, *.db, and backtest/graph/. Report candidate files before any source apply."
```

대화형 `$ralph`로 진행할 경우 다음 프롬프트를 사용한다.

```text
$ralph V3 Phase 6 continuation --no-deslop. Do not apply source yet. First run STOM V3.0-only dry-run using ec7db11c1e6b4a4263327cdd5bf3b7514d4d62fb as the corrected V3.0 body/source boundary candidate. Protect .gitignore, AGENTS.md, CLAUDE.md, docs/, _database/, _log/, *.db, and backtest/graph/. Report candidate files before any source apply.
```