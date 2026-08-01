# -*- coding: utf-8 -*-
"""손실 해부 2단계 — 1~2분 손실의 정체를 밝힌다.

1단계 발견: 1~2분 보유 구간이 승률 14~16%, 건당 −54k~−63k 로 전체 손실을 초과.
   두 구간(설계 2년·표본외 23개월)에서 동일 재현 → 우연 아님.

이번 질문:
  A. 그 거래들은 어떤 청산 조건으로 나갔나? (진입 문제 vs 청산 문제 분리)
  B. 나가기 전에 이익이었던 적이 있나? (MFE — 있으면 '먹을 걸 놓친 것')
  C. 진입 시점 변수로 그 거래들을 미리 알아볼 수 있나? (있으면 진입 필터)
  D. 그 거래를 '안 했다면' vs '더 오래 들었다면' 무엇이 나았나?
"""
import os
import pandas as pd
from ai_strategy_loop.autopsy.label_dataset import enrich

D = 'backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731234533.csv'
H = 'backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731235145.csv'


def load(p):
    df = enrich(pd.read_csv(p, encoding='utf-8-sig')).df
    df['_pnl'] = pd.to_numeric(df['수익금'], errors='coerce').fillna(0)
    df['_ret'] = pd.to_numeric(df['수익률'], errors='coerce')
    df['_hold'] = pd.to_numeric(df.get('보유시간'), errors='coerce')
    return df


for name, path in (('설계 2년', D), ('표본외 23개월', H)):
    df = load(path)
    band = df[(df['_hold'] > 60) & (df['_hold'] <= 120)]
    print(f'\n{"="*74}\n{name} — 1~2분 보유 거래 {len(band):,}건 · 합 {band["_pnl"].sum():,.0f} · 건당 {band["_pnl"].mean():,.0f}')
    print("="*74)

    # A. 청산 조건 분해.
    if '매도조건' in band.columns:
        g = band.groupby('매도조건').agg(n=('_pnl', 'size'), pnl=('_pnl', 'sum'))
        g['건당'] = g['pnl'] / g['n']
        g = g.sort_values('pnl')
        print('\n[A] 이 구간의 청산 조건별')
        for k, r in g.head(5).iterrows():
            share = r['pnl'] / band['_pnl'].sum() * 100
            print(f"   {str(k)[:52]:52s} {int(r['n']):>5,}건 건당 {r['건당']:>9,.0f} (손실의 {share:4.1f}%)")

    # B. MFE/MAE — 나가기 전에 이익 구간이 있었나.
    for mfe_col, mae_col in (('R_MFE', 'R_MAE'), ('R_매수후최고수익률', 'R_매수후최저수익률')):
        if mfe_col in band.columns:
            mfe = pd.to_numeric(band[mfe_col], errors='coerce')
            mae = pd.to_numeric(band[mae_col], errors='coerce')
            print(f'\n[B] {mfe_col}(최고 도달)/{mae_col}(최저 도달) — 손실 거래만')
            lose = band[band['_pnl'] <= 0]
            lm, la = pd.to_numeric(lose[mfe_col], errors='coerce'), pd.to_numeric(lose[mae_col], errors='coerce')
            print(f'   손실 {len(lose):,}건: 최고 도달 평균 {lm.mean():+.2f}% (중앙 {lm.median():+.2f}%)'
                  f' · 최저 도달 평균 {la.mean():+.2f}%')
            for thr in (0.5, 1.0, 2.0):
                k = (lm >= thr).sum()
                print(f'     한때 +{thr}% 이상이었던 손실 거래: {k:,}건 ({k/max(1,len(lose))*100:.1f}%)')
            break

    # C. 진입 시점 변수로 구분되나 — 1~2분 손실 vs 5~10분 이익.
    bad = df[(df['_hold'] > 60) & (df['_hold'] <= 120)]
    good = df[(df['_hold'] > 300) & (df['_hold'] <= 600)]
    feats = [c for c in df.columns if c.startswith('B_') and pd.to_numeric(df[c], errors='coerce').notna().sum() > 500]
    rows = []
    for f in feats:
        b = pd.to_numeric(bad[f], errors='coerce').dropna()
        g = pd.to_numeric(good[f], errors='coerce').dropna()
        if len(b) < 100 or len(g) < 100:
            continue
        pooled = ((b.std() ** 2 + g.std() ** 2) / 2) ** 0.5
        if pooled <= 0:
            continue
        rows.append((abs((b.mean() - g.mean()) / pooled), f, b.mean(), g.mean()))
    rows.sort(reverse=True)
    print('\n[C] 진입 변수로 구분 가능한가 (1~2분 손실군 vs 5~10분 이익군, 효과크기 상위 5)')
    for d, f, bm, gm in rows[:5]:
        print(f'   {f:22s} d={d:.3f}  손실군 {bm:>12,.1f} vs 이익군 {gm:>12,.1f}')

    # D. 반사실 — 이 구간을 아예 안 했다면.
    rest = df[~((df['_hold'] > 60) & (df['_hold'] <= 120))]
    print(f'\n[D] 1~2분 구간 제외 시: {len(rest):,}건 · 합 {rest["_pnl"].sum():,.0f} · 건당 {rest["_pnl"].mean():,.0f}'
          f'  (전체 건당 {df["_pnl"].mean():,.0f} → 개선 {df["_pnl"].mean() - rest["_pnl"].mean():+,.0f})')
