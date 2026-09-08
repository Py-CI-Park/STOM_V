# SYS-05 SQ00 / F02 평가 통계 혼용 수정 TASK_RECEIPT

2026-09-08. 기능 branch `codex/process-research-sys-05-evaluation-stats`.
시작 commit `ba18e1413baa5d4b880157e46b79820839fab4ff`: RES-04P 정의 Gate 완료.
이 영수증을 포함한 commit은 로컬 개발 commit이며 loop 정본 병합/배포가 아니다.

## 결과

**평가 자료가 바뀌어도 발견 통계로 연구 필터를 통과하던 결함을 수정했다. SYS-05 전체 완료는 아니다.**

| 동일 합성 평가 자료 | 수정 전 | 수정 후 |
|---|---:|---:|
| 실제 평가 대상 표본 | 500 | 500 |
| 반환 support | 잘못된 발견값 5,000 | 500 |
| 반환 positives | 잘못된 발견값 4,000 | 400 |
| 반환 lift | 잘못된 발견값 2.0 | 1.3333333333333335 |
| bootstrap CI | [1.3333,1.3333] | [1.3333,1.3333] |
| 기본 연구 필터 반환 | 1개 | 0개 |

위 `adopt`는 합성 입력을 처리한 메모리 내 연구 필터 호출이다. 운영 전략 자동채택이나 실거래가 아니다.

## 원인·수정·하위호환

- H1 확인: 동일 16행/CI[2,2]에서 발견 통계만 100/100/9 ↔ 1/0/.1로 바꾸면 필터 반환이 1 ↔ 0으로 변했다.
- H2 기각: 실제 mask500, positive400, `_idx500/_pos_idx400/_n1000`은 정상이다.
- H3 기각: 실제 restart 모듈·Python3.13.13·NumPy2.3.5에서 공용 bootstrap point/CI가 4/3으로 정상이다.
- `alpha_lab/mining/stats.py::evaluate_leaves`: 평가 행 기준 support/positives/base_rate/lift 재집계. 공용 `_lift`, bootstrap, FDR 산식은 유지.
- 최초 발견 support/positives/lift를 `discovery_stats`로 복사해 보존. 재평가에서도 최초값 유지, 기존 입력 객체 불변.
- 새 정의 `evaluation_binary_lift_v2`, 범위 `PROVIDED_EVALUATION_ROWS_NOT_INDEPENDENCE_PROOF`. 같은 자료 평가일 수도 있으므로 독립 확인 주장 금지.
- `cli/alpha_mine.py::_serialize_rules`: 새 4개 metadata를 보고서까지 전달. 해당 key가 없는 구형 입력은 기존 형태로 허용.
- 과거 봉인 보고서 재작성/DB migration/새 table 없음. 미래 보고서부터 새 projection을 식별한다.

## 시험과 실제 사용 QA

로그: `C:/Users/parkc/STOM_Verification/v1.5_20260907/sys05-f02-*.log`.

| 검사 | 실제 결과 |
|---|---|
| 통계 red | 5 failed, 1 passed in 29.35s, exit1; `assert 5000 == 500` |
| 최초 library green | 39 passed in 32.37s, exit0 |
| 보고서 red | 1 failed, 6 deselected, exit1; `KeyError: stats_definition` |
| 최종 회귀+기존 mining/stats+CLI fixture 통합 | 66 passed in 42.05s, exit0 |
| 독립 code reviewer | 22 passed, exit0 |
| 독립 실제 library/report QA | 기본 재현·빈mask·전체음성·재평가·JSON sanitize PASS, exit0 |
| 신규 시험 lint | E,F,I,C90,UP,B,SIM,TCH PASS |

최종 묶음 명령:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/unit/test_alpha_mining_evaluation_scope.py tests/unit/test_alpha_mining.py tests/unit/test_alpha_stats_common.py tests/unit/test_alpha_cli.py -q -p no:cacheprovider --basetemp=C:/Users/parkc/STOM_Verification/v1.5_20260907/sys05-f02-cli-temp
```

CLI 시험은 기존 `tmp_path` 합성 SQLite·임시 run-dir fixture만 사용한다. 운영 back DB 분석을 실행하지 않았다. 독립 QA는 실제 evaluator/serializer/json_sanitize 호출로 JSON null·내부키 제거·발견값 보존도 확인했다. 브라우저 QA나 전체 페이지 수용시험 완료로 보고하지 않는다.

정적 분석: F02 관련 3파일 basedpyright는 **10 errors / 196 warnings로 전체 PASS가 아니다**. 10개 오류는 부모 코드에도 있는 미매개변수 `dict` 선언(stats8, serializer2)이다. 새 테스트의 TypedDict→구형 dict 경계 오류 4개는 명시적인 사본 변환으로 제거했다. 이번 좁은 결함 수정에 기존 typing 전체 이관을 섞지 않았다. 별도 typed mining contract 작업에 남긴다. 설치 NumPy2.3.5와 requirements64.txt의2.4.4도 다르며 이 시험은 관측된 로컬 환경의 결과다.

## 독립 검토 결과

| 영역 | 판정 | 범위 |
|---|---|---|
| res04_goal | PASS | SQ00 목적·RES04P 이후 순서·경제권한 불변 |
| res04_code | PASS | 실제 평가 집계·하위호환·재평가 |
| res04_qa | PASS | 원래 잘못 통과하던 입력이 반환0으로 변경 |
| res04_security | PASS | 메모리 계산/보고서 필드만 변경 |
| res04_context | PASS | 원문 F02 경계·CLI 연결·미완료 권고 구분 |

## 남은 범위·롤백

F02 감사 권고 전체 완료는 아니다. train/eval dataset identity의 명시적 연결, 독립 확인 파이프라인, FDR 보정 타당성, 연속형 라벨, typed mining contract는 후속 단계다. 다음은 SQ01의 실제 CSV loader + TradeArtifactContract + typed DQ.

새 JSON 3개의 raw hash가 Git CRLF 변환으로 바뀌지 않도록 별도 `.gitattributes` commit으로 -text를 지정했다. 현재 bytes와 `git -c core.autocrlf=true cat-file --filters HEAD:<path>` 출력 hash가 3개 모두 일치했다. 원본 evidence는 변경하지 않았다.

롤백은 이 기능 commit의 stats/serializer/새회귀 변경만 새 역변경 commit으로 되돌린다. RES-04P 정의 Gate·사용자 데이터·봉인 보고서는 되돌리지 않는다. 신규 버전 보고서는 버전별로 보존한다. 디버그 instrumentation/서버/포트는 만들지 않았고 임시 debug journal은 인계 후 제거한다.
