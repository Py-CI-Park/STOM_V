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

    return parser


def handle_subcommand(args=None):
    """서브커맨드를 처리한다. Returns exit code."""
    parser = create_subcommand_parser()
    parsed = parser.parse_args(args)

    if parsed.command == 'formula':
        return _handle_formula(parsed)
    elif parsed.command == 'strategy':
        return _handle_strategy(parsed)
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
