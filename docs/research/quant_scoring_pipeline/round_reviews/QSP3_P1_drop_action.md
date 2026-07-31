# QSP3 P1 게이트 — drop_leaf 액션 프로세스 내장 (2026-07-31)

> 채점 방식 변경: 감사 지적(동일 컨텍스트 자가승인 무효)에 따라 **자가점수를 매기지 않는다.**
> 본 문서는 증거 체크리스트만 기록하고, 점수는 P5 독립 감사 2건이 부여한다.

## 구현 (커밋 참조)

| 항목 | 내용 | 증거 |
|---|---|---|
| 제안 | `surgeon.propose_drops` — 설계+홀드아웃 **양쪽 손실** 리프만, 설계 손실 순 top_k, 손실 점유율 2% 미만 제외, 기시도 리프 제외 | test_propose_drops_requires_both_windows_losing / _respects_exclude |
| 적용 | `apply_drop` — 대상 리프 첫 절 줄만 `if/elif True: # DROP_LEAF` 교체(줄 좌표 = hier_ast lineno), compile 검사 | test_apply_and_verify_drop_roundtrip |
| 검증 | `verify_drop` — 리프 키 집합 불변 + 대상 외 전 리프 (ident,consts) 동일 + 대상 첫 절 ident '?' | test_verify_drop_rejects_out_of_scope_change (변조 검출) |
| 러너 | `--actions drop,tighten` — drop 가능 시 우선, 소진 시 조임 폴백. 홀드아웃 라벨 CSV 는 직전 라운드 홀드아웃 run(첫 라운드는 `<holdout_config>.baseline.json`) | round_runner.py `_holdout_label_csv` |
| 재유입 기록 | 후보별 `추정 Δ`(빼기) vs `실측 Δ`(재백테) 차 = reentry_cost 를 record["reentry"] 에 저장·출력 | DROP3 프로브 실증(21~38%) 규칙의 자동화 |
| 이미 드롭 가드 | 드롭된 리프(첫 절 '?')는 재제안·재적용 불가 | test_apply_drop_refuses_already_dropped |

## 사용자 규칙 반영 확인

| 규칙 | 반영 |
|---|---|
| "제거 채택은 항상 재백테 실측" | 추정은 후보 순위에만 사용, 채택은 기존 공식 배치 실측 경로 그대로 |
| "홀드아웃 동방향" | 후보 사전필터(양쪽 손실) + 기존 홀드아웃 동반 판정(과최적 괴리 발산) 이중 |
| 파서 호환 | 드롭 코드 hier_ast 파싱 정상(P0 검증: 16리프 유지, 드롭 리프 ident '?') |

## 테스트

- 신규 5(test_surgeon_qsp3.py) + 회귀 32(revision/convergence) = 37/37 PASS.

## 남은 한계 (원장 이관)

- 드롭 인코딩이 첫 절만 무력화 — 나머지 절은 dead code 로 남음(가독성; 기능 무해).
- `_holdout_label_csv` 는 holdout run 의 CSV 존재를 가정 — CSV 청소 시 drop 모드 자동 강등(조임 폴백).
