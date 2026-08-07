# Cause Disappearance Ledger

| cause id | expected truth | previous observation | last_seen | disconfirming observation | replacement cause | current status | violation gone? |
|---|---|---|---|---|---|---|---|
| CD-01 | v2 실패는 sell/risk 표 해석 오류가 고쳐지면 사라진다 | hold-time 90/120이 stop/take 값으로 잘못 표기됨 | 2026-07-09 | corrected audit 뒤에도 decision은 8 no_go; 7개 측정 손실 + 1개 무지표 오류 | 측정된 entry×exit 결합 실패 + 유효하지 않은 control | rejected | no |
| CD-02 | 게이트가 너무 엄격해서 survivor가 없다 | cap 35, daily 0.5 | 2026-07-09 | 7/7 profit 음수, MDD cap의 2.56~12.62배 | negative expectancy | rejected | no |
| CD-03 | 거래가 너무 적어 성과가 안 난다 | 이전 lattice의 low-daily issue | 2026-07-08 | v2 daily 20.5~143.9, 모두 손실 | adequate/high frequency with negative entry×exit expectancy; overfiring only some bodies | rejected | no |
| CD-04 | 몇 건의 큰 손실이 합계를 망쳤다 | aggregate profit만 볼 때 가능 | 2026-07-09 | 각 body median return<0; loss 상위 1% 비중 2.6~3.4% | diffuse common-mode losses | rejected | no |
| CD-05 | 엔진 장애가 8개 모두를 망쳤다 | body07 no-metrics | 2026-07-08 | 다른 7개 status=ok, 동일 엔진 Plan-D rows는 양수 가능 | body07 lane mismatch; that control remains inconclusive | mostly rejected | one control invalid |
| CD-06 | 매도만 고치면 해결된다 | 공통 TP/SL/hold exits | 2026-07-09 | body04 distinct exit도 손실; adverse MFE/MAE | entry×exit interaction | unresolved | n/a |
| CD-07 | AI 자율 loop 전체가 이번 실험에서 실패했다 | dashboard shows batch as latest | 2026-07-08 | artifact commit + provider=batch/current state + learning flags OFF | static v2 branch failed, autonomous loop untested here | rejected as overclaim | yes |
