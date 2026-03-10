"""서브커맨드 라우터 — formula, strategy 서브커맨드 처리."""
import argparse
import json

from cli.paths import DB_STRATEGY


def create_subcommand_parser():
    """서브커맨드 파서 생성."""
    parser = argparse.ArgumentParser(prog='stom_backtest')
    sub = parser.add_subparsers(dest='command')

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
    else:
        parser.print_help()
        return 0


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
        stgs = list_strategies()
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
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' else 1

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
        promotion_criteria = {
            'min_rounds': parsed.promote_min_rounds,
            'min_success_rate': parsed.promote_min_success_rate,
            'min_mean_oos_metric': parsed.promote_min_mean_oos,
            'min_avg_trade_count': parsed.promote_min_avg_trade_count,
        }
        result = controller.discover_and_promote_strategy(
            parsed.name,
            config_dict=config_dict,
            input_path=parsed.input_file,
            param_space=_load_param_space(parsed),
            top_n=parsed.top_n,
            buy_var=parsed.buy_var,
            min_samples=parsed.min_samples,
            quantiles=parsed.quantiles,
            alpha=parsed.alpha,
            output_code_path=parsed.output_code,
            walk_forward_settings=walk_forward_settings,
            promotion_criteria=promotion_criteria,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'ok' and result.get('promoted', False) else 1

    return 1
