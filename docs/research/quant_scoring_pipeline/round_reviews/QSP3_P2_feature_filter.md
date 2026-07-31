# QSP3 P2 게이트 — 특징 영역 일반화: feature_map + add_filter (2026-07-31)

> 자가점수 없음 — 증거 체크리스트만. 채점은 P5 독립 감사 2건.

## 구현

| 항목 | 내용 | 증거 |
|---|---|---|
| 다차원 맵 | `feature_map.grid(csv, x, y, bins)` — 변수 선택형 1D/2D 분위 구간 손익(거래수·손익합·평균수익률·승률) | test_feature_map_grid_and_loss_regions (합계 보존 검증) |
| 손실 영역 랭킹 | `loss_regions(csv)` — 전 변수 1D 스캔, "이 매수 특징 = 손실" 자동 후보 목록 | 동일 테스트 |
| 필터 제안 | `filtersmith.propose_filters` — 손실 리프 × **FDR(BH, q≤0.10) 통과 변수만** × 분위 임계 스윕, 설계·홀드아웃 **양쪽 추정 이득>0** + 제거율≤60% 캡, 리프당 1개 | test_propose_filters_finds_separating_variable |
| 적용/검증 | 리프 절 체인 끝에 `elif not (X op t)` 1절 삽입, verify_filter 가 "대상 리프 끝 1절 추가 외 diff 0" 강제 | roundtrip + 변조 검출 테스트 |
| 러너 | actions 우선순위 drop→filter→tighten, 기시도 (변수,리프) 제외, 재유입 기록을 est 보유 명세 전반으로 일반화 | round_runner.py |
| 변수 안전성 | 허용 = B_*만(이름 기반 캡처 설계상 런타임 동일 변수 보장), 가격축·구조축 제외, **D_* 파생 제외**(식 합성·0나눗셈 — 단위 사고 재발 방지) | filtersmith._runtime_var |

## 감사 백로그 해소 표시

| 백로그 | 상태 |
|---|---|
| B1: 제안 경로 FDR 미배선 | **filter 경로에 배선 완료**(리프 family BH). tighten 경로는 잔여(원장 유지) |
| A4: action 1종(tighten)뿐 | drop_leaf + add_filter 추가 — 계약 4종 중 3종 |

## 테스트

52/52 PASS (신규 filtersmith/feature_map 4 + surgeon 5 포함 전체 회귀).
