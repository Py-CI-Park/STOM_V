# Proxy OOS Timeout Diagnosis (2026-06-19)

## 원인

Q4 proxy OOS가 후보 실행 전에 warm-engine data loading 단계에서 멈춘 직접 원인은, 이전 warm-run 부모 프로세스가 사라진 뒤에도 repo cwd에서 `--multiprocessing-fork` 자식 프로세스들이 대량으로 남아 있었기 때문입니다. 확인된 orphan 프로세스 104개를 종료했습니다.

## 조치

1. repo cwd 기준 orphan multiprocessing fork 프로세스 104개 종료
2. timeout 발생 시 process tree를 정리하는 logged runner 추가
3. 기존 proxy run root와 evidence-local sqlite/wrapper 경계를 유지

## 재실행 순서

1. Q4 stress 재실행
2. Q4가 공식 evidence를 만들면 2022~2026 YTD 순차 실행
3. 후보별 성과/거래수/MDD/집중도 산출
4. pass/defer/reject/evidence_blocker 카드 갱신
