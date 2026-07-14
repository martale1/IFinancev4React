import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath('.'))
from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManager import AlligatorChartManager

ta = TechnicalAnalyzer('AAPL', '1y')
ta.calculate_TA_Indicators('MACD,RSI,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30')
cm = AlligatorChartManager(ta)

print("0. Setup data")
cm.df = cm.ta.dataframe.copy()
cm.ticker = getattr(cm.ta, "ticker", cm.ticker)

print("1. Windown temporal")
df = cm.df.tail(120).copy()
df0 = df.copy()
df_pos = cm._convert_to_positions(df)

print("2. Setup panels")
show_volume = False
show_rsi = True
show_stoch = True
show_willr = True
show_adx = True
show_atr_pct_panel = False
show_tech_score = False
show_mcs = False
show_sar = True
show_mas = True
show_chandelier = True
show_signal6_bg = False
volume_ma = (10, 5)

have_osc_panel = (show_rsi or show_stoch or show_willr)
n_panels = 1  # Price
if show_volume: n_panels += 1
if have_osc_panel: n_panels += 1
n_panels += 1  # MACD
if show_mcs: n_panels += 1
if show_tech_score: n_panels += 1
if show_adx: n_panels += 1
if show_atr_pct_panel: n_panels += 1

ratios = [4.5]
if show_volume: ratios.append(1.8)
if have_osc_panel: ratios.append(2.4)
ratios.append(2.8)
if show_mcs: ratios.append(2.8)
if show_tech_score: ratios.append(2.2)
if show_adx: ratios.append(2.4)
if show_atr_pct_panel: ratios.append(1.6)

plt.style.use('default')
fig, axs = plt.subplots(n_panels, 1, figsize=(16, 20), dpi=110, sharex=True, gridspec_kw={'height_ratios': ratios})
axes = list(axs) if isinstance(axs, (list, np.ndarray)) else [axs]
idx_ax = 0

ax_price = axes[idx_ax]; idx_ax += 1
ax_vol = None
if show_volume: ax_vol = axes[idx_ax]; idx_ax += 1
ax_stoch = None
if have_osc_panel: ax_stoch = axes[idx_ax]; idx_ax += 1
ax_macd = axes[idx_ax]; idx_ax += 1
ax_mcs = None
if show_mcs: ax_mcs = axes[idx_ax]; idx_ax += 1
ax_ts = None
if show_tech_score: ax_ts = axes[idx_ax]; idx_ax += 1
ax_adx = None
if show_adx: ax_adx = axes[idx_ax]; idx_ax += 1
ax_atr_pct = None
if show_atr_pct_panel: ax_atr_pct = axes[idx_ax]

print("3. Plotting Price")
ax_price.plot(df_pos.index, df_pos['Close'], linewidth=2.2, label='Close Price', zorder=5)

for col, color, lbl in [
    ('Alligator_Jaw', 'blue', 'Jaw (Blue)'),
    ('Alligator_Teeth', 'red', 'Teeth (Red)'),
    ('Alligator_Lips', 'green', 'Lips (Green)')
]:
    if col in df_pos.columns and not df_pos[col].isna().all():
        ax_price.plot(df_pos.index, df_pos[col], color=color, linewidth=2.2, alpha=0.8, label=lbl, zorder=3)

print("4. SAR & Moving Averages")
if show_sar: cm._add_sar_indicator_positions(ax_price, df_pos)
if show_mas: cm._add_moving_averages_positions(ax_price, df_pos)

print("5. CE Long")
if show_chandelier and {'CE_Long', 'CE_Short'}.issubset(df_pos.columns):
    ax_price.plot(df_pos.index, df_pos['CE_Long'], linewidth=1.2, alpha=0.9, label='CE Long', zorder=2)
    ax_price.plot(df_pos.index, df_pos['CE_Short'], linewidth=1.2, alpha=0.9, label='CE Short', zorder=2)

cm._optimize_chart_layout_positions(ax_price, df_pos)
ax_price.set_ylabel('Price')
ax_price.set_title(f"{cm.ticker} - Price")
ax_price.legend(loc='upper left', ncol=2, framealpha=0.9)

print("6. Plotting Volume")
if show_volume and ax_vol is not None:
    cm._add_volume_bars_positions(ax_vol, df_pos, ma_periods=volume_ma, width=0.8)

print("7. Plotting Oscillators (Stoch/RSI/WillR)")
if have_osc_panel and ax_stoch is not None:
    if show_rsi and 'RSI' in df_pos.columns:
        ax_stoch.plot(df_pos.index, df_pos['RSI'], linewidth=1.6, color='#F4B000', label='RSI')
        ax_stoch.axhline(70, linewidth=4, linestyle=':', alpha=0.7)
        ax_stoch.axhline(50, linewidth=2, linestyle=':', alpha=0.7)
        ax_stoch.axhline(30, linewidth=4, linestyle=':', alpha=0.7)

    if show_stoch and all(c in df_pos.columns for c in ['Stoch_K', 'Stoch_D']):
        ax_stoch.plot(df_pos.index, df_pos['Stoch_K'], linewidth=1.3, color='blue', linestyle='-', label='Stoch K')
        ax_stoch.plot(df_pos.index, df_pos['Stoch_D'], linewidth=1.3, color='red', linestyle='-', label='Stoch D')
        ax_stoch.axhline(80, linewidth=0.8, linestyle=':', alpha=0.7)
        ax_stoch.axhline(20, linewidth=0.8, linestyle=':', alpha=0.7)

    print("   -> Plotting Williams %R")
    if show_willr and 'Williams_R' in df_pos.columns:
        ax_willr = ax_stoch.twinx()
        ax_willr.plot(df_pos.index, df_pos['Williams_R'], linewidth=1.2, color='purple', label='Williams %R')
        ax_willr.set_ylim(-105, 5)
        ax_willr.axhline(-80, color='purple', linewidth=0.8, linestyle=':', alpha=0.5)
        ax_willr.axhline(-20, color='purple', linewidth=0.8, linestyle=':', alpha=0.5)
        ax_willr.set_ylabel('Williams %R (-100..0)', color='purple')
        ax_willr.tick_params(axis='y', labelcolor='purple')

    ax_stoch.set_ylim(-5, 105)
    ax_stoch.set_ylabel('Oscillators (0..100)')
    ax_stoch.set_title('RSI / Stoch / Williams%R')

    if 'ax_willr' in locals():
        print("   -> Combining legends")
        lines1, labels1 = ax_stoch.get_legend_handles_labels()
        lines2, labels2 = ax_willr.get_legend_handles_labels()
        ax_stoch.legend(lines1 + lines2, labels1 + labels2, loc='upper left', ncol=2, framealpha=0.9)
    else:
        ax_stoch.legend(loc='upper left', ncol=2, framealpha=0.9)

print("8. Plotting MACD")
if all(c in df_pos.columns for c in ['MACD', 'MACD_Signal', 'MACD_Hist']):
    idx_x, macd, sig, hist = df_pos.index, df_pos['MACD'], df_pos['MACD_Signal'], df_pos['MACD_Hist']
    ax_macd.axhline(0, color='0.4', linewidth=1, linestyle='--', alpha=0.6)
    ax_macd.plot(idx_x, macd, linewidth=1.8, color='blue', label='MACD')
    ax_macd.plot(idx_x, sig, linewidth=1.8, color='red', label='MACD Signal')
    ax_macd.bar(idx_x, hist, width=0.8, alpha=0.7, color='green', label='MACD Histogram', zorder=0)
    ax_macd.set_ylabel('MACD')
    ax_macd.set_title('MACD / Signal / Histogram')
    ax_macd.legend(loc='upper left', framealpha=0.9)

print("9. Plotting ADX")
if show_adx and ax_adx is not None:
    cm._add_adx_panel_positions(ax_adx, df_pos)

print("10. Date axis & layout")
bottom_ax = axes[-1]
cm._setup_date_axis(bottom_ax, df0, df_pos.index)

for ax in [ax_price, ax_macd]:
    ax.grid(True, alpha=0.35)
if ax_vol is not None: ax_vol.grid(True, alpha=0.35)
if ax_stoch is not None: ax_stoch.grid(True, alpha=0.35)
if ax_adx is not None: ax_adx.grid(True, alpha=0.35)

print("11. Saving figure")
fig.savefig("scratch/test_chart_output_step.png", dpi=110, bbox_inches='tight')
print("Finished completely!")
