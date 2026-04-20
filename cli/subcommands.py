"""서브커맨드 라우터 — formula, strategy 서브커맨드 처리."""
import argparse
import json

from cli.paths import DB_STRATEGY


# Keep aligned with cli.config.parse_args --divid-mode choices.
DIVID_MODE_CHOICES = ('종목코드별 분류', '일자별 분류', '한종목 로딩')


def create_subcommand_parser():
    """서브커맨드 파서 생성."""
    from cli.version import DISPLAY_VERSION
    parser = argparse.ArgumentParser(prog='stom_backtest')
    parser.add_argument('--version', action='version',
                         version='STOM CLI Backtest Runner %s' % DISPLAY_VERSION)
    sub = parser.add_subparsers(dest='command')

    from cli.config import BacktestConfig
    config_defaults = BacktestConfig()

    runtime_preflight = sub.add_parser(
        'runtime-preflight',
        help='CLI 백테스트 실행 전 runtime DB, 전략코드, 실행 조건을 검증',
    )
    runtime_preflight.add_argument('--buy', required=True)
    runtime_preflight.add_argument('--sell', required=True)
    runtime_preflight.add_argument('--start', type=int, required=True)
    runtime_preflight.add_argument('--end', type=int, required=True)
    runtime_preflight.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    runtime_preflight.add_argument('--betting', default='1')
    runtime_preflight.add_argument('--avg-time', type=str, default='60')
    runtime_preflight.add_argument('--start-time', type=int, default=90000)
    runtime_preflight.add_argument('--end-time', type=int, default=152800)
    runtime_preflight.add_argument('--engines', type=int, default=4)
    runtime_preflight.add_argument('--timeout', type=int, default=3600)
    runtime_preflight.add_argument('--oms', action='store_true', default=False)
    runtime_preflight.add_argument('--blacklist', action='store_true', default=False)
    runtime_preflight.add_argument('--back-club', action='store_true', default=False)
    runtime_preflight.add_argument(
        '--divid-mode',
        default=config_defaults.divid_mode,
        choices=DIVID_MODE_CHOICES,
    )
    runtime_preflight.add_argument('--one-code', default='')

    # formula subcommand
    formula_parser = sub.add_parser('formula', help='수식 관리')
    formula_sub = formula_parser.add_subparsers(dest='formula_action')

    # formula list
    formula_sub.add_parser('list', help='수식 목록')

    # formula add
    add_p = formula_sub.add_parser('add', help='수식 추가')
    add_p.add_argument('name', help='수식명')
    add_p.add_argument('--code', required=True, help='수식 코드')
    add_p.add_argument('--code-file', help='수식 코드 파일')
    add_p.add_argument('--factor', default='현재가')
    add_p.add_argument('--display-type', default='선:일반')
    add_p.add_argument('--color', default='white')
    add_p.add_argument('--size', type=float, default=1.0)
    add_p.add_argument('--line-type', type=int, default=1)

    # formula test
    test_p = formula_sub.add_parser('test', help='구문 검증')
    test_p.add_argument('code', help='수식 코드')

    # formula delete
    del_p = formula_sub.add_parser('delete', help='수식 삭제')
    del_p.add_argument('name', help='수식명')

    # formula export
    exp_p = formula_sub.add_parser('export', help='수식 내보내기')
    exp_p.add_argument('--output', '-o', required=True, help='출력 파일')

    # formula import
    imp_p = formula_sub.add_parser('import', help='수식 가져오기')
    imp_p.add_argument('--input', '-i', required=True, dest='input_file', help='입력 파일')

    # strategy subcommand
    stg_parser = sub.add_parser('strategy', help='전략 관리')
    stg_sub = stg_parser.add_subparsers(dest='strategy_action')

    # strategy list
    stg_sub.add_parser('list', help='전략 목록')

    # strategy validate
    val_p = stg_sub.add_parser('validate', help='전략 검증')
    val_p.add_argument('name', help='전략명')
    val_p.add_argument('--type', choices=['buy', 'sell'], required=True)
    val_p.add_argument('--v251-compat', action='store_true')

    # strategy analyze (AST analysis)
    ana_p = stg_sub.add_parser('analyze', help='전략 코드 분석')
    ana_p.add_argument('name', help='전략명')
    ana_p.add_argument('--type', choices=['buy', 'sell'], required=True)

    # discovery subcommand
    disc_parser = sub.add_parser('discovery', help='자동 조건식 탐색')
    disc_sub = disc_parser.add_subparsers(dest='discovery_action')

    # discovery analyze
    disc_ana = disc_sub.add_parser('analyze', help='결과 CSV 분석')
    disc_ana.add_argument('--input', '-i', required=True, dest='input_file', help='입력 CSV 파일')
    disc_ana.add_argument('--output', '-o', help='분석 결과 JSON 저장 경로')
    disc_ana.add_argument('--min-samples', type=int, default=30)
    disc_ana.add_argument('--quantiles', type=int, default=10)
    disc_ana.add_argument('--alpha', type=float, default=0.05)

    # discovery ml-analyze
    disc_ml = disc_sub.add_parser('ml-analyze', help='ML 기반 팩터 분석')
    disc_ml.add_argument('--input', '-i', required=True, dest='input_file', help='입력 CSV 파일')
    disc_ml.add_argument('--output', '-o', help='ML 분석 결과 JSON 저장 경로')
    disc_ml.add_argument('--model-type', choices=['random_forest', 'gradient_boosting'], default='random_forest')
    disc_ml.add_argument('--top-n', type=int, default=10)
    disc_ml.add_argument('--n-splits', type=int, default=5)
    disc_ml.add_argument('--random-state', type=int, default=42)

    # discovery generate
    disc_gen = disc_sub.add_parser('generate', help='분석 결과로 조건 코드 생성')
    disc_gen.add_argument('--input', '-i', required=True, dest='input_file', help='입력 CSV 파일')
    disc_gen.add_argument('--output', '-o', help='생성 코드 저장 경로')
    disc_gen.add_argument('--top-n', type=int, default=5)
    disc_gen.add_argument('--buy-var', default='매수')
    disc_gen.add_argument('--min-samples', type=int, default=30)
    disc_gen.add_argument('--quantiles', type=int, default=10)
    disc_gen.add_argument('--alpha', type=float, default=0.05)
    disc_gen.add_argument('--ml-feature-limit', type=int, default=0, help='ML 상위 feature만 후보 생성에 사용')
    disc_gen.add_argument('--ml-model-type', choices=['random_forest', 'gradient_boosting'], default='random_forest')
    disc_gen.add_argument('--ml-top-n', type=int, default=10)
    disc_gen.add_argument('--ml-n-splits', type=int, default=5)
    disc_gen.add_argument('--ml-weight', type=float, default=0.0, help='ML importance를 candidate ranking에 가중치로 반영')

    # discovery create-strategy
    disc_create = disc_sub.add_parser('create-strategy', help='분석 결과를 strategy.db 전략으로 저장')
    disc_create.add_argument('name', help='저장할 전략명')
    disc_create.add_argument('--input', '-i', required=True, dest='input_file', help='입력 CSV 파일')
    disc_create.add_argument('--output-code', help='생성 코드 저장 경로')
    disc_create.add_argument('--top-n', type=int, default=5)
    disc_create.add_argument('--buy-var', default='매수')
    disc_create.add_argument('--min-samples', type=int, default=30)
    disc_create.add_argument('--quantiles', type=int, default=10)
    disc_create.add_argument('--alpha', type=float, default=0.05)
    disc_create.add_argument('--ml-feature-limit', type=int, default=0, help='ML 상위 feature만 후보 생성에 사용')
    disc_create.add_argument('--ml-model-type', choices=['random_forest', 'gradient_boosting'], default='random_forest')
    disc_create.add_argument('--ml-top-n', type=int, default=10)
    disc_create.add_argument('--ml-n-splits', type=int, default=5)
    disc_create.add_argument('--ml-weight', type=float, default=0.0, help='ML importance를 candidate ranking에 가중치로 반영')

    # discovery research
    disc_research = disc_sub.add_parser('research', help='run one discovery research iteration')
    disc_research.add_argument('name', help='strategy name to create')
    disc_research.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
    disc_research.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
    disc_research.add_argument('--sell', required=True, help='existing sell strategy name')
    disc_research.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
    disc_research.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
    disc_research.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_research.add_argument('--betting', default='1')
    disc_research.add_argument('--avg-time', type=int, default=60)
    disc_research.add_argument('--start-time', type=int, default=90000)
    disc_research.add_argument('--end-time', type=int, default=152800)
    disc_research.add_argument('--engines', type=int, default=4)
    disc_research.add_argument('--top-n', type=int, default=1)
    disc_research.add_argument('--min-samples', type=int, default=30)
    disc_research.add_argument('--quantiles', type=int, default=10)
    disc_research.add_argument('--alpha', type=float, default=0.05)
    candidate_mode = disc_research.add_mutually_exclusive_group()
    candidate_mode.add_argument('--run-candidate', action='store_true', default=False)
    candidate_mode.add_argument('--run-candidates', action='store_true', default=False)
    disc_research.add_argument('--candidate-count', type=int, default=5)
    disc_research.add_argument('--candidate-name-prefix')
    disc_research.add_argument('--cleanup-best-candidate', action='store_true', default=False)
    disc_research.add_argument('--keep-loser-candidates', action='store_true', default=False)
    disc_research.add_argument('--min-estimated-retention', type=float, default=0.4)
    disc_research.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
    disc_research.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
    disc_research.add_argument('--candidate-pool-multiplier', type=int, default=3)
    disc_research.add_argument('--candidate-start', type=int)
    disc_research.add_argument('--candidate-end', type=int)
    disc_research.add_argument('--candidate-timeout', type=int)
    disc_research.add_argument('--candidate-plan-only', action='store_true', default=False)
    disc_research.add_argument('--keep-failed-candidate', action='store_true', default=False)

    # discovery promote
    disc_promote = disc_sub.add_parser('promote', help='WFO 통과 전략만 최종 채택')
    disc_promote.add_argument('name', help='최종 전략명')
    disc_promote.add_argument('--input', '-i', required=True, dest='input_file', help='입력 CSV 파일')
    disc_promote.add_argument('--sell', required=True, help='기준 매도 전략명')
    disc_promote.add_argument('--start', type=int, required=True, help='시작일자 YYYYMMDD')
    disc_promote.add_argument('--end', type=int, required=True, help='종료일자 YYYYMMDD')
    disc_promote.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_promote.add_argument('--betting', default='1')
    disc_promote.add_argument('--avg-time', type=int, default=60)
    disc_promote.add_argument('--start-time', type=int, default=90000)
    disc_promote.add_argument('--end-time', type=int, default=152800)
    disc_promote.add_argument('--engines', type=int, default=4)
    disc_promote.add_argument('--top-n', type=int, default=5)
    disc_promote.add_argument('--buy-var', default='매수')
    disc_promote.add_argument('--min-samples', type=int, default=30)
    disc_promote.add_argument('--quantiles', type=int, default=10)
    disc_promote.add_argument('--alpha', type=float, default=0.05)
    disc_promote.add_argument('--output-code', help='생성 코드 저장 경로')
    disc_promote.add_argument('--train-window-days', type=int, required=True)
    disc_promote.add_argument('--test-window-days', type=int, required=True)
    disc_promote.add_argument('--step-days', type=int)
    disc_promote.add_argument('--purge-days', type=int, default=0)
    disc_promote.add_argument('--embargo-days', type=int, default=0)
    disc_promote.add_argument('--objective', default='tpi')
    disc_promote.add_argument('--method', choices=['grid', 'random'], default='grid')
    disc_promote.add_argument('--max-iter', type=int, default=10)
    disc_promote.add_argument('--param-space-json', help='파라미터 스페이스 JSON 문자열')
    disc_promote.add_argument('--param-space-file', help='파라미터 스페이스 JSON 파일')
    disc_promote.add_argument('--promote-min-rounds', type=int, default=1)
    disc_promote.add_argument('--promote-min-success-rate', type=float, default=0.6)
    disc_promote.add_argument('--promote-min-mean-oos', type=float, default=0.0)
    disc_promote.add_argument('--promote-min-avg-trade-count', type=float, default=0.0)
    disc_promote.add_argument('--promotion-preset', choices=['conservative', 'balanced', 'aggressive'], default='balanced')
    disc_promote.add_argument('--report-json', help='채택/탈락 결과 JSON 리포트 저장 경로')
    disc_promote.add_argument('--report-md', help='채택/탈락 결과 Markdown 리포트 저장 경로')
    disc_promote.add_argument('--ml-feature-limit', type=int, default=0, help='ML 상위 feature만 후보 생성에 사용')
    disc_promote.add_argument('--ml-model-type', choices=['random_forest', 'gradient_boosting'], default='random_forest')
    disc_promote.add_argument('--ml-top-n', type=int, default=10)
    disc_promote.add_argument('--ml-n-splits', type=int, default=5)
    disc_promote.add_argument('--ml-weight', type=float, default=0.0, help='ML importance를 candidate ranking에 가중치로 반영')
    disc_promote.add_argument('--auto-relax', action='store_true', default=False,
                              help='무거래 시 top_n을 자동 완화하며 재시도 (preset 기준 사용, --promote-min-* 무시)')
    disc_promote.add_argument('--max-relax-steps', type=int, default=3, help='auto-relax 최대 완화 단계 수 (기본 3)')
    disc_promote.add_argument('--base-buy-strategy', default=None,
                              help='기존 매수 전략명 - 자동 필터를 이 전략에 결합하여 검증')

    # discovery auto
    disc_auto = disc_sub.add_parser('auto', help='DB 전략명으로 전체 파이프라인 원커맨드 실행')
    disc_auto.add_argument('--input', '-i', dest='input_file', help='기존 CSV 파일 경로 (지정 시 Phase A 백테스트 스킵)')
    disc_auto.add_argument('--buy', help='매수 전략명 (--input 미지정 시 필수)')
    disc_auto.add_argument('--sell', required=True, help='매도 전략명')
    disc_auto.add_argument('--start', type=int, required=True, help='시작일자 YYYYMMDD')
    disc_auto.add_argument('--end', type=int, required=True, help='종료일자 YYYYMMDD')
    disc_auto.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_auto.add_argument('--betting', default='1')
    disc_auto.add_argument('--avg-time', type=int, default=60)
    disc_auto.add_argument('--start-time', type=int, default=90000)
    disc_auto.add_argument('--end-time', type=int, default=152800)
    disc_auto.add_argument('--engines', type=int, default=4)
    disc_auto.add_argument('--timeout', type=int, default=3600)
    disc_auto.add_argument('--top-n', type=int, default=5)
    disc_auto.add_argument('--min-samples', type=int, default=30)
    disc_auto.add_argument('--quantiles', type=int, default=10)
    disc_auto.add_argument('--alpha', type=float, default=0.05)
    disc_auto.add_argument('--buy-var', default='매수')
    disc_auto.add_argument('--ml-feature-limit', type=int, default=0)
    disc_auto.add_argument('--ml-model-type', choices=['random_forest', 'gradient_boosting'], default='random_forest')
    disc_auto.add_argument('--ml-top-n', type=int, default=10)
    disc_auto.add_argument('--ml-n-splits', type=int, default=5)
    disc_auto.add_argument('--ml-weight', type=float, default=0.0)
    disc_auto.add_argument('--max-rounds', type=int, default=3, help='분석 다단계 재시도 최대 횟수')
    disc_auto.add_argument('--train-window-days', type=int, required=True)
    disc_auto.add_argument('--test-window-days', type=int, required=True)
    disc_auto.add_argument('--step-days', type=int)
    disc_auto.add_argument('--purge-days', type=int, default=0)
    disc_auto.add_argument('--embargo-days', type=int, default=0)
    disc_auto.add_argument('--objective', default='tpi')
    disc_auto.add_argument('--promotion-preset', choices=['conservative', 'balanced', 'aggressive'], default='balanced')
    disc_auto.add_argument('--auto-relax', action='store_true', default=False)
    disc_auto.add_argument('--max-relax-steps', type=int, default=3)
    disc_auto.add_argument('--base-buy-strategy', default=None)
    disc_auto.add_argument('--output-code', help='생성 코드 저장 경로')
    disc_auto.add_argument('--report-json', help='결과 JSON 리포트 저장 경로')
    disc_auto.add_argument('--report-md', help='결과 Markdown 리포트 저장 경로')

    # discovery batch
    disc_batch = disc_sub.add_parser('batch', help='배치 설정 JSON으로 여러 auto-discovery 순차 실행')
    disc_batch.add_argument('--config', '-c', required=True, dest='batch_config', help='배치 설정 JSON 파일 경로')
    disc_batch.add_argument('--parallel', '-p', type=int, default=0,
                             help='병렬 실행 수 (0=순차, 1+=병렬)')

    # discovery history
    disc_history = disc_sub.add_parser('history', help='auto-discovery 실행 히스토리 조회')
    disc_history.add_argument('--promoted-only', action='store_true', default=False,
                               help='승격된 결과만 표시')
    disc_history.add_argument('--limit', type=int, default=20, help='최대 표시 행 수')
    disc_history.add_argument('--json', action='store_true', default=False, dest='json_output',
                               help='JSON 형식으로 출력')

    # discovery evolve
    disc_evolve = disc_sub.add_parser('evolve', help='조건식 진화 루프 - 승격될 때까지 파라미터 자동 변이')
    disc_evolve.add_argument('--config', '-c', required=True, dest='evolve_config',
                              help='기본 auto-discovery 설정 JSON 파일 경로')
    disc_evolve.add_argument('--max-generations', type=int, default=5, help='최대 세대 수')
    disc_evolve.add_argument('--population-size', type=int, default=4, help='세대당 변이 개체 수')
    disc_evolve.add_argument('--objective', default='tpi', help='최적화 목표 지표')
    disc_evolve.add_argument('--stagnation-limit', type=int, default=2, help='개선 없는 세대 허용 수')
    disc_evolve.add_argument('--mutation-strength', type=float, default=0.3, help='변이 강도 (0.0~1.0)')
    disc_evolve.add_argument('--parallel', '-p', type=int, default=0, help='병렬 실행 수')
    disc_evolve.add_argument('--seed', type=int, default=None, help='랜덤 시드')

    # discovery compare
    disc_compare = disc_sub.add_parser('compare', help='discovery run 비교')
    disc_compare.add_argument('--ids', required=True, help='비교할 discovery_id (쉼표 구분)')
    disc_compare.add_argument('--json', action='store_true', default=False, dest='json_output',
                               help='JSON 형식으로 출력')

    # --- optimize 서브커맨드 ---
    opt_parser = sub.add_parser('optimize', help='파라미터 최적화 (Grid/Random)')
    opt_parser.add_argument('--buy', required=True, help='매수 전략명')
    opt_parser.add_argument('--sell', required=True, help='매도 전략명')
    opt_parser.add_argument('--start', type=int, required=True, help='시작일자 YYYYMMDD')
    opt_parser.add_argument('--end', type=int, required=True, help='종료일자 YYYYMMDD')
    opt_parser.add_argument('--param-space', required=True, dest='param_space_file',
                             help='파라미터 탐색 공간 JSON 파일 경로')
    opt_parser.add_argument('--method', choices=['grid', 'random'], default='grid',
                             help='최적화 방법 (default: grid)')
    opt_parser.add_argument('--objective', default='tpi', help='최적화 목표 지표')
    opt_parser.add_argument('--maximize', action='store_true', default=True)
    opt_parser.add_argument('--no-maximize', action='store_false', dest='maximize')
    opt_parser.add_argument('--max-iter', type=int, default=100, help='Random 최대 반복')
    opt_parser.add_argument('--seed', type=int, default=None, help='랜덤 시드')
    opt_parser.add_argument('--engines', type=int, default=4)
    opt_parser.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    opt_parser.add_argument('--betting', default='1')
    opt_parser.add_argument('--avg-time', type=int, default=60)
    opt_parser.add_argument('--start-time', type=int, default=90000)
    opt_parser.add_argument('--end-time', type=int, default=152800)
    opt_parser.add_argument('--timeout', type=int, default=3600)
    opt_parser.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
    opt_parser.add_argument('-o', '--output', dest='output_file')

    # --- sweep 서브커맨드 ---
    sweep_parser = sub.add_parser('sweep', help='파라미터 스윕 및 날짜 롤링')
    sweep_sub = sweep_parser.add_subparsers(dest='sweep_action')

    sweep_param = sweep_sub.add_parser('param', help='파라미터 조합 스윕')
    sweep_param.add_argument('--buy', help='매수 전략명 (--dry-run 시 불필요)')
    sweep_param.add_argument('--sell', help='매도 전략명 (--dry-run 시 불필요)')
    sweep_param.add_argument('--start', type=int, required=True)
    sweep_param.add_argument('--end', type=int, required=True)
    sweep_param.add_argument('--params', required=True, dest='sweep_params_file',
                              help='스윕 파라미터 JSON 파일')
    sweep_param.add_argument('--engines', type=int, default=4)
    sweep_param.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    sweep_param.add_argument('--betting', default='1')
    sweep_param.add_argument('--avg-time', type=int, default=60)
    sweep_param.add_argument('--start-time', type=int, default=90000)
    sweep_param.add_argument('--end-time', type=int, default=152800)
    sweep_param.add_argument('--timeout', type=int, default=3600)
    sweep_param.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
    sweep_param.add_argument('-o', '--output', dest='output_file')
    sweep_param.add_argument('--dry-run', action='store_true',
                              help='파라미터 조합 목록만 출력하고 실행하지 않음')

    sweep_rolling = sweep_sub.add_parser('rolling', help='날짜 롤링 (고정 윈도우 이동)')
    sweep_rolling.add_argument('--buy', help='매수 전략명 (--dry-run 시 불필요)')
    sweep_rolling.add_argument('--sell', help='매도 전략명 (--dry-run 시 불필요)')
    sweep_rolling.add_argument('--start', type=int, required=True, help='전체 시작일')
    sweep_rolling.add_argument('--end', type=int, required=True, help='전체 종료일')
    sweep_rolling.add_argument('--window-days', type=int, required=True, help='윈도우 크기 (일)')
    sweep_rolling.add_argument('--step-days', type=int, required=True, help='이동 간격 (일)')
    sweep_rolling.add_argument('--engines', type=int, default=4)
    sweep_rolling.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    sweep_rolling.add_argument('--betting', default='1')
    sweep_rolling.add_argument('--avg-time', type=int, default=60)
    sweep_rolling.add_argument('--start-time', type=int, default=90000)
    sweep_rolling.add_argument('--end-time', type=int, default=152800)
    sweep_rolling.add_argument('--timeout', type=int, default=3600)
    sweep_rolling.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
    sweep_rolling.add_argument('-o', '--output', dest='output_file')
    sweep_rolling.add_argument('--dry-run', action='store_true',
                                help='윈도우 목록만 출력하고 실행하지 않음')

    # --- wfo 서브커맨드 ---
    wfo_parser = sub.add_parser('wfo', help='Walk-Forward Optimization 검증')
    wfo_parser.add_argument('--start', type=int, required=True)
    wfo_parser.add_argument('--end', type=int, required=True)
    wfo_parser.add_argument('--train-window-days', type=int, required=True, help='훈련 윈도우 크기 (일)')
    wfo_parser.add_argument('--test-window-days', type=int, required=True, help='테스트 윈도우 크기 (일)')
    wfo_parser.add_argument('--buy', help='매수 전략명 (--dry-run 시 불필요)')
    wfo_parser.add_argument('--sell', help='매도 전략명 (--dry-run 시 불필요)')
    wfo_parser.add_argument('--step-days', type=int, default=None,
                             help='윈도우 이동 간격 (미지정 시 test-window-days)')
    wfo_parser.add_argument('--purge-days', type=int, default=0, help='train-test 사이 퍼지 기간')
    wfo_parser.add_argument('--embargo-days', type=int, default=0, help='test 후 엠바고 기간')
    wfo_parser.add_argument('--param-space', dest='param_space_file', default=None,
                             help='최적화 파라미터 공간 JSON (미지정 시 고정 파라미터)')
    wfo_parser.add_argument('--objective', default='tpi')
    wfo_parser.add_argument('--method', choices=['grid', 'random'], default='grid')
    wfo_parser.add_argument('--maximize', action='store_true', default=True)
    wfo_parser.add_argument('--max-iter', type=int, default=100)
    wfo_parser.add_argument('--engines', type=int, default=4)
    wfo_parser.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    wfo_parser.add_argument('--betting', default='1')
    wfo_parser.add_argument('--avg-time', type=int, default=60)
    wfo_parser.add_argument('--start-time', type=int, default=90000)
    wfo_parser.add_argument('--end-time', type=int, default=152800)
    wfo_parser.add_argument('--timeout', type=int, default=3600)
    wfo_parser.add_argument('--format', choices=['json', 'text'], default='json', dest='output_format')
    wfo_parser.add_argument('-o', '--output', dest='output_file')
    wfo_parser.add_argument('--dry-run', action='store_true',
                             help='train/test 윈도우 목록만 출력')

    # --- setting 서브커맨드 ---
    setting_parser = sub.add_parser('setting', help='STOM 설정 조회 (read-only)')
    setting_sub = setting_parser.add_subparsers(dest='setting_action')

    setting_list = setting_sub.add_parser('list', help='전체 설정 키-값 목록')
    setting_list.add_argument('--format', choices=['json', 'text'], default='text',
                               dest='output_format')

    setting_get = setting_sub.add_parser('get', help='특정 설정 값 조회')
    setting_get.add_argument('key', help='설정 키 이름')
    setting_get.add_argument('--format', choices=['json', 'text'], default='text',
                              dest='output_format')

    setting_search = setting_sub.add_parser('search', help='설정 키 검색 (부분 일치)')
    setting_search.add_argument('query', help='검색어')
    setting_search.add_argument('--format', choices=['json', 'text'], default='text',
                                 dest='output_format')

    # --- report 서브커맨드 ---
    report_parser = sub.add_parser('report', help='백테스트/Discovery 결과 리포트 생성')
    report_parser.add_argument('--source', required=True,
                                choices=['backtest', 'discovery'],
                                help='데이터 소스')
    report_parser.add_argument('--limit', type=int, default=0,
                                help='최근 N건 제한 (0=전체)')
    report_parser.add_argument('--summary', action='store_true',
                                help='요약 통계만 출력')
    report_parser.add_argument('--format', choices=['json', 'csv', 'excel', 'text'],
                                default='json', dest='output_format')
    report_parser.add_argument('-o', '--output', dest='output_file',
                                help='출력 파일 (csv/excel 시 필수)')

    # --- tune 서브커맨드 ---
    tune_parser = sub.add_parser('tune', help='시스템 리소스 분석 및 엔진 수 추천')
    tune_parser.add_argument('--engines', type=int, default=None,
                              help='확인할 엔진 수 (미지정 시 자동 추천)')
    tune_parser.add_argument('--total-codes', type=int, default=0,
                              help='백테스트 대상 종목 수 (추천 정밀도 향상)')
    tune_parser.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    tune_parser.add_argument('--format', choices=['json', 'text'], default='text',
                              dest='output_format')

    # --- db 서브커맨드 ---
    db_parser = sub.add_parser('db', help='데이터베이스 상태 확인 및 유틸리티')
    db_sub = db_parser.add_subparsers(dest='db_action')

    db_check = db_sub.add_parser('check', help='DB 파일 상태 확인')
    db_check.add_argument('--format', choices=['json', 'text'], default='text',
                           dest='output_format')

    db_ensure = db_sub.add_parser('ensure', help='필수 DB 존재 확인 및 자동 복구')
    db_ensure.add_argument('--timeframe', choices=['tick', 'min'], default='tick')

    db_restore = db_sub.add_parser('restore', help='빈 DB 파일 복원 (심볼릭 링크 제거)')
    db_restore.add_argument('--target', required=True,
                             choices=['tick', 'min'],
                             help='복원할 DB 종류')

    return parser


def handle_subcommand(args=None):
    """서브커맨드를 처리한다. Returns exit code."""
    parser = create_subcommand_parser()
    parsed = parser.parse_args(args)

    if parsed.command == 'formula':
        return _handle_formula(parsed)
    elif parsed.command == 'strategy':
        return _handle_strategy(parsed)
    elif parsed.command == 'discovery':
        return _handle_discovery(parsed)
    elif parsed.command == 'optimize':
        return _handle_optimize(parsed)
    elif parsed.command == 'sweep':
        return _handle_sweep(parsed)
    elif parsed.command == 'wfo':
        return _handle_wfo(parsed)
    elif parsed.command == 'setting':
        return _handle_setting(parsed)
    elif parsed.command == 'report':
        return _handle_report(parsed)
    elif parsed.command == 'tune':
        return _handle_tune(parsed)
    elif parsed.command == 'db':
        return _handle_db(parsed)
    elif parsed.command == 'runtime-preflight':
        return _handle_runtime_preflight(parsed)
    else:
        parser.print_help()
        return 0


def _handle_runtime_preflight(parsed):
    from cli.config import BacktestConfig
    from cli import runtime_preflight

    config = BacktestConfig(
        buy_strategy=parsed.buy,
        sell_strategy=parsed.sell,
        start_date=parsed.start,
        end_date=parsed.end,
        betting=parsed.betting,
        avg_time=_normalize_avg_time(parsed.avg_time),
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        engine_count=parsed.engines,
        is_tick=parsed.timeframe == 'tick',
        oms=parsed.oms,
        blacklist=parsed.blacklist,
        back_club=parsed.back_club,
        divid_mode=parsed.divid_mode,
        one_code=parsed.one_code,
        timeout=parsed.timeout,
    )
    result = runtime_preflight.run_runtime_preflight(config)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get('status') == 'ok' else 1


def _normalize_avg_time(avg_time):
    avg_time_parts = [int(x.strip()) for x in str(avg_time).split(',') if x.strip()]
    return avg_time_parts[0] if len(avg_time_parts) == 1 else avg_time_parts


def _handle_formula(parsed):
    from cli.formula import list_formulas, add_formula, test_formula, delete_formula

    if parsed.formula_action == 'list':
        formulas = list_formulas(DB_STRATEGY)
        print(json.dumps(formulas, ensure_ascii=False, indent=2))
        return 0

    elif parsed.formula_action == 'add':
        code = parsed.code
        if parsed.code_file:
            with open(parsed.code_file, 'r', encoding='utf-8') as f:
                code = f.read()
        result = add_formula(
            DB_STRATEGY, parsed.name, code,
            factor=parsed.factor,
            display_type=parsed.display_type,
            color=parsed.color,
            size=parsed.size,
            line_type=parsed.line_type,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'ok' else 1

    elif parsed.formula_action == 'test':
        result = test_formula(parsed.code)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'ok' else 1

    elif parsed.formula_action == 'delete':
        result = delete_formula(DB_STRATEGY, parsed.name)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'ok' else 1

    elif parsed.formula_action == 'export':
        formulas = list_formulas(DB_STRATEGY)
        with open(parsed.output, 'w', encoding='utf-8') as f:
            json.dump(formulas, f, ensure_ascii=False, indent=2)
        print(json.dumps(
            {'status': 'ok', 'count': len(formulas), 'path': parsed.output},
            ensure_ascii=False,
        ))
        return 0

    elif parsed.formula_action == 'import':
        with open(parsed.input_file, 'r', encoding='utf-8') as f:
            formulas = json.load(f)
        count = 0
        failed = []
        for fm in formulas:
            result = add_formula(
                DB_STRATEGY, fm['name'], fm['code'],
                factor=fm.get('factor', '현재가'),
                display_type=fm.get('display_type', '선:일반'),
                color=fm.get('color', 'white'),
                size=fm.get('size', 1.0),
                line_type=fm.get('line_type', 1),
            )
            if result['status'] == 'ok':
                count += 1
            else:
                failed.append({
                    'name': fm.get('name', ''),
                    'message': result.get('message', 'unknown error'),
                })
        status = 'ok' if not failed else 'partial'
        print(json.dumps({'status': status, 'imported': count, 'failed': failed}, ensure_ascii=False))
        return 0 if not failed else 1

    return 1


def _handle_strategy(parsed):
    from cli.strategy import evaluate_strategy, validate_strategy
    from cli.strategy_loader import load_strategy_from_db
    from cli.config import list_strategies

    if parsed.strategy_action == 'list':
        try:
            stgs = list_strategies()
        except Exception as e:
            print(json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False))
            return 1
        print(json.dumps(stgs, ensure_ascii=False, indent=2))
        return 0

    elif parsed.strategy_action == 'validate':
        result = evaluate_strategy(DB_STRATEGY, parsed.name, parsed.type)
        if result['status'] != 'ok':
            print(json.dumps(result, ensure_ascii=False))
            return 1
        val_result = validate_strategy(result['code'], v251_compat=parsed.v251_compat)
        val_result['strategy_name'] = parsed.name
        val_result['strategy_type'] = parsed.type
        print(json.dumps(val_result, ensure_ascii=False, indent=2))
        return 0 if val_result['status'] == 'ok' else 1

    elif parsed.strategy_action == 'analyze':
        result = load_strategy_from_db(DB_STRATEGY, parsed.name, parsed.type)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'ok' else 1

    return 1


def _load_param_space(parsed):
    if getattr(parsed, 'param_space_json', None):
        return json.loads(parsed.param_space_json)
    if getattr(parsed, 'param_space_file', None):
        with open(parsed.param_space_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _handle_discovery(parsed):
    from cli.ai_controller import AIBacktestController

    controller = AIBacktestController()

    if parsed.discovery_action == 'analyze':
        result = controller.analyze_results(
            parsed.input_file,
            min_samples=parsed.min_samples,
            quantiles=parsed.quantiles,
            alpha=parsed.alpha,
            output_path=parsed.output,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'ml-analyze':
        result = controller.analyze_results_ml(
            parsed.input_file,
            model_type=parsed.model_type,
            top_n=parsed.top_n,
            n_splits=parsed.n_splits,
            random_state=parsed.random_state,
            output_path=parsed.output,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'generate':
        result = controller.generate_conditions(
            input_path=parsed.input_file,
            top_n=parsed.top_n,
            buy_var=parsed.buy_var,
            output_path=parsed.output,
            min_samples=parsed.min_samples,
            quantiles=parsed.quantiles,
            alpha=parsed.alpha,
            ml_feature_limit=parsed.ml_feature_limit,
            ml_model_type=parsed.ml_model_type,
            ml_top_n=parsed.ml_top_n,
            ml_n_splits=parsed.ml_n_splits,
            ml_weight=parsed.ml_weight,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'create-strategy':
        result = controller.create_strategy_from_analysis(
            parsed.name,
            input_path=parsed.input_file,
            top_n=parsed.top_n,
            buy_var=parsed.buy_var,
            min_samples=parsed.min_samples,
            quantiles=parsed.quantiles,
            alpha=parsed.alpha,
            output_code_path=parsed.output_code,
            ml_feature_limit=parsed.ml_feature_limit,
            ml_model_type=parsed.ml_model_type,
            ml_top_n=parsed.ml_top_n,
            ml_n_splits=parsed.ml_n_splits,
            ml_weight=parsed.ml_weight,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'research':
        result = controller.research_strategy_once({
            'name': parsed.name,
            'baseline_csv': getattr(parsed, 'input_file', None),
            'base_buy_strategy': parsed.base_buy_strategy,
            'sell_strategy': parsed.sell,
            'start_date': parsed.start,
            'end_date': parsed.end,
            'is_tick': parsed.timeframe == 'tick',
            'betting': parsed.betting,
            'avg_time': parsed.avg_time,
            'start_time': parsed.start_time,
            'end_time': parsed.end_time,
            'engine_count': parsed.engines,
            'top_n': parsed.top_n,
            'min_samples': parsed.min_samples,
            'quantiles': parsed.quantiles,
            'alpha': parsed.alpha,
            'run_candidate': parsed.run_candidate,
            'run_candidates': parsed.run_candidates,
            'candidate_count': parsed.candidate_count,
            'candidate_name_prefix': parsed.candidate_name_prefix,
            'cleanup_best_candidate': parsed.cleanup_best_candidate,
            'keep_loser_candidates': parsed.keep_loser_candidates,
            'min_estimated_retention': parsed.min_estimated_retention,
            'allow_retention_fallback': parsed.allow_retention_fallback,
            'use_retention_penalty': parsed.use_retention_penalty,
            'candidate_pool_multiplier': parsed.candidate_pool_multiplier,
            'candidate_start_date': parsed.candidate_start,
            'candidate_end_date': parsed.candidate_end,
            'candidate_timeout': parsed.candidate_timeout,
            'candidate_plan_only': parsed.candidate_plan_only,
            'keep_failed_candidate': parsed.keep_failed_candidate,
        })
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'history':
        result = controller.get_discovery_history(
            limit=parsed.limit, promoted_only=parsed.promoted_only,
        )
        if parsed.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        else:
            from cli.table_formatter import format_table
            runs = result.get('runs', [])
            if not runs:
                print('(no discovery runs)')
            else:
                columns = [
                    ('discovery_id', 'ID', 4),
                    ('timestamp', 'Timestamp', 20),
                    ('buy_strategy', 'Buy Strategy', 12),
                    ('status', 'Status', 6),
                    ('promoted', 'Promoted', 8),
                    ('strategy_name', 'Strategy Name', 12),
                    ('pipeline_duration', 'Duration(s)', 10),
                ]
                print(format_table(runs, columns))
                print(f"\nTotal: {result.get('total', len(runs))} runs")
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'compare':
        ids = [int(x.strip()) for x in parsed.ids.split(',') if x.strip()]
        result = controller.compare_discovery_history(ids)
        if parsed.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        else:
            from cli.table_formatter import format_table
            runs = result.get('runs', [])
            if not runs:
                print('(no matching discovery runs)')
            else:
                columns = [
                    ('discovery_id', 'ID', 4),
                    ('buy_strategy', 'Buy Strategy', 12),
                    ('promoted', 'Promoted', 8),
                    ('pipeline_duration', 'Duration(s)', 10),
                    ('phase_a_duration', 'Phase A(s)', 9),
                    ('phase_b_duration', 'Phase B(s)', 9),
                    ('phase_c_duration', 'Phase C(s)', 9),
                    ('phase_b_rounds', 'B Rounds', 8),
                ]
                print(format_table(runs, columns))
                best = result.get('best', {})
                if best:
                    print('\nBest:')
                    for metric, did in best.items():
                        print(f'  {metric}: discovery_id={did}')
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'batch':
        from cli.auto_discovery import run_batch

        result = run_batch(batch_path=parsed.batch_config,
                           parallel=getattr(parsed, 'parallel', 0))
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.discovery_action == 'auto':
        from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

        if not getattr(parsed, 'input_file', None) and not parsed.buy:
            print(json.dumps({'status': 'error', 'message': '--input 또는 --buy 중 하나는 반드시 지정해야 합니다.'}, ensure_ascii=False))
            return 1

        auto_config = AutoDiscoveryConfig(
            input_csv=getattr(parsed, 'input_file', None),
            buy_strategy=parsed.buy or '',
            sell_strategy=parsed.sell,
            start_date=parsed.start,
            end_date=parsed.end,
            is_tick=parsed.timeframe == 'tick',
            betting=parsed.betting,
            avg_time=parsed.avg_time,
            start_time=parsed.start_time,
            end_time=parsed.end_time,
            engine_count=parsed.engines,
            timeout=parsed.timeout,
            top_n=parsed.top_n,
            min_samples=parsed.min_samples,
            quantiles=parsed.quantiles,
            alpha=parsed.alpha,
            buy_var=parsed.buy_var,
            ml_feature_limit=parsed.ml_feature_limit,
            ml_model_type=parsed.ml_model_type,
            ml_top_n=parsed.ml_top_n,
            ml_n_splits=parsed.ml_n_splits,
            ml_weight=parsed.ml_weight,
            max_rounds=parsed.max_rounds,
            train_window_days=parsed.train_window_days,
            test_window_days=parsed.test_window_days,
            step_days=parsed.step_days,
            purge_days=parsed.purge_days,
            embargo_days=parsed.embargo_days,
            objective=parsed.objective,
            promotion_preset=parsed.promotion_preset,
            auto_relax=parsed.auto_relax,
            max_relax_steps=parsed.max_relax_steps,
            base_buy_strategy=parsed.base_buy_strategy,
            output_code=parsed.output_code,
            report_json=parsed.report_json,
            report_md=parsed.report_md,
        )
        result = AutoDiscoveryEngine.run(auto_config)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('status') == 'ok' and result.get('promoted', False) else 1

    elif parsed.discovery_action == 'promote':
        config_dict = {
            'sell_strategy': parsed.sell,
            'start_date': parsed.start,
            'end_date': parsed.end,
            'is_tick': parsed.timeframe == 'tick',
            'betting': parsed.betting,
            'avg_time': parsed.avg_time,
            'start_time': parsed.start_time,
            'end_time': parsed.end_time,
            'engine_count': parsed.engines,
        }
        if parsed.base_buy_strategy:
            config_dict['base_buy_strategy'] = parsed.base_buy_strategy
        walk_forward_settings = {
            'train_window_days': parsed.train_window_days,
            'test_window_days': parsed.test_window_days,
            'step_days': parsed.step_days,
            'purge_days': parsed.purge_days,
            'embargo_days': parsed.embargo_days,
            'objective': parsed.objective,
            'method': parsed.method,
            'max_iter': parsed.max_iter,
        }
        from cli.discovery_config import (
            DiscoveryAnalysisConfig, DiscoveryConfig, DiscoveryMlConfig,
            DiscoveryOutputConfig, DiscoveryPromotionConfig,
        )
        if parsed.auto_relax:
            promotion_criteria = None
        else:
            promotion_criteria = {
                'min_rounds': parsed.promote_min_rounds,
                'min_success_rate': parsed.promote_min_success_rate,
                'min_mean_oos_metric': parsed.promote_min_mean_oos,
                'min_avg_trade_count': parsed.promote_min_avg_trade_count,
            }
        discovery_config = DiscoveryConfig(
            analysis=DiscoveryAnalysisConfig(
                top_n=parsed.top_n,
                min_samples=parsed.min_samples,
                quantiles=parsed.quantiles,
                alpha=parsed.alpha,
                buy_var=parsed.buy_var,
            ),
            ml=DiscoveryMlConfig(
                feature_limit=parsed.ml_feature_limit,
                model_type=parsed.ml_model_type,
                top_n=parsed.ml_top_n,
                n_splits=parsed.ml_n_splits,
                weight=parsed.ml_weight,
            ),
            promotion=DiscoveryPromotionConfig(
                preset=parsed.promotion_preset,
                criteria=promotion_criteria,
                auto_relax=parsed.auto_relax,
                max_relax_steps=parsed.max_relax_steps,
            ),
            output=DiscoveryOutputConfig(
                code_path=parsed.output_code,
                report_json_path=parsed.report_json,
                report_md_path=parsed.report_md,
            ),
        )
        result = controller.discover_and_promote_strategy(
            parsed.name,
            config_dict=config_dict,
            input_path=parsed.input_file,
            param_space=_load_param_space(parsed),
            walk_forward_settings=walk_forward_settings,
            discovery_config=discovery_config,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' and result.get('promoted', False) else 1

    elif parsed.discovery_action == 'evolve':
        result = controller.auto_discover_evolve(
            config_path=parsed.evolve_config,
            max_generations=parsed.max_generations,
            population_size=parsed.population_size,
            objective=parsed.objective,
            stagnation_limit=parsed.stagnation_limit,
            mutation_strength=parsed.mutation_strength,
            parallel=getattr(parsed, 'parallel', 0),
            seed=getattr(parsed, 'seed', None),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('promoted', False) else 1

    return 1


def _build_base_config_dict(parsed):
    """공통 백테스트 설정을 parsed args에서 추출한다."""
    return {
        'buy_strategy': parsed.buy,
        'sell_strategy': parsed.sell,
        'start_date': parsed.start,
        'end_date': parsed.end,
        'is_tick': getattr(parsed, 'timeframe', 'tick') == 'tick',
        'betting': getattr(parsed, 'betting', '1'),
        'avg_time': getattr(parsed, 'avg_time', 60),
        'start_time': getattr(parsed, 'start_time', 90000),
        'end_time': getattr(parsed, 'end_time', 152800),
        'engine_count': getattr(parsed, 'engines', 4),
        'timeout': getattr(parsed, 'timeout', 3600),
    }


def _write_output(text, output_file=None):
    """stdout 또는 파일로 출력."""
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
    else:
        print(text)


def _handle_optimize(parsed):
    """optimize 서브커맨드 핸들러."""
    try:
        with open(parsed.param_space_file, 'r', encoding='utf-8') as f:
            param_space = json.load(f)
    except FileNotFoundError:
        print(json.dumps({'status': 'error', 'message': '파일을 찾을 수 없습니다: %s' % parsed.param_space_file}, ensure_ascii=False))
        return 1
    except json.JSONDecodeError as e:
        print(json.dumps({'status': 'error', 'message': 'JSON 파싱 오류: %s' % str(e)}, ensure_ascii=False))
        return 1

    if not isinstance(param_space, dict) or not param_space:
        print(json.dumps({'status': 'error', 'message': 'param-space는 비어있지 않은 dict여야 합니다.'}, ensure_ascii=False))
        return 1

    from cli.optimizer import optimize

    base_config = _build_base_config_dict(parsed)
    results = []

    def run_fn(config_dict):
        from cli.runner import run_backtest
        from cli.config import BacktestConfig
        merged = {**base_config}
        merged.update({k: v for k, v in config_dict.items()
                       if k in BacktestConfig.__dataclass_fields__})
        cfg = BacktestConfig(**merged)
        return run_backtest(cfg)

    def save_fn(combo, result):
        results.append({**combo, 'result': result})

    try:
        best = optimize(
            base_config=base_config,
            param_space=param_space,
            objective=parsed.objective,
            method=parsed.method,
            maximize=parsed.maximize,
            max_iter=parsed.max_iter,
            seed=parsed.seed,
            run_fn=run_fn,
            save_fn=save_fn,
        )
    except Exception as e:
        print(json.dumps({'status': 'error', 'message': '최적화 실행 오류: %s' % str(e)}, ensure_ascii=False))
        return 2

    output = {
        'status': 'ok',
        'method': parsed.method,
        'objective': parsed.objective,
        'best': best,
        'total_combinations': len(results),
        'results': results,
    }
    text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
    _write_output(text, getattr(parsed, 'output_file', None))
    return 0


def _handle_sweep(parsed):
    """sweep 서브커맨드 핸들러."""
    if parsed.sweep_action == 'rolling':
        from cli.sweep import generate_rolling_windows

        windows = generate_rolling_windows(
            start_date=parsed.start,
            end_date=parsed.end,
            window_days=parsed.window_days,
            step_days=parsed.step_days,
        )

        if parsed.dry_run:
            output = {
                'status': 'dry-run',
                'window_count': len(windows),
                'windows': windows,
            }
            text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
            _write_output(text, getattr(parsed, 'output_file', None))
            return 0

        if not parsed.buy or not parsed.sell:
            print(json.dumps({'status': 'error', 'message': '--buy와 --sell은 실행 시 필수입니다 (--dry-run이 아닌 경우).'}))
            return 1

        from cli.sweep import run_rolling
        base_config = _build_base_config_dict(parsed)
        try:
            result = run_rolling(base_config, parsed.window_days, parsed.step_days)
        except Exception as e:
            print(json.dumps({'status': 'error', 'message': '롤링 실행 오류: %s' % str(e)}, ensure_ascii=False))
            return 2
        text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        _write_output(text, getattr(parsed, 'output_file', None))
        return 0 if result.get('status') == 'ok' else 1

    elif parsed.sweep_action == 'param':
        try:
            with open(parsed.sweep_params_file, 'r', encoding='utf-8') as f:
                sweep_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False))
            return 1

        from cli.sweep import generate_combinations, run_sweep
        combos = generate_combinations(sweep_params)

        if getattr(parsed, 'dry_run', False):
            output = {
                'status': 'dry-run',
                'total_combinations': len(combos),
                'combinations': combos,
            }
            text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
            _write_output(text, getattr(parsed, 'output_file', None))
            return 0

        if not parsed.buy or not parsed.sell:
            print(json.dumps({'status': 'error', 'message': '--buy와 --sell은 실행 시 필수입니다 (--dry-run이 아닌 경우).'}, ensure_ascii=False))
            return 1

        base_config = _build_base_config_dict(parsed)
        try:
            result = run_sweep(base_config, sweep_params)
        except Exception as e:
            print(json.dumps({'status': 'error', 'message': '스윕 실행 오류: %s' % str(e)}, ensure_ascii=False))
            return 2
        output = {
            'status': 'ok',
            'total_combinations': len(combos),
            'results': result if isinstance(result, list) else [result],
        }
        text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
        _write_output(text, getattr(parsed, 'output_file', None))
        return 0

    else:
        print(json.dumps({'status': 'error', 'message': 'sweep 하위 명령을 지정하세요: param, rolling'}))
        return 1


def _handle_wfo(parsed):
    """wfo 서브커맨드 핸들러."""
    from cli.wfo import generate_walk_forward_windows

    step_days = parsed.step_days if parsed.step_days is not None else parsed.test_window_days

    windows = generate_walk_forward_windows(
        start_date=parsed.start,
        end_date=parsed.end,
        train_window_days=parsed.train_window_days,
        test_window_days=parsed.test_window_days,
        step_days=step_days,
        purge_days=parsed.purge_days,
        embargo_days=parsed.embargo_days,
    )

    if parsed.dry_run:
        output = {
            'status': 'dry-run',
            'train_window_days': parsed.train_window_days,
            'test_window_days': parsed.test_window_days,
            'step_days': step_days,
            'purge_days': parsed.purge_days,
            'embargo_days': parsed.embargo_days,
            'round_count': len(windows),
            'windows': windows,
        }
        text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
        _write_output(text, getattr(parsed, 'output_file', None))
        return 0

    if not parsed.buy or not parsed.sell:
        print(json.dumps({'status': 'error', 'message': '--buy와 --sell은 실행 시 필수입니다 (--dry-run이 아닌 경우).'}))
        return 1

    from cli.wfo import run_walk_forward, save_walk_forward_report

    param_space = {}
    if parsed.param_space_file:
        try:
            with open(parsed.param_space_file, 'r', encoding='utf-8') as f:
                param_space = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(json.dumps({'status': 'error', 'message': str(e)}))
            return 1

    base_config = _build_base_config_dict(parsed)
    try:
        result = run_walk_forward(
            base_config=base_config,
            param_space=param_space,
            train_window_days=parsed.train_window_days,
            test_window_days=parsed.test_window_days,
            step_days=step_days,
            purge_days=parsed.purge_days,
            embargo_days=parsed.embargo_days,
            objective=parsed.objective,
            method=parsed.method,
            maximize=parsed.maximize,
            max_iter=parsed.max_iter,
        )
    except Exception as e:
        print(json.dumps({'status': 'error', 'message': 'WFO 실행 오류: %s' % str(e)}, ensure_ascii=False))
        return 2

    output_file = getattr(parsed, 'output_file', None)
    if output_file:
        if output_file.endswith('.json'):
            save_walk_forward_report(result, output_file)
        else:
            text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
            _write_output(text, output_file)
    else:
        text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        print(text)
    return 0 if result.get('status') == 'ok' else 1


def _handle_setting(parsed):
    """setting 서브커맨드 핸들러 (read-only)."""
    try:
        from utility.setting import DICT_SET
    except (Exception, SystemExit) as e:
        error_msg = str(e)
        if isinstance(e, SystemExit) or 'InvalidToken' in type(e).__name__ or '암호키' in error_msg:
            print(json.dumps({
                'status': 'error',
                'message': 'setting.db 암호키 불일치. STOM_ALLOW_MINIMAL_SETTING=1 환경변수를 설정하세요.',
            }, ensure_ascii=False))
        else:
            print(json.dumps({
                'status': 'error',
                'message': 'DICT_SET 로드 실패: %s' % error_msg,
            }, ensure_ascii=False))
        return 1

    if parsed.setting_action == 'list':
        items = {k: repr(v) for k, v in sorted(DICT_SET.items())}
        if parsed.output_format == 'json':
            print(json.dumps({'status': 'ok', 'count': len(items), 'settings': items}, ensure_ascii=False, indent=2))
        else:
            print('=== STOM Settings (%d keys) ===' % len(items))
            for k, v in sorted(items.items()):
                print('  %-30s = %s' % (k, v))
        return 0

    elif parsed.setting_action == 'get':
        key = parsed.key
        if key not in DICT_SET:
            print(json.dumps({'status': 'error', 'message': '키를 찾을 수 없습니다: %s' % key}, ensure_ascii=False))
            return 1
        value = DICT_SET[key]
        if parsed.output_format == 'json':
            print(json.dumps({'status': 'ok', 'key': key, 'value': repr(value)}, ensure_ascii=False))
        else:
            print('%s = %s' % (key, repr(value)))
        return 0

    elif parsed.setting_action == 'search':
        query = parsed.query.lower()
        matches = {k: repr(v) for k, v in DICT_SET.items() if query in k.lower()}
        if parsed.output_format == 'json':
            print(json.dumps({'status': 'ok', 'query': parsed.query, 'count': len(matches), 'results': matches}, ensure_ascii=False, indent=2))
        else:
            if not matches:
                print('검색 결과 없음: %s' % parsed.query)
            else:
                print('=== Search: "%s" (%d matches) ===' % (parsed.query, len(matches)))
                for k, v in sorted(matches.items()):
                    print('  %-30s = %s' % (k, v))
        return 0

    else:
        print(json.dumps({'status': 'error', 'message': 'setting 하위 명령을 지정하세요: list, get, search'}, ensure_ascii=False))
        return 1


def _handle_report(parsed):
    """report 서브커맨드 핸들러."""
    import sqlite3
    from cli.paths import DB_BACKTEST

    if parsed.source == 'backtest':
        table_name = 'stock_bt'
        try:
            con = sqlite3.connect(DB_BACKTEST)
            # 테이블 존재 여부 확인
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if table_name not in tables:
                con.close()
                print(json.dumps({
                    'status': 'error',
                    'message': "테이블 '%s'가 존재하지 않습니다 (DB: %s). 사용 가능: %s" % (
                        table_name, DB_BACKTEST, ', '.join(tables) or '(없음)'),
                }, ensure_ascii=False))
                return 1
            query = "SELECT * FROM '%s' ORDER BY rowid DESC" % table_name
            if parsed.limit > 0:
                query += " LIMIT %d" % parsed.limit
            import pandas as pd
            df = pd.read_sql_query(query, con)
            con.close()
        except Exception as e:
            print(json.dumps({'status': 'error', 'message': 'DB 조회 실패 (%s): %s' % (DB_BACKTEST, str(e))}, ensure_ascii=False))
            return 1

        if parsed.summary:
            from cli.report import summary_stats
            stats = summary_stats(df)
            stats['status'] = 'ok'
            stats['row_count'] = len(df)
            print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))
            return 0

        if parsed.output_format == 'csv':
            if not parsed.output_file:
                print(json.dumps({'status': 'error', 'message': '--format csv 시 -o 파일 경로 필수'}, ensure_ascii=False))
                return 1
            from cli.report import save_csv
            result = save_csv(df, parsed.output_file)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result['status'] == 'ok' else 1

        elif parsed.output_format == 'excel':
            if not parsed.output_file:
                print(json.dumps({'status': 'error', 'message': '--format excel 시 -o 파일 경로 필수'}, ensure_ascii=False))
                return 1
            from cli.report import save_excel
            result = save_excel(df, parsed.output_file)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result['status'] == 'ok' else 1

        else:
            # json or text
            records = df.to_dict(orient='records')
            output = {'status': 'ok', 'row_count': len(records), 'data': records}
            print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
            return 0

    elif parsed.source == 'discovery':
        from cli.ai_controller import AIBacktestController
        controller = AIBacktestController()
        result = controller.get_discovery_history(
            limit=parsed.limit if parsed.limit > 0 else 100,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get('status') == 'ok' else 1

    return 1


def _handle_tune(parsed):
    """tune 서브커맨드 핸들러."""
    from cli.engine_tuner import (
        get_system_info, recommend_engine_count,
        estimate_memory_per_engine, check_resources,
    )

    info = get_system_info()
    rec = recommend_engine_count(total_codes=parsed.total_codes)
    is_tick = parsed.timeframe == 'tick'
    mem_per_engine = estimate_memory_per_engine(is_tick)

    result = {
        'system': info,
        'recommendation': rec,
        'memory_per_engine_mb': mem_per_engine,
        'timeframe': parsed.timeframe,
    }

    if parsed.engines is not None:
        resource_check = check_resources(parsed.engines, is_tick)
        result['resource_check'] = resource_check

    if parsed.output_format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('=== STOM Engine Tuner ===')
        print('CPU: %d cores' % info['cpu_count'])
        print('Memory: %.1f GB (available: %.1f GB)' % (
            info['memory_total_gb'], info['memory_available_gb']))
        print('Platform: %s' % info['platform'])
        print('Timeframe: %s (%.0f MB/engine)' % (parsed.timeframe, mem_per_engine))
        print()
        print('Recommended engines: %d' % rec['recommended'])
        print('Reason: %s' % rec['reason'])
        if parsed.engines is not None:
            rc = result['resource_check']
            print()
            print('Resource check (--engines %d): [%s]' % (parsed.engines, rc['status']))
            print('  %s' % rc['message'])

    return 0


def _handle_db(parsed):
    """db 서브커맨드 핸들러."""
    import os
    from cli.paths import (
        DB_STRATEGY, DB_BACKTEST,
        DB_STOCK_BACK_TICK, DB_STOCK_BACK_MIN, DB_SETTING,
    )
    from cli.data_bridge import check_tick_db, ensure_tick_db, restore_empty_db

    if parsed.db_action == 'check':
        db_files = {
            'setting': DB_SETTING,
            'strategy': DB_STRATEGY,
            'backtest': DB_BACKTEST,
            'stock_tick_back': DB_STOCK_BACK_TICK,
            'stock_min_back': DB_STOCK_BACK_MIN,
        }
        results = {}
        for name, path in db_files.items():
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            results[name] = {
                'path': path,
                'exists': exists,
                'size_bytes': size,
                'size_mb': round(size / (1024 * 1024), 2) if size > 0 else 0,
            }

        # tick DB 상세 진단
        tick_diag = check_tick_db(DB_STOCK_BACK_TICK)
        results['stock_tick_back']['detail'] = tick_diag

        overall_status = 'error' if tick_diag.get('status') == 'error' else 'ok'
        output = {'status': overall_status, 'databases': results}

        if parsed.output_format == 'json':
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print('=== STOM Database Status ===')
            for name, info in results.items():
                if name == 'stock_tick_back' and info.get('detail', {}).get('status') == 'error':
                    status = 'ERROR'
                else:
                    status = 'OK' if info['exists'] else 'MISSING'
                print('  %-20s %s  %8.2f MB  %s' % (
                    name, status, info['size_mb'], info['path']))
                if name == 'stock_tick_back' and info.get('detail', {}).get('status') == 'error':
                    print('  %-20s %s' % ('', info['detail']['message']))
        return 0 if overall_status == 'ok' else 1

    elif parsed.db_action == 'ensure':
        db_path = DB_STOCK_BACK_TICK if parsed.timeframe == 'tick' else DB_STOCK_BACK_MIN
        result = ensure_tick_db(db_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] != 'error' else 1

    elif parsed.db_action == 'restore':
        db_path = DB_STOCK_BACK_TICK if parsed.target == 'tick' else DB_STOCK_BACK_MIN
        result = restore_empty_db(db_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'ok' else 1

    else:
        print(json.dumps({'status': 'error', 'message': 'db 하위 명령을 지정하세요: check, ensure, restore'}))
        return 1
