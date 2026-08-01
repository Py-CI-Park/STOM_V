# -*- coding: utf-8 -*-
"""손실 해부 3단계 — 매도식 전수 분해 + 놓쳤을 수 있는 것들 점검.

1·2단계 발견: 손실의 대부분이 단일 손절 조건에서 나온다.
이번엔 매도식 **전체**를 조건별로 뜯고, 그동안 한 번도 보지 않은 축들을 점검한다.

점검 목록(놓친 것 후보):
  S1. 매도 조건별 손익 기여 — 이익 조건 / 손실 조건 / 무의미 조건
  S2. 각 조건의 '기회비용' — 그 시점에 안 팔았으면 어떻게 됐나(MFE/MAE 로 근사)
  S3. 손절이 실제로 막아준 것 — 손절 거래의 MAE 분포(진짜 큰 손실을 막았나)
  S4. 시간대별 청산 구성 — 장 초반과 후반에서 다른가
  S5. 전략종료청산(장 마감 강제) 규모 — 청산 설계 공백
  S6. 승자의 청산 조건 — 이익은 어디서 실현되나
  S7. 비용 — 왕복 비용이 건당 손익에서 차지하는 몫
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
    df['_mfe'] = pd.to_numeric(df.get('R_MFE'), errors='coerce')
    df['_mae'] = pd.to_numeric(df.get('R_MAE'), errors='coerce')
    df['_hms'] = df['매수시간'].astype(str).str.slice(8, 12)
    return df


def short(s, n=46):
    s = str(s).strip().replace('\n', ' ')
    return s[:n]


for name, path in (('설계 2년', D), ('표본외 23개월', H)):
    df = load(path)
    tot = df['_pnl'].sum()
    print(f'\n{"#"*78}\n# {name} — {len(df):,}건 · {tot:,.0f}원 · 건당 {df["_pnl"].mean():,.0f}\n{"#"*78}')

    # S1. 매도 조건별 전수 분해.
    g = df.groupby('매도조건').agg(n=('_pnl', 'size'), pnl=('_pnl', 'sum'),
                                mfe=('_mfe', 'mean'), mae=('_mae', 'mean'),
                                ret=('_ret', 'mean'), hold=('_hold', 'median'))
    g['건당'] = g['pnl'] / g['n']
    g['승률'] = df.groupby('매도조건')['_ret'].apply(lambda s: (s > 0).mean() * 100)
    g = g.sort_values('pnl')
    print(f'\n[S1] 매도 조건 전수 ({len(g)}종) — 손익 오름차순')
    print(f'{"조건":48s} {"건수":>6s} {"건당":>9s} {"승률":>6s} {"중앙보유":>7s} {"MFE":>7s} {"MAE":>7s} {"기여%":>7s}')
    for k, r in g.iterrows():
        print(f'{short(k,48):48s} {int(r["n"]):>6,} {r["건당"]:>9,.0f} {r["승률"]:>5.1f}% '
              f'{r["hold"]:>7,.0f} {r["mfe"]:>+7.2f} {r["mae"]:>+7.2f} {r["pnl"]/tot*100:>6.1f}%')

    # S3. 손절이 막아준 것 — 손절 거래의 MAE 분포.
    stop = df[df['매도조건'].astype(str).str.contains('최저현재가', na=False)]
    if len(stop):
        print(f'\n[S3] 손절류 청산 {len(stop):,}건 — 정말 큰 손실을 막았나?')
        print(f'   실현 손익 평균 {stop["_pnl"].mean():,.0f} · 실현 수익률 평균 {stop["_ret"].mean():+.2f}%')
        print(f'   MAE(최저 도달) 평균 {stop["_mae"].mean():+.2f}% · 중앙 {stop["_mae"].median():+.2f}%')
        print(f'   MFE(최고 도달) 평균 {stop["_mfe"].mean():+.2f}% · 중앙 {stop["_mfe"].median():+.2f}%')
        for thr in (-1, -2, -3, -5):
            k = (stop['_mae'] <= thr).sum()
            print(f'     MAE ≤ {thr}% 였던 거래: {k:>5,}건 ({k/len(stop)*100:4.1f}%)')
        near = stop[(stop['_mae'] > -1.0)]
        print(f'   → MAE 가 −1% 도 안 갔는데 잘린 거래: {len(near):,}건 ({len(near)/len(stop)*100:.1f}%)'
              f' · 그 손익 합 {near["_pnl"].sum():,.0f}')

    # S4. 시간대별 청산 구성.
    print('\n[S4] 매수 시각대별 (청산 성적)')
    for lo, hi, lab in ((900, 905, '09:00~05'), (905, 910, '09:05~10'), (910, 920, '09:10~20'), (920, 2400, '09:20+')):
        sub = df[(pd.to_numeric(df['_hms'], errors='coerce') >= lo) & (pd.to_numeric(df['_hms'], errors='coerce') < hi)]
        if len(sub) < 50:
            continue
        stop_share = sub['매도조건'].astype(str).str.contains('최저현재가', na=False).mean() * 100
        print(f'   {lab}: {len(sub):>6,}건 · 건당 {sub["_pnl"].mean():>8,.0f} · 승률 {(sub["_ret"]>0).mean()*100:4.1f}%'
              f' · 손절비중 {stop_share:4.1f}%')

    # S6. 승자의 청산.
    win = df[df['_pnl'] > 0]
    gw = win.groupby('매도조건').agg(n=('_pnl', 'size'), pnl=('_pnl', 'sum'))
    gw = gw.sort_values('pnl', ascending=False).head(4)
    print('\n[S6] 이익은 어디서 실현되나 (상위 4)')
    for k, r in gw.iterrows():
        print(f'   {short(k,52):52s} {int(r["n"]):>5,}건 · 합 {r["pnl"]:>13,.0f}')

    # S7. 비용 — **추정 금지, 역산으로 실측한다**.
    #   수익금/매도금액은 이미 비용 차감 후다(utility/static.py GetKiwoomPgSgSp:
    #   세금 0.18% + 매수·매도 수수료 각 0.015%). 따라서 '매도금액 - 매수금액'
    #   으로는 비용이 0으로 나온다(실제로 그렇게 나온다 — 검증됨).
    #   비용을 보려면 수량으로 비용 전 매도대금을 복원해야 한다.
    bg = pd.to_numeric(df['매수금액'], errors='coerce')
    cg_net = pd.to_numeric(df['매도금액'], errors='coerce')      # 이미 비용 차감 후
    bp = pd.to_numeric(df['매수가'], errors='coerce')
    sp_ = pd.to_numeric(df['매도가'], errors='coerce')
    qty = (bg / bp).round()
    gross_sell = sp_ * qty                                        # 비용 전 매도대금
    cost = gross_sell - cg_net
    gross_pnl = gross_sell - bg
    print(f'\n[S7] 비용 실측 (수량 역산) — 평균 진입 {bg.mean():,.0f}원')
    print(f'   비용        건당 {cost.mean():>9,.0f}원 ({cost.mean()/bg.mean()*100:.3f}%) · 합 {cost.sum():>15,.0f}')
    print(f'   비용 전 손익 건당 {gross_pnl.mean():>9,.0f}원 · 합 {gross_pnl.sum():>15,.0f}')
    print(f'   비용 후 손익 건당 {df["_pnl"].mean():>9,.0f}원 · 합 {df["_pnl"].sum():>15,.0f}')
    verdict = '흑자' if gross_pnl.sum() > 0 else '적자'
    print(f'   → 비용 전 기준 이 전략은 **{verdict}** — 건당 {cost.mean()/bg.mean()*100:.3f}% 를 넘겨야 실전 흑자')
