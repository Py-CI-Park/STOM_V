# -*- coding: utf-8 -*-
"""손실 해부 1단계 — 손실이 '어디에·어떤 모양으로' 있는지부터 본다.

자동 탐색 이전에 사람이 읽을 수 있는 사실을 쌓는 것이 목적이다.
질문:
  Q1. 손실은 소수 대형 손실인가, 다수 소액 손실인가?
  Q2. 승/패의 비대칭은 어디서 오는가(승률 vs 손익비)?
  Q3. 보유시간·청산사유별로 손실 구조가 다른가?
  Q4. 같은 종목/같은 날에 반복 진입해서 잃는가?
  Q5. 설계구간과 표본외 구간에서 이 구조가 다른가?
"""
import pandas as pd
import numpy as np
from ai_strategy_loop.autopsy.label_dataset import enrich

D = 'backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731234533.csv'   # 설계 2년
H = 'backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731235145.csv'   # 표본외 23개월
import glob, os
if not os.path.exists(H):
    cands = sorted(glob.glob('backtest/csv/stock_bt_QSP2ANCH_R8C2_B_*.csv'), key=os.path.getmtime)
    H = cands[-1] if cands[-1] != D else cands[-2]

def load(p):
    df = enrich(pd.read_csv(p, encoding='utf-8-sig')).df
    df['_pnl'] = pd.to_numeric(df['수익금'], errors='coerce').fillna(0)
    df['_ret'] = pd.to_numeric(df['수익률'], errors='coerce')
    df['_date'] = df['매수시간'].astype(str).str.slice(0, 8)
    return df

for name, path in (('설계 2년', D), ('표본외', H)):
    df = load(path)
    pnl, ret = df['_pnl'], df['_ret']
    n = len(df)
    print(f'\n{"="*72}\n{name}  ({os.path.basename(path)})  {n:,}건 · {pnl.sum():,.0f}원 · 건당 {pnl.mean():,.0f}')
    print("="*72)

    # Q1 손실 집중도 — 상위 손실 거래가 전체 손실의 몇 %인가.
    losses = pnl[pnl < 0].sort_values()
    tot_loss = losses.sum()
    print(f'\n[Q1] 손실 집중도 (손실 거래 {len(losses):,}건, 합 {tot_loss:,.0f}원)')
    for k in (0.01, 0.05, 0.10, 0.25):
        m = max(1, int(len(losses) * k))
        print(f'   상위 {k:>4.0%} 손실({m:,}건) = 전체 손실의 {losses.head(m).sum()/tot_loss*100:5.1f}%')

    # Q2 승패 비대칭.
    win, lose = pnl[pnl > 0], pnl[pnl <= 0]
    wr = len(win) / n * 100
    print(f'\n[Q2] 승패 구조: 승률 {wr:.1f}% · 승 평균 {win.mean():,.0f} · 패 평균 {lose.mean():,.0f}'
          f' · 손익비 {abs(win.mean()/lose.mean()):.2f}')
    be_wr = abs(lose.mean()) / (win.mean() + abs(lose.mean())) * 100
    print(f'   손익분기 승률 = {be_wr:.1f}% → 현재 {wr:.1f}% (부족분 {be_wr-wr:+.1f}%p)')
    print(f'   ※ 승률을 {be_wr:.1f}% 로 올리거나, 손익비를 {abs(lose.mean())/win.mean()*(wr/(100-wr)):.2f} 배로 만들어야 본전')

    # Q3 보유시간.
    if '보유시간' in df.columns:
        hold = pd.to_numeric(df['보유시간'], errors='coerce')
        bins = [0, 30, 60, 120, 300, 600, 1e9]
        labels = ['~30초', '30~60초', '1~2분', '2~5분', '5~10분', '10분+']
        g = df.assign(_h=pd.cut(hold, bins, labels=labels)).groupby('_h', observed=True)
        print('\n[Q3] 보유시간별')
        for k, sub in g:
            p = sub['_pnl']
            print(f'   {str(k):>8s}: {len(sub):>5,}건 · 건당 {p.mean():>8,.0f} · 승률 {(sub["_ret"]>0).mean()*100:4.1f}% · 합 {p.sum():>13,.0f}')

    # Q4 하루 반복 진입.
    per_day = df.groupby('_date').agg(n=('_pnl', 'size'), pnl=('_pnl', 'sum'))
    print(f'\n[Q4] 일별: {len(per_day)}일 · 하루 평균 {per_day["n"].mean():.1f}건'
          f' · 흑자일 {(per_day["pnl"]>0).mean()*100:.1f}%')
    q = per_day['n'].quantile([0.25, 0.5, 0.75, 0.95]).round(0).astype(int).to_dict()
    print(f'   하루 거래수 분위: {q}')
    hi = per_day[per_day['n'] >= per_day['n'].quantile(0.75)]
    lo = per_day[per_day['n'] <= per_day['n'].quantile(0.25)]
    print(f'   많이 산 날(상위25%) 건당 {hi["pnl"].sum()/hi["n"].sum():>8,.0f} vs 적게 산 날(하위25%) {lo["pnl"].sum()/lo["n"].sum():>8,.0f}')

    # 종목 반복.
    per_stock = df.groupby('종목명').agg(n=('_pnl', 'size'), pnl=('_pnl', 'sum'))
    rep = per_stock[per_stock['n'] >= 20]
    print(f'   20회 이상 산 종목 {len(rep)}개 · 그 거래 {rep["n"].sum():,}건({rep["n"].sum()/n*100:.0f}%) · 건당 {rep["pnl"].sum()/rep["n"].sum():,.0f}')

    # Q5 청산 사유(있으면).
    for col in ('매도이유', '청산사유', '매도조건'):
        if col in df.columns:
            g = df.groupby(col).agg(n=('_pnl', 'size'), pnl=('_pnl', 'sum'))
            g['건당'] = g['pnl'] / g['n']
            g = g.sort_values('pnl').head(6)
            print(f'\n[Q5] {col} 하위 6:')
            for k, r in g.iterrows():
                print(f'   {str(k)[:44]:44s} {int(r["n"]):>5,}건 건당 {r["건당"]:>8,.0f}')
            break
