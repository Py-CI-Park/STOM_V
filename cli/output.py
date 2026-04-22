
import json
from datetime import datetime


def format_result(result, fmt='json'):
    if fmt == 'json':
        return format_json(result)
    else:
        return format_text(result)


def format_json(result):
    if result.get('status') == 'error':
        output = {
            'status': 'error',
            'message': result.get('message', 'Unknown error'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        if result.get('backtest_child_diagnostics') is not None:
            output['backtest_child_diagnostics'] = result['backtest_child_diagnostics']
    else:
        metrics = result.get('metrics') or {}
        config = result.get('config') or {}
        output = {
            'status': 'success',
            'metrics': {
                'trade_count': metrics.get('trade_count', 0),
                'win_rate': metrics.get('win_rate', 0.0),
                'avg_profit_pct': metrics.get('avg_profit_pct', 0.0),
                'total_profit_pct': metrics.get('total_profit_pct', 0.0),
                'total_profit_krw': metrics.get('total_profit_krw', 0),
                'cagr': metrics.get('cagr', 0.0),
                'mdd_pct': metrics.get('mdd_pct', 0.0),
                'mdd_amount': metrics.get('mdd_amount', 0.0),
                'tpi': metrics.get('tpi', 0.0),
                'seed_capital': metrics.get('seed_capital', 0.0),
                'max_hold_count': metrics.get('max_hold_count', 0),
                'avg_hold_time': metrics.get('avg_hold_time', 0.0),
                'day_count': metrics.get('day_count', 0),
            },
            'bootstrap': {
                'avg_return': metrics.get('bootstrap_avg', 0.0),
                'ci_lower': metrics.get('bootstrap_min', 0.0),
                'ci_upper': metrics.get('bootstrap_max', 0.0),
            },
            'config': {
                'buy_strategy': config.get('buy_strategy', ''),
                'sell_strategy': config.get('sell_strategy', ''),
                'start_date': config.get('start_date', ''),
                'end_date': config.get('end_date', ''),
            },
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    return json.dumps(output, ensure_ascii=False, indent=2)


def format_text(result):
    if result.get('status') == 'error':
        return f"ERROR: {result.get('message', 'Unknown error')}"

    metrics = result.get('metrics') or {}
    lines = [
        '=' * 50,
        'STOM Backtest Result',
        '=' * 50,
        f"  매매횟수:       {metrics.get('trade_count', 0)}",
        f"  승률:           {metrics.get('win_rate', 0.0):.2f}%",
        f"  평균수익률:     {metrics.get('avg_profit_pct', 0.0):.2f}%",
        f"  총수익률:       {metrics.get('total_profit_pct', 0.0):.2f}%",
        f"  총수익금:       {metrics.get('total_profit_krw', 0):,}원",
        f"  CAGR:           {metrics.get('cagr', 0.0):.2f}%",
        f"  MDD:            {metrics.get('mdd_pct', 0.0):.2f}%",
        f"  TPI:            {metrics.get('tpi', 0.0):.4f}",
        f"  시드:           {metrics.get('seed_capital', 0.0):,.0f}원",
        f"  최대동시보유:   {metrics.get('max_hold_count', 0)}",
        f"  평균보유시간:   {metrics.get('avg_hold_time', 0.0):.1f}",
        f"  거래일수:       {metrics.get('day_count', 0)}",
        '-' * 50,
        f"  Bootstrap 평균: {metrics.get('bootstrap_avg', 0.0):.4f}",
        f"  Bootstrap 하한: {metrics.get('bootstrap_min', 0.0):.4f}",
        f"  Bootstrap 상한: {metrics.get('bootstrap_max', 0.0):.4f}",
        '=' * 50,
    ]
    return '\n'.join(lines)
