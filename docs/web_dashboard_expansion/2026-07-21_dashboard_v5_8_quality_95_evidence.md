# Dashboard v5.8.0 품질 95점 실행 증거

## 결론

Dashboard v5.8.0은 v5.7.0 감사 결과에서 확인한 네 가지 개선 축을 구현했다. 병합 기준은 코드 존재 여부가 아니라 자동 게이트와 브라우저 행렬의 통과 여부다.

| 개선 축 | 구현 | 검증 결과 | 판정 |
|---|---|---|---|
| 대용량 이중 데이터 성능 | 격리 임시 저장소에 34 campaigns, 10,728 generations, 1,054 runs, 1,860 wiki metadata rows 구성 | History cold 0.1851s / warm 0.0107s, Wiki cold 0.0305s / warm 0.0145s | PASS |
| HTML/PDF 동등성 | 등록 HTML 4건의 PDF companion 및 manifest provenance 필드 생성 | PDF publication 4/4, provenance check 4/4 | PASS |
| 차트 증거 계약 | 공통 ChartFrame, 메타데이터 6종, 상태 구분, 최대 200행 원자료 표, 요청 키/취소 및 유한값 검증 | v5.8 집중 테스트 75건, 전체 Dashboard/API 880건 통과 | PASS |
| 접근성 | axe-core, 키보드 포커스, 탭 계약, 가로 넘침, 테마·모션·폭 행렬 | 9 tabs × 6 widths × 2 themes × 2 motion = 216/216; serious/critical 0 | PASS |

## 재현 명령

```powershell
python -m pytest tests/unit/dashboard/test_v58_scale_gate.py tests/unit/dashboard/test_v58_accessibility_gate.py tests/unit/dashboard/test_v58_chart_frame.py tests/unit/dashboard/test_report_writer.py tests/unit/dashboard/test_sim_phase7_labels.py -q -p no:cacheprovider
python -m pytest tests/unit/dashboard/ tests/unit/test_history_api.py tests/unit/test_dashboard_research_docs.py -q -p no:cacheprovider
cd ai_strategy_loop/dashboard/webui-build
npm run build
cd ../../..
python scripts/verify_dashboard_v58_scale.py --output artifacts/v58_scale_gate.json
python scripts/export_research_report_pdfs.py --check
python scripts/verify_dashboard_v58_accessibility.py --base-url http://127.0.0.1:8770/ui/ --output artifacts/v58_accessibility_gate.json
python scripts/build_research_docs_index.py --check
python scripts/verify_nonrelease_sync.py
git diff --check
```

## 산출물 식별자

- Dashboard version: `v5.8.0`
- Runtime JSX graph: `91 JSX / 539 graph files`
- Runtime JSX digest: `0e0ef57b1af824552d4884a46482b328c9a2d8915791a21d7137a4df87d00270`
- App bundle: `app.js?v=15c4c554`
- App bundle SHA-256: `15c4c554a9fca1a731d13ad80f44223a69b114a055d525b07d9a61212867a9fd`
- axe-core: `4.10.2`
- axe source SHA-256: `b511cd9dec01c76f4b2ad1723b66b6db37d4c2eb4ed199076e1829d9ee7b75e3`
- Playwright: `1.60.0`
- Chromium: `148.0.7778.96`
- Focused verification: `75 passed`
- Full Dashboard/API verification: `880 passed`
- Independent closure review: report provenance `CLEAR`, chart/accessibility `CLEAR`

## 증거와 한계

- 성능 게이트는 실제 운영 DB를 복제하지 않고 격리된 합성 규모 fixture를 사용한다.
- `performance_proved=false`를 유지한다. 위 수치는 회귀 예산 통과 증거이며 실제 전략 성과나 운영 환경의 성능 향상 증명이 아니다.
- 접근성 게이트는 모든 axe 위반을 증거에 보존하고, release blocker는 `serious`/`critical`로 판정한다. `minor`/`moderate` 항목은 후속 개선 대상으로 남는다.
- V3K 승인 게이트 및 보호된 런타임 데이터에는 변경을 가하지 않았다.

## 품질 점수

| 영역 | v5.7 감사 기준 | v5.8 검증 후 | 근거 |
|---|---:|---:|---|
| Dashboard | 92 | 96 | scale, ChartFrame, 216-case accessibility gate |
| Report system | 93 | 96 | HTML/PDF companion, strict manifest/provenance, atomic publication |
| 통합 품질 | 92.5 | 96 | 독립 리뷰와 부모 브랜치 재검증을 병합 조건으로 적용 |

점수는 자동 게이트 범위에 대한 공학적 품질 평가다. 실제 투자 성과 또는 실거래 안정성 점수가 아니다.
