# 대시보드 리모델 캡처 반영도 재채점

- 기준: Reference captures under ai_strategy_loop/dashboard/frontend/remodel/docs/captures versus current 8776 captures under artifacts/runtime/zip-parity-current at 1920x1080.
- 정정: The previous 100/100 was entrypoint/function-presence/safety verification. Capture-to-capture visual parity is not 100; the corrected average is lower because live backend state changes visible values and the static prototype differs from production feature depth on backtest/replay.

## 종합 점수

- 캡처 픽셀/구조 유사도 평균: 71.5/100
- DOM/정보구조 반영 평균: 89.9/100
- 기능 반영 평균: 79.8/100
- 보정 총점 평균: 79.6/100

## 페이지별 점수

|페이지|캡처 유사도|구조 점수|기능 점수|보정 총점|차이 요약|
|---|---:|---:|---:|---:|---|
|조건식 AI|72.3|92|84|81.5|상단/탭/3-column 카드 구조는 일치. 차이는 백엔드 실시간 값(8776, idle, Gen -1, 0.0%)이 참조 더미값(9200, running, Gen 137, 68.5%)을 덮어쓴 데서 크게 발생.|
|프로세스|71.6|90|82|80.1|페이지 골격은 일치. 참조 대비 상단 런 상태와 일부 로그/메타 값이 달라 텍스트 edge 차이가 큼.|
|히스토리|70.0|90|82|79.4|표/차트/사이드 패널 배치는 유사하나 run 목록이 live/fallback 데이터와 랜덤성 일부 영향을 받아 다름.|
|연구실|72.4|92|82|81.2|히트맵·중요도·검증 요약 구성은 비교적 가장 가까움.|
|분석 워크벤치|71.7|90|82|80.2|후보 카드/월별 히트맵/상세 차트 구성은 유지. 텍스트·후보값 차이 존재.|
|결정 감사|71.9|90|84|80.7|감사 레이아웃/append-only 문구/결정 입력은 일치. 표·체크리스트 값 차이 존재.|
|백테스트|71.5|88|72|77.4|압축파일의 백테스트 정적 구성이 반영됨. 다만 기존 production 백테스트의 실제 실행 폼과는 UI 밀도/동작 깊이가 다름.|
|차트 리플레이|70.2|87|70|76.0|차트 리플레이 구획은 반영. reference/current 모두 정적 데모형이며 기존 production replay 대비 기능형 조작 깊이는 낮음.|

## 증거

- 비교 contact sheet: `artifacts/runtime/zip-parity-compare/side-by-side-contact-sheet.png`
- 상세 JSON: `artifacts/runtime/zip-parity-compare/detailed-scorecard.json`
- 원본 metric JSON: `artifacts/runtime/zip-parity-compare/visual-parity-report.json`
