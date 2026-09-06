import os
import sys

# Ensure matplotlib DLLs can be loaded on Windows when running Python directly
if sys.platform == "win32":
    env_dir = r"C:\Users\theoi\anaconda3\envs\IFinanceTA"
    for d in [
        os.path.join(env_dir, "Library", "bin"),
        os.path.join(env_dir, "Library", "mingw-w64", "bin"),
        os.path.join(env_dir, "bin"),
    ]:
        if os.path.exists(d):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from typing import Optional  # <-- per compatibilità Python < 3.10


class AlligatorChartManager:
    """
    Classe per gestire la visualizzazione dei grafici dell'indicatore Alligator.
    Versione ottimizzata per massimizzare la visibilità e l'utilizzo dello spazio.
    """

    def __init__(self, technical_analyzer=None):
        """
        Inizializza il chart manager

        Args:
            technical_analyzer (TechnicalAnalyzer, optional): Istanza di TechnicalAnalyzer
        """
        self.ta = technical_analyzer
        self.df = None
        self.ticker = None
        self.tickerName = None

        if technical_analyzer:
            self.df = technical_analyzer.dataframe.copy()
            self.ticker = technical_analyzer.ticker

    def _add_trade_levels(
            self,
            ax,
            df_pos,
            show_sl1=True,
            show_sl2=True,
            show_pullback=False,
            sl1_col="Trend_Stop_Level",
            sl2_col="CE_Long",
            pb_low_col="Pullback_Entry_Zone_Low",
            pb_high_col="Pullback_Entry_Zone_High",
            pb_level_col="Pullback_Entry_Level",
            pb_stop_col="Pullback_Stop_Level",
    ):
        import pandas as pd

        def last_valid(colname):
            if colname not in df_pos.columns:
                return None

            s = df_pos[colname]

            # gestisce "21,76" -> "21.76"
            s = (
                s.astype(str)
                    .str.replace(" ", "", regex=False)
                    .str.replace(",", ".", regex=False)
            )

            s = pd.to_numeric(s, errors="coerce").dropna()
            if s.empty:
                return None
            return float(s.iloc[-1])

        sl1 = last_valid(sl1_col) if show_sl1 else None
        sl2 = last_valid(sl2_col) if show_sl2 else None

        pb_low = last_valid(pb_low_col) if show_pullback else None
        pb_high = last_valid(pb_high_col) if show_pullback else None
        pb_lvl = last_valid(pb_level_col) if show_pullback else None
        pb_stop = last_valid(pb_stop_col) if show_pullback else None

        # ---------- SL1 ----------
        if sl1 is not None:
            self._add_safe_axhline(ax, sl1, linestyle="--", linewidth=1.1, alpha=0.85, color="red", zorder=5)
            ax.text(
                0.01, sl1, f" SL1 {sl1:.2f}",
                color="red", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )

        # ---------- SL2 ----------
        if sl2 is not None:
            self._add_safe_axhline(ax, sl2, linestyle="--", linewidth=1.1, alpha=0.85, color="darkred", zorder=5)
            ax.text(
                0.01, sl2, f" SL2 {sl2:.2f}",
                color="darkred", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )

        # ---------- PULLBACK ZONE (fascia + DUE linee ai bordi) ----------
        if (pb_low is not None) and (pb_high is not None) and (pb_low < pb_high):
            # fascia
            ax.axhspan(pb_low, pb_high, alpha=0.12, color="orange", zorder=1.5)

            # linee range (queste sono le 21.76 / 22.10 che volevi vedere)
            self._add_safe_axhline(ax, pb_low, linestyle="--", linewidth=1.0, alpha=0.85, color="orange", zorder=6)
            self._add_safe_axhline(ax, pb_high, linestyle="--", linewidth=1.0, alpha=0.85, color="orange", zorder=6)

            # label centrale
            ax.text(
                0.01, (pb_low + pb_high) / 2,
                f" Pullback zone {pb_low:.2f} – {pb_high:.2f}",
                color="orange", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )

            # label sui bordi (opzionale ma utile)
            ax.text(
                0.01, pb_low, f" PB Low {pb_low:.2f}",
                color="orange", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )
            ax.text(
                0.01, pb_high, f" PB High {pb_high:.2f}",
                color="orange", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )

        # ---------- PULLBACK ENTRY ----------
        if pb_lvl is not None:
            self._add_safe_axhline(ax, pb_lvl, linestyle=":", linewidth=1.1, alpha=0.9, color="orange", zorder=6)
            ax.text(
                0.01, pb_lvl, f" EntryRef {pb_lvl:.2f}",
                color="orange", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )

        # ---------- PULLBACK STOP ----------
        if pb_stop is not None:
            self._add_safe_axhline(ax, pb_stop, linestyle="--", linewidth=1.1, alpha=0.9, color="brown", zorder=6)
            ax.text(
                0.01, pb_stop, f" PB Stop {pb_stop:.2f}",
                color="brown", fontsize=8, va="center", ha="left",
                transform=ax.get_yaxis_transform(), zorder=7
            )

    def _add_techscore_panel_positions(self, ax, df_pos):
        """
        Pannello Technical Score (0..100) con soglie/marker:
          - linee guida: 20 / 40 / 60 / 80
          - area 'zona neutra' 40..60
          - marker su cross 60 (up) e 40 (down)
          - badge con ultimo valore e fascia
        """
        import numpy as np

        if 'TECH_SCORE' not in df_pos.columns or df_pos['TECH_SCORE'].isna().all():
            ax.text(0.02, 0.7, "TECH_SCORE non disponibile", transform=ax.transAxes)
            return False

        idx = df_pos.index
        ts = pd.to_numeric(df_pos['TECH_SCORE'], errors='coerce')

        # linee guida
        for y, ls in [(50, '--'), (60, ':'), (40, ':'), (80, '-.'), (20, '-.')]:
            self._add_safe_axhline(ax, y, linewidth=1.0, linestyle=ls, alpha=0.6)

        # banda neutra 40..60
        ax.fill_between(idx, 40, 60, alpha=0.08, zorder=0)

        # curva principale
        ax.plot(idx, ts, linewidth=2.0, label='TECH_SCORE', zorder=2)

        # marker cross: sopra 60 (bull) / sotto 40 (bear)
        cross_up = (ts.shift(1) <= 60) & (ts > 60)
        cross_dn = (ts.shift(1) >= 40) & (ts < 40)
        if cross_up.any():
            ax.scatter(idx[cross_up], ts[cross_up], marker='^', s=110, color='green',
                       edgecolors='black', linewidth=1.0, zorder=5, label='Cross > 60')
        if cross_dn.any():
            ax.scatter(idx[cross_dn], ts[cross_dn], marker='v', s=110, color='red',
                       edgecolors='black', linewidth=1.0, zorder=5, label='Cross < 40')

        # badge ultimo valore + fascia
        last = float(ts.iloc[-1])

        def fascia(val):
            if val >= 80: return "BULL EXTREME"
            if val >= 60: return "BULL STRONG"
            if val >= 40: return "BULL/BEAR NEUTRAL"
            if val >= 20: return "BEAR IMPROVING"
            return "BEAR STRONG"

        state = fascia(last)
        edge = 'green' if last >= 60 else ('gray' if 40 <= last < 60 else 'red')
        ax.text(0.985, 0.92, f"{last:.1f} — {state}",
                transform=ax.transAxes, ha='right', va='top',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.35", fc="lightyellow", alpha=0.9, ec=edge))

        ax.set_ylim(0, 100)
        ax.set_ylabel('Tech Score (0..100)')
        ax.set_title('Technical Score')
        ax.legend(loc='upper left', framealpha=0.92)
        return True

    def fetch_ticker_name(self, prefer_long: bool = True) -> str:
        """
        Ricava e cache-a il nome del ticker per il ChartManager.
        Tenta prima da TechnicalAnalyzer, poi direttamente da Yahoo.
        """
        # 1) se già risolto
        if getattr(self, "tickerName", None):
            return self.tickerName

        # 2) se ho un TechnicalAnalyzer con nome già pronto
        if self.ta is not None and getattr(self.ta, "tickerName", None):
            self.tickerName = self.ta.tickerName
            return self.tickerName

        # 3) provo a farmelo dare dal TA (se ha il metodo)
        if self.ta is not None and hasattr(self.ta, "fetch_ticker_name"):
            try:
                self.tickerName = self.ta.fetch_ticker_name(prefer_long=prefer_long)
                if self.tickerName:
                    return self.tickerName
            except Exception:
                pass

        # 4) chiamata diretta a Yahoo (senza dipendenze globali)
        try:
            import yfinance as yf
            info = (yf.Ticker(self.ticker).get_info()) or {}
            if prefer_long:
                name = info.get("longName") or info.get("shortName")
            else:
                name = info.get("shortName") or info.get("longName")
            name = name or info.get("displayName") or info.get("symbol") or str(self.ticker)
            self.tickerName = name
            return name
        except Exception:
            # Fallback sicuro
            self.tickerName = str(self.ticker)
            return self.tickerName

    def set_data(self, dataframe, ticker):
        """
        Imposta i dati manualmente se non si usa TechnicalAnalyzer
        """
        self.df = dataframe.copy()
        self.ticker = ticker

    def _validate_alligator_data(self):
        if self.df is None:
            raise ValueError("Nessun dato disponibile. Usa set_data() o passa TechnicalAnalyzer nel costruttore.")
        required_cols = ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw', 'Close']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Indicatori Alligator mancanti: {missing_cols}")
        return True

    def _ensure_signal6(self):
        if 'Signal6' not in self.df.columns and self.ta:
            print("Signal6 non trovato, lo calcolo automaticamente...")
            self.ta.calculate_alligator_signal6()
            self.df = self.ta.dataframe.copy()

    def _validate_candlestick_data(self):
        if self.df is None:
            print("⚠️  ATTENZIONE: Nessun dato disponibile per candlestick.")
            print("Utilizzo il grafico a linee invece delle candlestick...")
            return False
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        if missing_cols:
            print(f"⚠️  ATTENZIONE: Dati OHLC mancanti: {missing_cols}")
            print("Utilizzo il grafico a linee invece delle candlestick...")
            return False
        return True

    def _optimize_chart_layout(self, ax, df):
        y_values = []
        y_values.extend(df['Close'].dropna().values)
        y_values.extend(df['Alligator_Jaw'].dropna().values)
        y_values.extend(df['Alligator_Teeth'].dropna().values)
        y_values.extend(df['Alligator_Lips'].dropna().values)

        if all(col in df.columns for col in ['High', 'Low']):
            y_values.extend(df['High'].dropna().values)
            y_values.extend(df['Low'].dropna().values)
        if 'SAR' in df.columns:
            y_values.extend(df['SAR'].dropna().values)

        ma_columns = [col for col in df.columns if
                      col.startswith(('MA_', 'EMA_', 'SMA_')) and
                      col not in ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw']]
        for ma_col in ma_columns:
            if ma_col in df.columns:
                y_values.extend(df[ma_col].dropna().values)

        if y_values:
            y_min = min(y_values)
            y_max = max(y_values)
            y_range = y_max - y_min
            margin = y_range * 0.02
            ax.set_ylim(y_min - margin, y_max + margin)

        if len(df) > 0:
            time_range = df.index[-1] - df.index[0]
            margin = time_range * 0.01
            ax.set_xlim(df.index[0] - margin, df.index[-1] + margin)

    def _setup_figure_style(self, figsize=None, dpi=100):
        if figsize is None:
            figsize = (16, 10)
        plt.style.use('default')
        plt.rcParams.update({
            'figure.figsize': figsize,
            'figure.dpi': dpi,
            'axes.grid': True,
            'grid.alpha': 0.3,
            'axes.axisbelow': True,
            'font.size': 11,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'legend.fontsize': 10
        })
        return plt.subplots(figsize=figsize, dpi=dpi)

    def _setup_date_axis(self, ax, df, positions):
        import numpy as np
        ax.set_xlim(-0.5, len(df) - 0.5)
        num_labels = min(8, len(df))
        if len(df) > 1:
            step = max(1, len(df) // num_labels)
            label_positions = np.arange(0, len(df), step)
            if label_positions[-1] != len(df) - 1:
                label_positions = np.append(label_positions, len(df) - 1)
        else:
            label_positions = [0]
        ax.set_xticks(label_positions)
        date_labels = [df.index[int(pos)].strftime('%Y-%m-%d') for pos in label_positions]
        ax.set_xticklabels(date_labels, rotation=45, ha='right')

    def _convert_to_positions(self, df):
        import numpy as np
        df_pos = df.copy()
        df_pos['original_index'] = df.index
        df_pos.index = np.arange(len(df))
        return df_pos

    def _add_safe_axhline(self, ax, y, **kwargs):
        """Draws a horizontal line using ax.plot to prevent C-level segfaults."""
        x_limits = ax.get_xlim()
        x_min = x_limits[0] if x_limits[0] != 0.0 or x_limits[1] != 1.0 else -1000
        x_max = x_limits[1] if x_limits[0] != 0.0 or x_limits[1] != 1.0 else 10000
        line = ax.plot([x_min, x_max], [y, y], **kwargs)
        ax.set_xlim(x_limits)
        return line[0] if line else None

    def _add_safe_axvspan(self, ax, xmin, xmax, **kwargs):
        """Draws a vertical span using ax.fill_between to prevent C-level segfaults."""
        y_limits = ax.get_ylim()
        span = ax.fill_between([xmin, xmax], y_limits[0], y_limits[1], **kwargs)
        ax.set_ylim(y_limits)
        return span

    def _add_safe_bar(self, ax, x, y, width=0.8, color='blue', **kwargs):
        """Draws vertical bars using ax.plot loop to prevent C-level segfaults."""
        import numpy as np
        x_arr = np.array(x)
        y_arr = np.array(y)
        mask = ~np.isnan(x_arr) & ~np.isnan(y_arr)
        x_arr = x_arr[mask]
        y_arr = y_arr[mask]
        
        # Calculate dynamic line thickness to make them look exactly like bars
        try:
            fig = ax.get_figure()
            fig_width = fig.get_size_inches()[0] if fig else 16.0
        except Exception:
            fig_width = 16.0

        if len(x_arr) > 1:
            x_span = float(np.max(x_arr) - np.min(x_arr))
            N = x_span + 1.0
        else:
            N = float(len(x_arr)) if len(x_arr) > 0 else 1.0
            
        N = max(N, 1.0)
        
        # Calculate ideal linewidth in points to fill 'width' (default 0.8) fraction of the slot.
        # Standard axes width is around 80-85% of figure width.
        axes_fraction = 0.82
        ideal_lw = (fig_width * axes_fraction / N) * width * 72.0
        
        # Apply reasonable boundaries for linewidth
        default_lw = max(1.5, min(ideal_lw, 60.0))
            
        lw = kwargs.pop('linewidth', default_lw)
        first = True
        for xi, yi in zip(x_arr, y_arr):
            lbl = kwargs.get('label') if first else None
            c = kwargs.get('color', color)
            kw = {k: v for k, v in kwargs.items() if k != 'color'}
            ax.plot([xi, xi], [0, yi], color=c, linewidth=lw, solid_capstyle='butt', **{**kw, 'label': lbl})
            first = False

    def plot_simple_alligator(self, days=None, show_signals=True, figsize=None,
                              title=None, show_signal6_markers=True, show_sar=True,
                              show_moving_averages=True, chart_type='line', dpi=100,
                              max_candles=200):
        self._validate_alligator_data()
        use_candlestick = False
        if chart_type.lower() == 'candlestick':
            use_candlestick = self._validate_candlestick_data()

        df = self.df.copy()
        if days:
            df = df.tail(days)
        if use_candlestick and len(df) > max_candles:
            df = self._optimize_candlestick_density(df, max_candles)

        df_original = df.copy()
        df_pos = self._convert_to_positions(df)
        fig, ax = self._setup_figure_style(figsize, dpi)

        if use_candlestick:
            self._add_candlesticks(ax, df_original)
        else:
            ax.plot(df_pos.index, df_pos['Close'], color='black', linewidth=2.5,
                    label='Close Price', zorder=5, alpha=0.9)
            self._setup_date_axis(ax, df_original, df_pos.index)

        ax.plot(df_pos.index, df_pos['Alligator_Jaw'], color='blue', linewidth=2.5,
                label='Jaw (Blue)', alpha=0.8, zorder=3)
        ax.plot(df_pos.index, df_pos['Alligator_Teeth'], color='red', linewidth=2.5,
                label='Teeth (Red)', alpha=0.8, zorder=3)
        ax.plot(df_pos.index, df_pos['Alligator_Lips'], color='green', linewidth=2.5,
                label='Lips (Green)', alpha=0.8, zorder=3)

        if show_sar and 'SAR' in df_pos.columns:
            self._add_sar_indicator_positions(ax, df_pos)
        if show_moving_averages:
            self._add_moving_averages_positions(ax, df_pos)
        if show_signals and 'Signal6' in df_pos.columns and show_signal6_markers:
            self._add_signal_markers_positions(ax, df_pos)

        self._optimize_chart_layout_positions(ax, df_pos)

        if title is None:
            chart_label = "Candlestick" if use_candlestick else "Line"
            title = f'{self.ticker} - Alligator Chart ({chart_label})'
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=13, fontweight='bold')
        ax.set_ylabel('Price', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.4, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        ax.legend(loc='upper left', fontsize=10, framealpha=0.95,
                  fancybox=True, shadow=True, ncol=2)

        if 'Signal6' in df_pos.columns:
            latest_signal = df_pos['Signal6'].iloc[-1]
            latest_close = df_pos['Close'].iloc[-1]
            info_text = f"Latest: {latest_close:.2f} | Signal6: {latest_signal}"
            if use_candlestick and len(self.df) > max_candles:
                info_text += f" | Showing {len(df)}/{len(self.df)} candles"
            ax.text(0.98, 0.98, info_text, transform=ax.transAxes, fontsize=11,
                    ha='right', va='top', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow",
                              alpha=0.9, edgecolor='gray'))
        plt.subplots_adjust(hspace=0.30, top=0.92, bottom=0.10, left=0.08, right=0.92)

    def _optimize_candlestick_density(self, df, max_candles=200):
        if len(df) <= max_candles:
            return df
        print(f"⚠️ Troppi dati ({len(df)} candlestick). Ottimizzazione per migliore visualizzazione...")
        recent_data = df.tail(max_candles // 2)
        older_data = df.head(len(df) - len(recent_data))
        if len(older_data) > max_candles // 2:
            step = len(older_data) // (max_candles // 2)
            older_data = older_data.iloc[::step]
        optimized_df = pd.concat([older_data, recent_data]).sort_index()
        print(f"✅ Dati ottimizzati: {len(optimized_df)} candlestick visualizzate")
        return optimized_df

    def _add_sar_indicator_positions(self, ax, df_pos):
        if 'SAR' not in df_pos.columns:
            return
        sar_above = df_pos['SAR'] > df_pos['Close']
        if sar_above.any():
            ax.scatter(df_pos.index[sar_above], df_pos['SAR'][sar_above],
                       color='red', marker='o', s=25, alpha=0.8,
                       label='SAR (Sell)', zorder=4)
        sar_below = df_pos['SAR'] <= df_pos['Close']
        if sar_below.any():
            ax.scatter(df_pos.index[sar_below], df_pos['SAR'][sar_below],
                       color='lime', marker='o', s=25, alpha=0.8,
                       label='SAR (Buy)', zorder=4)

    def _add_moving_averages_positions(self, ax, df_pos):
        ma_columns = [col for col in df_pos.columns if
                      col.startswith(('MA_', 'EMA_', 'SMA_')) and
                      col not in ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw']]
        ma_colors = ['purple', 'orange', 'brown', 'pink', 'cyan', 'magenta']
        ma_styles = ['-', '--', '-.', ':']
        for i, ma_col in enumerate(ma_columns):
            if ma_col in df_pos.columns and not df_pos[ma_col].isna().all():
                color = ma_colors[i % len(ma_colors)]
                style = ma_styles[i % len(ma_styles)]
                period = ma_col.split('_')[-1] if '_' in ma_col else ''
                label = f"{ma_col.split('_')[0]}{period}" if period else ma_col
                ax.plot(df_pos.index, df_pos[ma_col], color=color, linewidth=2,
                        linestyle=style, alpha=0.8, label=label, zorder=2)

    def _add_signal_markers_positions(self, ax, df_pos):
        signal_configs = {
            'Uptrend*': ('lime', '^', 'Uptrend Start'),
            'Downtrend*': ('red', 'v', 'Downtrend Start'),
            'wakeup2*': ('orange', 'o', 'Wakeup2 Start')
        }
        for signal, (color, marker, label) in signal_configs.items():
            signal_mask = df_pos['Signal6'] == signal
            if signal_mask.any():
                ax.scatter(df_pos.index[signal_mask], df_pos['Close'][signal_mask],
                           color=color, marker=marker, s=120, alpha=0.9,
                           label=label, zorder=6, edgecolors='black', linewidth=1.5)

    def _add_background_colors_positions(self, ax, df_pos):
        for i in range(len(df_pos)):
            signal = df_pos['Signal6'].iloc[i]
            alpha = 0.15
            if 'Uptrend' in signal:
                color = 'green'
            elif 'Downtrend' in signal:
                color = 'red'
            elif 'sleep' in signal:
                color = 'gray'
            elif 'wakeup' in signal:
                color = 'lightgreen'
            else:
                continue
            left = i - 0.5
            right = min(i + 0.5, len(df_pos) - 0.5)
            self._add_safe_axvspan(ax, left, right, color=color, alpha=alpha)

    def _resolve_di_columns(self, df_like):
        """
        Restituisce una tupla (di_plus, di_minus) scegliendo le colonne
        disponibili tra varie convenzioni:
          - 'PLUS_DI' / 'MINUS_DI'
          - '+DI' / '-DI'
          - '+DX' / '-DX'  (usati come DI+ / DI- se presenti)
        Ritorna (None, None) se non trova nulla.
        """
        candidates = [
            ('PLUS_DI', 'MINUS_DI'),
            ('+DI', '-DI'),
            ('PLUS_DI', 'MINUS_DI'),  # ripetizione intenzionale, per compatibilità
            ('+DX', '-DX'),  # tua convenzione
        ]
        for p, m in candidates:
            if p in df_like.columns and m in df_like.columns:
                return df_like[p], df_like[m]
        return None, None

    def _add_adx_panel_positions(self, ax, df_pos):
        """
        Pannello ADX + DI:
          - linee: ADX (spessa), DI+ e DI− (con vari alias gestiti da _resolve_di_columns)
          - soglia 25 (trend strength)
          - marker di cross (DI+ sopra DI− = bull, sotto = bear)
          - badge in alto a destra con ADX_Trend (se presente)
        """
        import numpy as np

        idx = df_pos.index
        have_adx = ('ADX' in df_pos.columns) and (not df_pos['ADX'].isna().all())
        di_plus, di_minus = self._resolve_di_columns(df_pos)
        have_di = (di_plus is not None) and (not di_plus.isna().all()) and \
                  (di_minus is not None) and (not di_minus.isna().all())

        if not (have_adx or have_di):
            ax.text(0.02, 0.7, "ADX/DI non disponibili", transform=ax.transAxes)
            return False

        # --- DI+ / DI−
        if have_di:
            ax.plot(idx, di_plus, linewidth=1.6, label='DI+')
            ax.plot(idx, di_minus, linewidth=1.6, label='DI−')

            # Cross DI+ / DI−
            cross_up = (di_plus.shift(1) <= di_minus.shift(1)) & (di_plus > di_minus)  # bull cross
            cross_dn = (di_plus.shift(1) >= di_minus.shift(1)) & (di_plus < di_minus)  # bear cross
            if cross_up.any():
                ax.scatter(idx[cross_up], di_plus[cross_up], marker='^', s=80,
                           edgecolors='black', linewidth=0.8, zorder=5, label='Bull cross')
            if cross_dn.any():
                ax.scatter(idx[cross_dn], di_minus[cross_dn], marker='v', s=80,
                           edgecolors='black', linewidth=0.8, zorder=5, label='Bear cross')

        # --- ADX
        if have_adx:
            ax.plot(idx, df_pos['ADX'], linewidth=2.0, label='ADX', zorder=4)
            self._add_safe_axhline(ax, 25, linestyle='--', linewidth=1, alpha=0.6)
            ax.text(1.01, 25, '25', transform=ax.get_yaxis_transform(),
                    ha='left', va='center', fontsize=8,
                    bbox=dict(fc='white', ec='gray', alpha=0.85, pad=1.5))

        # Y e labels
        #ax.set_ylim(0, 100)
        # Adatta i limiti Y al range effettivo con margine di sicurezza
        all_vals = []
        if have_adx:
            all_vals.extend(df_pos['ADX'].dropna().values)
        if have_di:
            all_vals.extend(di_plus.dropna().values)
            all_vals.extend(di_minus.dropna().values)

        if len(all_vals) > 0:
            ymin = min(all_vals)
            ymax = max(all_vals)
            span = ymax - ymin
            # margine visivo (10% dello span, minimo ±5)
            pad = max(5, span * 0.1)
            ax.set_ylim(max(0, ymin - pad), min(100, ymax + pad))
        else:
            ax.set_ylim(0, 100)

        ax.set_ylabel('ADX / DI (0..100)')
        ax.set_title('ADX + DI (25 = trend strength)')
        ax.legend(loc='upper left', framealpha=0.9, ncol=2)

        # Badge stato (se hai ADX_Trend = 'Up'/'Down'/'Flat')
        if 'ADX_Trend' in df_pos.columns and not df_pos['ADX_Trend'].isna().all():
            t = str(df_pos['ADX_Trend'].iloc[-1]).strip().lower()
            txt = 'ADX ↑' if t == 'up' else ('ADX ↓' if t == 'down' else 'ADX ·')
            ax.text(0.985, 0.90, txt, transform=ax.transAxes, ha='right', va='top',
                    fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.30', fc='white', ec='gray', alpha=0.95))
        return True

    def plot_adx(self, days=120, figsize=(16, 5), dpi=120, save=False, filename=None):
        """
        Grafico singolo con ADX + DI (con cross e soglia 25).
        Usa automaticamente self.ta per calcolare ADX/DI se mancano e la sorgente lo supporta.
        """
        if self.df is None and self.ta is not None:
            self.df = self.ta.dataframe.copy()
            self.ticker = getattr(self.ta, "ticker", self.ticker)
        if self.df is None or len(self.df) == 0:
            raise ValueError("Nessun dato. Usa set_data() o passa TechnicalAnalyzer.")

        # Prova ad auto-calcolare ADX/DI se assenti e se il TA lo consente
        need_adx = 'ADX' not in self.df.columns or self.df['ADX'].isna().all()
        p, m = self._resolve_di_columns(self.df)
        need_di = (p is None) or (m is None) or p.isna().all() or m.isna().all()
        if (need_adx or need_di) and self.ta is not None:
            try:
                self.ta.calculate_TA_Indicators("ADX,DI")
                self.df = self.ta.dataframe.copy()
            except Exception:
                pass

        df = self.df.tail(days).copy()
        df_pos = self._convert_to_positions(df)

        fig, ax = self._setup_figure_style(figsize=figsize, dpi=dpi)
        ok = self._add_adx_panel_positions(ax, df_pos)

        title = f"{self.ticker or ''} — ADX + DI (last {len(df)} bars)"
        ax.set_title(title)
        self._setup_date_axis(ax, df, df_pos.index)
        ax.grid(True, alpha=0.35)
        plt.subplots_adjust(hspace=0.30, top=0.92, bottom=0.10, left=0.08, right=0.92)

        if save:
            if not filename:
                base = (self.ticker or "chart").replace("/", "_")
                filename = f"{base}_adx.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Grafico salvato: {filename}")

        return fig

    def _optimize_chart_layout_positions(self, ax, df_pos):
        y_values = []
        y_values.extend(df_pos['Close'].dropna().values)
        y_values.extend(df_pos['Alligator_Jaw'].dropna().values)
        y_values.extend(df_pos['Alligator_Teeth'].dropna().values)
        y_values.extend(df_pos['Alligator_Lips'].dropna().values)
        if all(col in df_pos.columns for col in ['High', 'Low']):
            y_values.extend(df_pos['High'].dropna().values)
            y_values.extend(df_pos['Low'].dropna().values)
        if 'SAR' in df_pos.columns:
            y_values.extend(df_pos['SAR'].dropna().values)
        ma_columns = [col for col in df_pos.columns if
                      col.startswith(('MA_', 'EMA_', 'SMA_')) and
                      col not in ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw']]
        for ma_col in ma_columns:
            if ma_col in df_pos.columns:
                y_values.extend(df_pos[ma_col].dropna().values)
        if y_values:
            y_min = min(y_values)
            y_max = max(y_values)
            y_range = y_max - y_min
            margin = y_range * 0.02
            ax.set_ylim(y_min - margin, y_max + margin)

    def plot_advanced_alligator(self, days=60, show_background=True, figsize=None,
                                save_chart=False, filename=None, show_sar=True,
                                show_moving_averages=True, chart_type='line', dpi=100,
                                max_candles=200):
        self._validate_alligator_data()
        self._ensure_signal6()
        use_candlestick = False
        if chart_type.lower() == 'candlestick':
            use_candlestick = self._validate_candlestick_data()

        df = self.df.tail(days).copy()
        if use_candlestick and len(df) > max_candles:
            df = self._optimize_candlestick_density(df, max_candles)

        df_original = df.copy()
        df_pos = self._convert_to_positions(df)

        if figsize is None:
            figsize = (18, 12)
        fig, ax = self._setup_figure_style(figsize, dpi)

        if use_candlestick:
            self._add_candlesticks(ax, df_original)
        else:
            ax.plot(df_pos.index, df_pos['Close'], color='black', linewidth=3,
                    label='Close Price', zorder=5, alpha=0.9)
            self._setup_date_axis(ax, df_original, df_pos.index)

        ax.plot(df_pos.index, df_pos['Alligator_Jaw'], color='blue', linewidth=3,
                label='Jaw (Blue)', alpha=0.8)
        ax.plot(df_pos.index, df_pos['Alligator_Teeth'], color='red', linewidth=3,
                label='Teeth (Red)', alpha=0.8)
        ax.plot(df_pos.index, df_pos['Alligator_Lips'], color='green', linewidth=3,
                label='Lips (Green)', alpha=0.8)

        if show_sar and 'SAR' in df_pos.columns:
            self._add_sar_indicator_positions(ax, df_pos)
        if show_moving_averages:
            self._add_moving_averages_positions(ax, df_pos)
        if 'Signal6' in df_pos.columns:
            self._add_signal_markers_positions(ax, df_pos)

        self._optimize_chart_layout_positions(ax, df_pos)
        if show_background and 'Signal6' in df_pos.columns:
            self._add_background_colors_positions(ax, df_pos)

        chart_label = "Candlestick" if use_candlestick else "Line"
        chart_title = f'{self.ticker} - Alligator Analysis ({chart_label}, Last {days} days)'
        if use_candlestick and len(self.df.tail(days)) > max_candles:
            chart_title += f' [Optimized: {len(df)} candles shown]'
        ax.set_title(chart_title, fontsize=18, fontweight='bold', pad=25)
        ax.set_ylabel('Price', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=14, fontweight='bold')

        self._setup_dual_legends(ax, show_background)
        ax.grid(True, alpha=0.4, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        plt.subplots_adjust(hspace=0.30, top=0.92, bottom=0.10, left=0.08, right=0.92)

        if save_chart:
            if filename is None:
                chart_type_for_filename = "candlestick" if use_candlestick else "line"
                filename = f"{self.ticker}_alligator_{chart_type_for_filename}_analysis.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Grafico salvato come: {filename}")

        self._print_analysis_summary(df, days)
        return fig

    def _add_background_colors(self, ax, df):
        for i in range(len(df)):
            signal = df['Signal6'].iloc[i]
            alpha = 0.15
            if 'Uptrend' in signal:
                color = 'green'
            elif 'Downtrend' in signal:
                color = 'red'
            elif 'sleep' in signal:
                color = 'gray'
            elif 'wakeup' in signal:
                color = 'lightgreen'
            else:
                continue
            self._add_safe_axvspan(ax, df.index[i], df.index[min(i + 1, len(df) - 1)], color=color, alpha=alpha)

    def _add_signal_markers(self, ax, df):
        signal_configs = {
            'Uptrend*': ('lime', '^', 'Uptrend Start'),
            'Downtrend*': ('red', 'v', 'Downtrend Start'),
            'wakeup2*': ('orange', 'o', 'Wakeup2 Start')
        }
        for signal, (color, marker, label) in signal_configs.items():
            signal_mask = df['Signal6'] == signal
            if signal_mask.any():
                ax.scatter(df.index[signal_mask], df['Close'][signal_mask],
                           color=color, marker=marker, s=120, alpha=0.9,
                           label=label, zorder=6, edgecolors='black', linewidth=1.5)

    def _add_candlesticks(self, ax, df, set_xticks: bool = False):
        from matplotlib.patches import Rectangle
        from matplotlib.lines import Line2D
        import numpy as np

        positions = np.arange(len(df))
        candle_width = 0.6

        for i, (_, row) in enumerate(df.iterrows()):
            pos = positions[i]
            o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']

            if c >= o:
                color = 'darkgreen';
                body_color = 'lightgreen';
                edge_color = 'darkgreen'
            else:
                color = 'darkred';
                body_color = 'lightcoral';
                edge_color = 'darkred'

            ax.add_line(Line2D([pos, pos], [l, h], color=color, linewidth=1.2, alpha=0.9, zorder=4))
            body_h = abs(c - o);
            body_y = min(o, c)
            if body_h > 0:
                ax.add_patch(Rectangle((pos - candle_width / 2, body_y), candle_width, body_h,
                                       facecolor=body_color, edgecolor=edge_color,
                                       linewidth=0.8, alpha=0.85, zorder=4))
            else:
                ax.add_line(Line2D([pos - candle_width / 2, pos + candle_width / 2],
                                   [c, c], color=color, linewidth=2, alpha=0.9, zorder=4))

        # ← non toccare ticks/lim a meno che non richiesto
        if set_xticks:
            self._setup_date_axis(ax, df, positions)

        # proxy invisibile per legenda
        proxy = Line2D([0], [0], color='gray', linewidth=2.5, label='Candlesticks', alpha=0.8)
        ax.add_line(proxy);
        proxy.set_visible(False)

    def _add_candlesticksv0(self, ax, df):
        from matplotlib.patches import Rectangle
        from matplotlib.lines import Line2D
        import numpy as np
        positions = np.arange(len(df))
        candle_width = 0.6
        for i, (date, row) in enumerate(df.iterrows()):
            pos = positions[i]
            open_price = row['Open']; high_price = row['High']
            low_price = row['Low']; close_price = row['Close']
            if close_price >= open_price:
                color = 'darkgreen'; body_color = 'lightgreen'; edge_color = 'darkgreen'
            else:
                color = 'darkred'; body_color = 'lightcoral'; edge_color = 'darkred'
            shadow = Line2D([pos, pos], [low_price, high_price], color=color, linewidth=1.2, alpha=0.9, zorder=4)
            ax.add_line(shadow)
            body_height = abs(close_price - open_price)
            body_bottom = min(open_price, close_price)
            if body_height > 0:
                body = Rectangle((pos - candle_width / 2, body_bottom),
                                 candle_width, body_height,
                                 facecolor=body_color, edgecolor=edge_color,
                                 linewidth=0.8, alpha=0.85, zorder=4)
                ax.add_patch(body)
            else:
                doji_line = Line2D([pos - candle_width / 2, pos + candle_width / 2],
                                   [close_price, close_price], color=color, linewidth=2, alpha=0.9, zorder=4)
                ax.add_line(doji_line)
        self._setup_date_axis(ax, df, positions)
        candlestick_proxy = Line2D([0], [0], color='gray', linewidth=2.5, label='Candlesticks', alpha=0.8)
        ax.add_line(candlestick_proxy)
        candlestick_proxy.set_visible(False)

    def _add_sar_indicator(self, ax, df):
        if 'SAR' not in df.columns:
            return
        sar_above = df['SAR'] > df['Close']
        if sar_above.any():
            ax.scatter(df.index[sar_above], df['SAR'][sar_above],
                       color='red', marker='o', s=25, alpha=0.8, label='SAR (Sell)', zorder=4)
        sar_below = df['SAR'] <= df['Close']
        if sar_below.any():
            ax.scatter(df.index[sar_below], df['SAR'][sar_below],
                       color='lime', marker='o', s=25, alpha=0.8, label='SAR (Buy)', zorder=4)

    def _add_moving_averages(self, ax, df):
        ma_columns = [col for col in df.columns if
                      col.startswith(('MA_', 'EMA_', 'SMA_')) and
                      col not in ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw']]
        ma_colors = ['purple', 'orange', 'brown', 'pink', 'cyan', 'magenta']
        ma_styles = ['-', '--', '-.', ':']
        for i, ma_col in enumerate(ma_columns):
            if ma_col in df.columns and not df[ma_col].isna().all():
                color = ma_colors[i % len(ma_colors)]
                style = ma_styles[i % len(ma_styles)]
                period = ma_col.split('_')[-1] if '_' in ma_col else ''
                label = f"{ma_col.split('_')[0]}{period}" if period else ma_col
                ax.plot(df.index, df[ma_col], color=color, linewidth=2,
                        linestyle=style, alpha=0.8, label=label, zorder=2)

    def _setup_dual_legends(self, ax, show_background):
        handles, labels = ax.get_legend_handles_labels()
        main_handles = []
        main_labels = []
        priority_items = ['Close Price', 'Candlesticks', 'Jaw (Blue)', 'Teeth (Red)', 'Lips (Green)',
                          'Uptrend Start', 'Downtrend Start', 'Wakeup2 Start']
        for priority in priority_items:
            for i, label in enumerate(labels):
                if label == priority:
                    main_handles.append(handles[i])
                    main_labels.append(labels[i])
                    break
        for i, label in enumerate(labels):
            if label not in main_labels:
                main_handles.append(handles[i])
                main_labels.append(labels[i])
        ncol = 3 if len(main_labels) > 12 else 2 if len(main_labels) > 6 else 1
        legend1 = ax.legend(main_handles, main_labels, loc='upper left', fontsize=10,
                            framealpha=0.95, fancybox=True, shadow=True, ncol=ncol,
                            columnspacing=1.2, handlelength=2)
        if show_background:
            background_legend = [
                Patch(facecolor='green', alpha=0.5, label='🟢 UPTREND'),
                Patch(facecolor='red', alpha=0.5, label='🔴 DOWNTREND'),
                Patch(facecolor='lightgreen', alpha=0.5, label='🟢 WAKEUP'),
                Patch(facecolor='gray', alpha=0.5, label='⚪ SLEEP')
            ]
            legend2 = ax.legend(background_legend, [patch.get_label() for patch in background_legend],
                                bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=11,
                                framealpha=0.95, fancybox=True, shadow=True,
                                title="Background Colors", title_fontsize=12)
            ax.add_artist(legend1)

    def _print_analysis_summary(self, df, days):
        if 'Signal6' not in df.columns:
            return
        latest_signal = df['Signal6'].iloc[-1]
        signal_counts = df['Signal6'].value_counts()
        print(f"\n{'=' * 50}")
        print(f"        ALLIGATOR ANALYSIS SUMMARY")
        print(f"{'=' * 50}")
        print(f"Ticker: {self.ticker}")
        print(f"Period analyzed: {days} days")
        print(f"Current Signal6: {latest_signal}")
        if self.ta:
            print(f"Description: {self.ta.get_signal6_description(latest_signal)}")
        print(f"Current Price: {df['Close'].iloc[-1]:.2f}")
        print(f"\nTop 3 Signal6 frequencies:")
        for signal, count in signal_counts.head(3).items():
            percentage = (count / len(df)) * 100
            print(f"  {signal}: {count} days ({percentage:.1f}%)")
        print(f"{'=' * 50}")

    def get_chart_config(self):
        config = {
            'has_data': self.df is not None,
            'has_alligator': self._has_alligator_indicators(),
            'has_signal6': 'Signal6' in self.df.columns if self.df is not None else False,
            'has_sar': 'SAR' in self.df.columns if self.df is not None else False,
            'has_ohlc': self._has_ohlc_data(),
            'ticker': self.ticker,
            'data_length': len(self.df) if self.df is not None else 0
        }
        if self.df is not None:
            ma_columns = [col for col in self.df.columns if
                          col.startswith(('MA_', 'EMA_', 'SMA_')) and
                          col not in ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw']]
            config['available_moving_averages'] = ma_columns
            config['has_moving_averages'] = len(ma_columns) > 0
        else:
            config['available_moving_averages'] = []
            config['has_moving_averages'] = False
        return config

    def _has_ohlc_data(self):
        if self.df is None:
            return False
        required_cols = ['Open', 'High', 'Low', 'Close']
        return all(col in self.df.columns for col in required_cols)

    def _has_alligator_indicators(self):
        if self.df is None:
            return False
        required_cols = ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw']
        return all(col in self.df.columns for col in required_cols)

    # ======= DASHBOARD MULTI-PANNELLO (compatibile Python < 3.10) =======

    # --- dentro AlligatorChartManager -------------------------------------------

    def _add_volume_bars_positions(self, ax, df_pos, ma_periods=None, width=0.8):
        """
        Barre dei volumi + una o più medie mobili dei volumi.
          - ma_periods può essere: None | int | list/tuple di int, es. [10, 5]
        """
        if 'Volume' not in df_pos.columns:
            ax.text(0.02, 0.7, "Volume non disponibile", transform=ax.transAxes)
            return

        # barre verdi/rosse
        up = df_pos['Close'] >= df_pos['Close'].shift(1)
        down = ~up
        self._add_safe_bar(ax, df_pos.index[up], df_pos['Volume'][up], width=width, alpha=0.75,
                           color='green', label='Vol Up', zorder=3)
        self._add_safe_bar(ax, df_pos.index[down], df_pos['Volume'][down], width=width, alpha=0.75,
                           color='red', label='Vol Down', zorder=3)

        # normalizza ma_periods -> lista
        if ma_periods is None:
            ma_list = []
        elif isinstance(ma_periods, (list, tuple)):
            ma_list = [int(p) for p in ma_periods if int(p) > 1]
        else:  # int singolo
            p = int(ma_periods)
            ma_list = [p] if p > 1 else []

        # disegna ciascuna MA
        for p in ma_list:
            vma = df_pos['Volume'].rolling(p, min_periods=1).mean()
            ax.plot(df_pos.index, vma, linewidth=1.6, label=f'Vol MA{p}', zorder=4)

        ax.set_ylabel('Volume')
        ax.legend(loc='upper left', framealpha=0.9)

    def _add_volume_bars_positionsv0(self, ax, df_pos, ma_period=None, width=0.8):
        """
        Barre dei volumi colorate:
          - verde se Close >= Close.shift(1)
          - rosso altrimenti
        Opzionale: media mobile dei volumi (ma_period).
        """
        if 'Volume' not in df_pos.columns:
            ax.text(0.02, 0.7, "Volume non disponibile", transform=ax.transAxes)
            return

        up = df_pos['Close'] >= df_pos['Close'].shift(1)
        down = ~up

        self._add_safe_bar(ax, df_pos.index[up], df_pos['Volume'][up], width=width, alpha=0.75,
                           color='green', label='Vol Up', zorder=3)
        self._add_safe_bar(ax, df_pos.index[down], df_pos['Volume'][down], width=width, alpha=0.75,
                           color='red', label='Vol Down', zorder=3)

        if ma_period and ma_period > 1:
            vma = df_pos['Volume'].rolling(int(ma_period), min_periods=1).mean()
            ax.plot(df_pos.index, vma, linewidth=1.6, label=f'Vol MA{int(ma_period)}', zorder=4)

        ax.set_ylabel('Volume')
        ax.legend(loc='upper left', framealpha=0.9)

    def _draw_mcs_guides(self, ax, df_pos, band=30, conf_hi=0.6):
        """
        Guide visive per MCS:
          - linee 0 / ±band
          - zone ad alta confidenza (riempimenti)
          - marker per cross di MCS_Smoothed attraverso 0 (↑/↓)
        """
        import numpy as np
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D

        if 'MCS_Smoothed' not in df_pos.columns:
            return []

        x = df_pos.index
        mcs = df_pos.get('MCS', np.nan)
        sm = df_pos['MCS_Smoothed']
        conf = df_pos.get('MCS_Conf', np.nan)

        # Linee guida
        self._add_safe_axhline(ax, 0, linewidth=1.0, linestyle='--', alpha=0.7)
        self._add_safe_axhline(ax, band, linewidth=0.8, linestyle=':', alpha=0.6)
        self._add_safe_axhline(ax, -band, linewidth=0.8, linestyle=':', alpha=0.6)

        # Zone alta confidenza (confidence > conf_hi e smoltre soglia)
        hi_bull = (conf > conf_hi) & (sm > band)
        hi_bear = (conf > conf_hi) & (sm < -band)
        ax.fill_between(x, band, sm, where=hi_bull, color='green', alpha=0.15, interpolate=True)
        ax.fill_between(x, -band, sm, where=hi_bear, color='red', alpha=0.15, interpolate=True)

        # Cross 0 di MCS_Smoothed
        cross_up = (sm.shift(1) <= 0) & (sm > 0)
        cross_dn = (sm.shift(1) >= 0) & (sm < 0)
        ax.scatter(x[cross_up], sm[cross_up], marker='^', s=70, color='green',
                   edgecolors='black', linewidth=0.8, zorder=5)
        ax.scatter(x[cross_dn], sm[cross_dn], marker='v', s=70, color='red',
                   edgecolors='black', linewidth=0.8, zorder=5)

        # Handle “didattici” per la legenda (zone e marker)
        handles = [
            Line2D([], [], marker='^', linestyle='None', color='green', markersize=8, label='Cross ↑ (Bullish)'),
            Line2D([], [], marker='v', linestyle='None', color='red', markersize=8, label='Cross ↓ (Bearish)'),
            Patch(facecolor='green', alpha=0.15, label=f'Zona High-Conf >{conf_hi:.0%} (Bull)'),
            Patch(facecolor='red', alpha=0.15, label=f'Zona High-Conf >{conf_hi:.0%} (Bear)'),
        ]
        return handles


    # --- fine inserimento --------------------------------------------------------

    def _add_signal6_state_labels_positions(self, ax, df_pos, min_gap: int = 10):
        """
        Evidenzia i cambi di stato di Signal6 con marker compatti.

        I testi completi (in particolare Downtrend_revS3Sig+++) occupavano diverse
        candele e rendevano difficile leggere prezzi e indicatori. I marker sono
        quindi posizionati appena fuori dal range della candela, senza riquadri o
        frecce; il significato dei colori resta disponibile nella legenda.
        """
        import numpy as np
        if 'Signal6' not in df_pos.columns:
            return

        s6 = df_pos['Signal6'].fillna('').astype(str)
        # posizioni in cui cambia stato vs barra precedente
        change_mask = s6.ne(s6.shift(1))
        change_idx = np.flatnonzero(change_mask.values)

        high_ref = df_pos['High'] if 'High' in df_pos.columns else df_pos['Close']
        low_ref = df_pos['Low'] if 'Low' in df_pos.columns else df_pos['Close']
        y_min = np.nanmin(low_ref.values)
        y_max = np.nanmax(high_ref.values)
        y_rng = max(1e-9, y_max - y_min)
        marker_off = 0.015 * y_rng

        last_plotted = -10 ** 9  # per evitare label troppo ravvicinati

        def _style(lbl: str):
            lo = lbl.lower()
            if 'uptrend' in lo:   return ('green', '^', 'top')  # marker, label sopra
            if 'downtrend' in lo: return ('red', 'v', 'bottom')  # marker, label sotto
            if 'wakeup' in lo:    return ('orange', 'o', 'top')
            if 'sleep' in lo:     return ('gray', 'o', 'bottom')
            return ('tab:blue', 'o', 'top')

        for i in change_idx:
            if i - last_plotted < min_gap:  # anti-affollamento
                continue

            lbl_raw = s6.iat[i]
            if not lbl_raw:
                continue

            # pulizia minima (mantieni eventuali "--", rimuovi eventuali asterischi)
            lbl = lbl_raw.replace('*', '')
            color, marker, where = _style(lbl)

            x = int(df_pos.index[i])
            # Stati rialzisti sotto la candela, ribassisti sopra: in questo modo
            # il simbolo segnala il cambio senza coprire corpo, shadow o linee.
            if where == 'top':
                y = float(low_ref.iat[i]) - marker_off
            else:
                y = float(high_ref.iat[i]) + marker_off

            ax.scatter(x, y, color=color, marker=marker, s=58,
                       edgecolors='black', linewidth=0.7, zorder=6)
            last_plotted = i

    def stampa_mcs_plain(ta, show_triggers: bool = True):
        """Riepilogo MCS/Smooth/Conf + indicazione operativa in plain text (st.markdown)."""
        import pandas as pd
        import numpy as np
        import streamlit as st

        df = ta.dataframe.copy()
        # Se manca MCS, prova a calcolarlo (se hai già calcolato il MACD)
        need = any(c not in df.columns for c in ['MCS', 'MCS_Smoothed', 'MCS_Conf'])
        if need and all(c in df.columns for c in ['MACD', 'MACD_Signal', 'MACD_Hist']):
            try:
                ta._calculate_mcs(L=26, k=1.8, beta=0.2, smooth=5)
                df = ta.dataframe
            except Exception:
                pass

        last = df.iloc[-1]

        def get(col):
            return float(last[col]) if col in df.columns and pd.notna(last[col]) else np.nan

        mcs = get('MCS')
        mcss = get('MCS_Smoothed')
        conf = get('MCS_Conf')
        macd = get('MACD')
        sig = get('MACD_Signal')
        hist = get('MACD_Hist')

        # ---- utilità grafica "leggera" come nel riepilogo pct ----
        def color_num(x, fmt='{:+.0f}'):
            import math
            if x is None or np.isnan(x): return "<span style='color:#999'>n/a</span>"
            c = "green" if x >= 0 else "red"
            return f"<span style='color:{c};font-weight:700'>" + fmt.format(x) + "</span>"

        def color_conf(c):
            if np.isnan(c): return "<span style='color:#999'>n/a</span>"
            col = "#137333" if c >= 0.80 else ("#8a6d3b" if c >= 0.60 else "#a50e0e")
            return f"<span style='color:{col};font-weight:700'>{c:.2f}</span>"

        def fascia(x):
            if np.isnan(x): return "n/a"
            if x >= 80:   return "BULL EXTREME"
            if x >= 60:   return "BULL STRONG"
            if x >= 40:   return "BULL CONFIRMED"
            if x >= 20:   return "BULL IMPROVING"
            if x >= 0:    return "BULL WEAK"
            if x >= -20:  return "BEAR WEAK"
            if x >= -40:  return "BEAR IMPROVING"
            if x >= -60:  return "BEAR CONFIRMED"
            if x >= -80:  return "BEAR STRONG"
            return "BEAR EXTREME"

        band = fascia(mcss)

        # ---- indicazione operativa sintetica ----
        def operativita(m, c, macd, sig, hist):
            if np.isnan(m): return "Dati insufficienti."
            bull = m >= 0
            macd_ok = (not np.isnan(macd)) and (not np.isnan(sig)) and (macd > sig)
            hist_pos = (not np.isnan(hist)) and (hist >= 0)

            if m >= 80 and c >= 0.80:
                return "Trend molto forte: mantieni/lascia correre; TP parziali e trailing. Evita nuove entrate tardive, meglio su pullback."
            if m >= 60 and c >= 0.60:
                return "Forte: mantieni; ingressi su pullback. Evita vendite controtrend."
            if m >= 40:
                return f"Trend sano: ok a mantenere/aggiungere se conferme MACD ({'ok' if macd_ok else 'no'}) e Hist ({'ok' if hist_pos else 'no'})."
            if m >= 20:
                return "Costruzione: ingressi selettivi solo con cross >0 recente e Conf ≥ 0.60."
            if 0 <= m < 20:
                return "Incipiente: tieni in watchlist finché supera 20 con Conf ≥ 0.60."
            # lato short
            if m <= -80 and c >= 0.80:
                return "Ribasso molto forte: mantieni short; TP parziali/trailing. Evita comprare il rimbalzo."
            if m <= -60 and c >= 0.60:
                return "Ribasso forte: short su rimbalzi; evita long controtrend."
            if m <= -40:
                return "Ribasso confermato: possibili short con conferme (MACD<Signal, Hist<0)."
            if m <= -20:
                return "Ribasso in costruzione: attendi conferme o break sotto 0 con Conf ≥ 0.60."
            return "Debolezza iniziale: watchlist finché scende sotto -20."

        hint = operativita(mcss, conf, macd, sig, hist)

        # ---- render testo “plain” ----
        html = f"""
        <div style="margin-top:6px;margin-bottom:2px;font-size:15px;">
          <b>MCS:</b> {color_num(mcs)} &nbsp;|&nbsp;
          <b>Smooth:</b> {color_num(mcss)} &nbsp;|&nbsp;
          <b>Conf:</b> {color_conf(conf)} &nbsp;|&nbsp;
          <b>Fascia:</b> <span style="font-weight:700">{band}</span>
        </div>
        <div style="font-size:14px;">
          <b>Indicazioni operative:</b> {hint}
        </div>
        """
        if show_triggers:
            html += """
            <div style="font-size:13px;opacity:0.95;margin-top:4px;">
              <b>Trigger pratici:</b>
              1) cross di <i>MCS_Smoothed</i> sopra/sotto 0 ⇒ buy/sell di base;
              2) superamento ±30 ⇒ allerta momentum;
              3) conferma solo con <i>Conf</i> ≥ 0.60 (meglio ≥ 0.80);
              4) divergenze MCS vs prezzo ⇒ possibili inversioni.
            </div>
            """
        st.markdown(html, unsafe_allow_html=True)

    def plot_ta_dashboard(
            self,
            days=120,
            chart_type="line",
            show_signal6_bg=True,
            show_sar=True,
            show_mas=True,
            show_mcs=True,
            show_rsi=True,
            show_stoch=True,
            show_willr=True,
            auto_compute_missing=True,
            max_candles=220,
            figsize=(16, 12),
            dpi=120,
            save=False,
            filename=None,
            height_ratios=None,
            show_volume=True,
            volume_ma=(10, 5),
            show_adx=True,
            show_atr_band: bool = True,  # lasciato per compatibilità (ma NON plotta ATR Upper/Lower)
            show_chandelier: bool = True,  # lasciato per compatibilità (ma NON plotta CE Short)
            show_atr_pct_panel: bool = False,
            show_tech_score: bool = True,
            willr_shifted: bool = False,
    ):
        """
        Dashboard multi-pannello (ordine nuovo):
          1) Price + Alligator (+SAR/MAs) con background Signal6
          2) Volume (+ MA opzionale)
          3) Oscillatori (RSI / Stoch / Williams%R)
          4) MACD
          5) MCS
          6) Technical Score
          7) ADX + DI
          8) ATR% (opzionale)
        """
        import matplotlib.pyplot as plt
        import numpy as np

        # ---- 0) Sorgente dati ----
        if self.df is None and self.ta is not None:
            self.df = self.ta.dataframe.copy()
            self.ticker = getattr(self.ta, "ticker", self.ticker)
        if self.df is None or len(self.df) == 0:
            raise ValueError("Nessun dato. Usa set_data() o passa TechnicalAnalyzer.")

        # ---- 1) Auto-compute indicatori mancanti (se possibile) ----
        if auto_compute_missing and self.ta is not None:
            need_alligator = any(
                c not in self.df.columns for c in ['Alligator_Jaw', 'Alligator_Teeth', 'Alligator_Lips'])
            need_macd = any(c not in self.df.columns for c in ['MACD', 'MACD_Signal', 'MACD_Hist'])
            need_rsi = show_rsi and 'RSI' not in self.df.columns
            need_stoch = show_stoch and not all(c in self.df.columns for c in ['Stoch_K', 'Stoch_D'])
            need_willr = show_willr and 'Williams_R' not in self.df.columns
            need_sar = show_sar and 'SAR' not in self.df.columns
            need_mas = show_mas and not any(col.startswith(('EMA_', 'SMA_', 'MA_')) for col in self.df.columns)
            need_signal6 = show_signal6_bg and 'Signal6' not in self.df.columns
            need_adx = show_adx and not all(c in self.df.columns for c in ['ADX', 'PLUS_DI', 'MINUS_DI'])
            need_atr = (show_atr_pct_panel or show_chandelier or show_atr_band) and ('ATR' not in self.df.columns)

            indicators = []
            if need_macd: indicators.append('MACD')
            if need_alligator: indicators.append('ALLIGATOR')
            if need_rsi: indicators.append('RSI')
            if need_stoch: indicators.append('STOCH')
            if need_willr: indicators.append('WILLR')
            if need_sar: indicators.append('SAR')
            if need_mas: indicators.extend(['EMA_30', 'EMA_50'])
            if need_adx: indicators.append('ADX')
            if need_atr: indicators.append('ATR')

            if indicators:
                self.ta.calculate_TA_Indicators(",".join(sorted(set(indicators))))
                self.df = self.ta.dataframe.copy()

            if need_signal6 and hasattr(self.ta, 'calculate_alligator_signal6'):
                self.ta.calculate_alligator_signal6()
                self.df = self.ta.dataframe.copy()

            need_ts = show_tech_score and ("TECH_SCORE" not in self.df.columns or self.df["TECH_SCORE"].isna().all())
            if need_ts and hasattr(self.ta, "calculate_technical_score"):
                try:
                    self.ta.calculate_technical_score()
                    self.df = self.ta.dataframe.copy()
                except Exception:
                    pass

        # ---- 2) Finestra temporale ----
        df = self.df.tail(days).copy()
        df0 = df.copy()
        use_candle = (chart_type.lower() == 'candlestick') and self._validate_candlestick_data()
        if use_candle and len(df) > max_candles:
            df = self._optimize_candlestick_density(df, max_candles)
            df0 = df.copy()
        df_pos = self._convert_to_positions(df)

        # ---- 3) Setup figura e layout pannelli ----
        have_osc_panel = (show_rsi or show_stoch or show_willr)

        n_panels = 1
        if show_volume: n_panels += 1
        if have_osc_panel: n_panels += 1
        n_panels += 1  # MACD
        if show_mcs: n_panels += 1
        if show_tech_score: n_panels += 1
        if show_adx: n_panels += 1
        if show_atr_pct_panel: n_panels += 1

        default_ratios = [4.5]
        if show_volume: default_ratios.append(1.8)
        if have_osc_panel: default_ratios.append(2.4)
        default_ratios.append(2.8)  # MACD
        if show_mcs: default_ratios.append(2.8)
        if show_tech_score: default_ratios.append(2.2)
        if show_adx: default_ratios.append(2.4)
        if show_atr_pct_panel: default_ratios.append(1.6)

        if height_ratios is None:
            ratios = default_ratios
        else:
            ratios = list(height_ratios)
            if len(ratios) < n_panels:
                last = ratios[-1] if ratios else 2.0
                while len(ratios) < n_panels:
                    ratios.append(last)
            elif len(ratios) > n_panels:
                ratios = ratios[:n_panels]

        plt.style.use('default')
        plt.rcParams.update({
            'axes.grid': True, 'grid.alpha': 0.3, 'axes.axisbelow': True,
            'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 13, 'legend.fontsize': 9
        })
        fig, axs = plt.subplots(
            n_panels, 1, figsize=figsize, dpi=dpi, sharex=True,
            gridspec_kw={'height_ratios': ratios}
        )

        axes = list(axs) if isinstance(axs, (list, np.ndarray)) else [axs]
        idx_ax = 0

        ax_price = axes[idx_ax];
        idx_ax += 1
        ax_vol = None
        if show_volume:
            ax_vol = axes[idx_ax];
            idx_ax += 1
        ax_osc = None
        if have_osc_panel:
            ax_osc = axes[idx_ax];
            idx_ax += 1
        ax_macd = axes[idx_ax];
        idx_ax += 1
        ax_mcs = None
        if show_mcs:
            ax_mcs = axes[idx_ax];
            idx_ax += 1
        ax_ts = None
        if show_tech_score:
            ax_ts = axes[idx_ax];
            idx_ax += 1
        ax_adx = None
        if show_adx:
            ax_adx = axes[idx_ax];
            idx_ax += 1
        ax_atr_pct = None
        if show_atr_pct_panel:
            ax_atr_pct = axes[idx_ax]

        # ===== 1) PREZZO + ALLIGATOR =====
        if use_candle:
            self._add_candlesticks(ax_price, df0)
        else:
            ax_price.plot(df_pos.index, df_pos['Close'], linewidth=2.2, label='Close Price', zorder=5)

        for col, color, lbl in [
            ('Alligator_Jaw', 'blue', 'Jaw (Blue)'),
            ('Alligator_Teeth', 'red', 'Teeth (Red)'),
            ('Alligator_Lips', 'green', 'Lips (Green)')
        ]:
            if col in df_pos.columns and not df_pos[col].isna().all():
                ax_price.plot(df_pos.index, df_pos[col], color=color, linewidth=2.2, alpha=0.8, label=lbl, zorder=3)

        if show_sar:
            self._add_sar_indicator_positions(ax_price, df_pos)
        if show_mas:
            self._add_moving_averages_positions(ax_price, df_pos)

        if 'Signal6' in df_pos.columns:
            self._add_signal_markers_positions(ax_price, df_pos)
            self._add_signal6_state_labels_positions(ax_price, df_pos, min_gap=10)
            ax_price.text(
                0.985, 0.93, f"S6: {str(df_pos['Signal6'].iloc[-1])}",
                transform=ax_price.transAxes, ha='right', va='top',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.35", fc="lightyellow", alpha=0.85, ec='gray')
            )

        # ✅ ATR Upper/Lower: NON plottati (rimossi come richiesto)

        # ✅ Chandelier Exit: plotta SOLO CE Long (CE Short rimosso)
        if show_chandelier and ('CE_Long' in df_pos.columns) and (not df_pos['CE_Long'].isna().all()):
            ax_price.plot(df_pos.index, df_pos['CE_Long'], linewidth=1.2, alpha=0.9, label='CE Long', zorder=2)
            try:
                self._add_safe_axhline(ax_price, float(df_pos['CE_Long'].iloc[-1]), linestyle=':', linewidth=0.8, alpha=0.5)
            except Exception:
                pass

        # --- SL1 / SL2 / Pullback zone (overlay trading) ---
        phase = ""
        if "Market_Phase" in df_pos.columns and not df_pos["Market_Phase"].isna().all():
            phase = str(df_pos["Market_Phase"].iloc[-1]).strip().upper()

        # 🔧 FIX: riconosce anche PULLBACK2 / PULLBACK_* ecc.
        is_pullback = phase.startswith("PULLBACK")

        # Se pullback: SOLO zona (no SL1/SL2) + linee pb_low/pb_high (gestite in _add_trade_levels)
        self._add_trade_levels(
            ax_price,
            df_pos,
            show_sl1=not is_pullback,
            show_sl2=not is_pullback,
            show_pullback=is_pullback,
            sl1_col="Trend_Stop_Level",
            sl2_col="CE_Long",
            pb_low_col="Pullback_Entry_Zone_Low",
            pb_high_col="Pullback_Entry_Zone_High",
            pb_level_col="Pullback_Entry_Level",
            pb_stop_col="Pullback_Stop_Level",
        )

        self._optimize_chart_layout_positions(ax_price, df_pos)
        if show_signal6_bg and 'Signal6' in df_pos.columns:
            self._add_background_colors_positions(ax_price, df_pos)
        ax_price.set_ylabel('Price')
        title1 = f"{self.ticker or ''} — Price & Alligator (last {len(df)} bars)"
        if use_candle and len(self.df.tail(days)) > max_candles:
            title1 += f" [optimized to {len(df)} candles]"
        ax_price.set_title(title1)
        ax_price.legend(loc='upper left', ncol=2, framealpha=0.9)

        # Draw 1D, 5D, 10D, 30D percentage changes
        pct_1 = None
        pct_5 = None
        pct_10 = None
        pct_30 = None
        if self.df is not None and 'Close' in self.df.columns and len(self.df) > 0:
            closes = self.df['Close'].dropna().values
            n_closes = len(closes)
            if n_closes >= 2:
                pct_1 = (closes[-1] / closes[-2] - 1.0) * 100.0
            if n_closes >= 6:
                pct_5 = (closes[-1] / closes[-6] - 1.0) * 100.0
            if n_closes >= 11:
                pct_10 = (closes[-1] / closes[-11] - 1.0) * 100.0
            if n_closes >= 31:
                pct_30 = (closes[-1] / closes[-31] - 1.0) * 100.0

        variations = []
        if pct_1 is not None:
            variations.append(("1D: ", pct_1))
        if pct_5 is not None:
            variations.append(("5D: ", pct_5))
        if pct_10 is not None:
            variations.append(("10D: ", pct_10))
        if pct_30 is not None:
            variations.append(("30D: ", pct_30))

        if variations:
            from matplotlib.offsetbox import HPacker, TextArea, AnnotationBbox
            children = []
            for label, val in variations:
                children.append(TextArea(label, textprops=dict(color="black", fontsize=9)))
                val_str = f"{'+' if val > 0 else ''}{val:.2f}%  "
                val_color = "green" if val > 0 else ("red" if val < 0 else "gray")
                children.append(TextArea(val_str, textprops=dict(color=val_color, fontweight="bold", fontsize=9)))

            packer = HPacker(children=children, align="center", pad=3, sep=2)
            ab = AnnotationBbox(
                packer,
                # Keep the performance summary in the white header area,
                # outside the price plot, so it never covers candles/lines.
                xy=(0.5, 1.12),
                xycoords='axes fraction',
                box_alignment=(0.5, 0.5),
                bboxprops=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.9, ec="#d0d0d0"),
                frameon=True,
                annotation_clip=False,
                zorder=10
            )
            ax_price.add_artist(ab)

        # ===== 2) VOLUMI =====
        if show_volume and ax_vol is not None:
            if 'Volume' in df_pos.columns and not df_pos['Volume'].isna().all():
                self._add_volume_bars_positions(ax_vol, df_pos, ma_periods=volume_ma, width=0.8)
                ax_vol.set_title("Volume")
            else:
                ax_vol.text(0.02, 0.7, "Volume non disponibile", transform=ax_vol.transAxes)

        # ===== 3) OSCILLATORI =====
        if have_osc_panel and ax_osc is not None:
            have_any = False
            ax_willr = None

            if show_rsi and 'RSI' in df_pos.columns and not df_pos['RSI'].isna().all():
                have_any = True
                ax_osc.plot(df_pos.index, df_pos['RSI'], linewidth=1.6, label='RSI')
                self._add_safe_axhline(ax_osc, 70, linewidth=1.0, linestyle=':', alpha=0.7)
                self._add_safe_axhline(ax_osc, 50, linewidth=0.9, linestyle=':', alpha=0.6)
                self._add_safe_axhline(ax_osc, 30, linewidth=1.0, linestyle=':', alpha=0.7)

            if show_stoch and all(c in df_pos.columns for c in ['Stoch_K', 'Stoch_D']):
                if (not df_pos['Stoch_K'].isna().all()) or (not df_pos['Stoch_D'].isna().all()):
                    have_any = True
                    ax_osc.plot(df_pos.index, df_pos['Stoch_K'], linewidth=1.3, label='Stoch K')
                    ax_osc.plot(df_pos.index, df_pos['Stoch_D'], linewidth=1.3, label='Stoch D')
                    self._add_safe_axhline(ax_osc, 80, linewidth=0.8, linestyle=':', alpha=0.7)
                    self._add_safe_axhline(ax_osc, 20, linewidth=0.8, linestyle=':', alpha=0.7)

            if show_willr and 'Williams_R' in df_pos.columns and not df_pos['Williams_R'].isna().all():
                have_any = True
                if willr_shifted:
                    # Plot shifted Williams %R (0..100) on the same main axis
                    ax_osc.plot(df_pos.index, df_pos['Williams_R'] + 100, linewidth=1.2,
                                color='#4682B4', label='Williams %R (shifted)')
                else:
                    # Plot native Williams %R (-100..0) on secondary y-axis
                    ax_willr = ax_osc.twinx()
                    ax_willr.plot(df_pos.index, df_pos['Williams_R'], linewidth=1.2, color='#38bdf8', label='Williams %R')
                    ax_willr.set_ylim(-105, 5)
                    self._add_safe_axhline(ax_willr, -80, color='#38bdf8', linewidth=0.8, linestyle=':', alpha=0.5)
                    self._add_safe_axhline(ax_willr, -20, color='#38bdf8', linewidth=0.8, linestyle=':', alpha=0.5)
                    ax_willr.set_ylabel('Williams %R (-100..0)', color='#38bdf8')
                    ax_willr.tick_params(axis='y', labelcolor='#38bdf8')

            if have_any:
                ax_osc.set_ylim(-5, 105)
                ax_osc.set_ylabel('Osc (0..100)')
                ax_osc.set_title('RSI / Stoch / Williams%R')
                if ax_willr is not None:
                    lines1, labels1 = ax_osc.get_legend_handles_labels()
                    lines2, labels2 = ax_willr.get_legend_handles_labels()
                    ax_osc.legend(lines1 + lines2, labels1 + labels2, loc='upper left', ncol=2, framealpha=0.9)
                else:
                    ax_osc.legend(loc='upper left', ncol=2, framealpha=0.9)
            else:
                ax_osc.text(0.02, 0.7, "Oscillatori non disponibili", transform=ax_osc.transAxes)

        # ===== 4) MACD =====
        if all(c in df_pos.columns for c in ['MACD', 'MACD_Signal', 'MACD_Hist']):
            idx_x, macd, sig, hist = df_pos.index, df_pos['MACD'], df_pos['MACD_Signal'], df_pos['MACD_Hist']
            self._add_safe_axhline(ax_macd, 0, linewidth=1, linestyle='--', alpha=0.6, zorder=0)
            ax_macd.plot(idx_x, macd, linewidth=1.8, label='MACD', zorder=2)
            ax_macd.plot(idx_x, sig, linewidth=1.8, label='MACD Signal', zorder=2)
            try:
                self._add_safe_bar(ax_macd, idx_x, hist, width=0.8, alpha=0.7, color='green', label='MACD Histogram', zorder=1)
            except Exception:
                self._add_safe_bar(ax_macd, idx_x, hist, width=0.8, alpha=0.7, color='green', label='MACD Histogram', zorder=1)
            ax_macd.set_ylabel('MACD')
            ax_macd.set_title('MACD / Signal / Histogram')
            ax_macd.legend(loc='upper left', framealpha=0.9)
        else:
            ax_macd.text(0.02, 0.7, "MACD non disponibile", transform=ax_macd.transAxes)

        # ===== 5) MCS =====
        if show_mcs and ax_mcs is not None:
            if all(c in df_pos.columns for c in ['MCS', 'MCS_Smoothed']):
                idx_x = df_pos.index
                self._add_safe_axhline(ax_mcs, 0, linewidth=1, linestyle='--', alpha=0.6)
                ax_mcs.plot(idx_x, df_pos['MCS'], linewidth=1.6, label='MCS')
                ax_mcs.plot(idx_x, df_pos['MCS_Smoothed'], linewidth=2.0, label='MCS Smoothed')
                ax_mcs.set_title('MCS')
                ax_mcs.legend(loc='upper left', framealpha=0.9)
            else:
                ax_mcs.text(0.02, 0.7, "MCS non disponibile", transform=ax_mcs.transAxes)

        # ===== 6) TECH SCORE =====
        if show_tech_score and ax_ts is not None:
            ok_ts = self._add_techscore_panel_positions(ax_ts, df_pos)
            if not ok_ts:
                ax_ts.text(0.02, 0.7, "TECH_SCORE non disponibile", transform=ax_ts.transAxes)

        # ===== 7) ADX =====
        if show_adx and ax_adx is not None:
            ok_adx = self._add_adx_panel_positions(ax_adx, df_pos)
            if not ok_adx:
                ax_adx.text(0.02, 0.7, "ADX/DI non disponibili", transform=ax_adx.transAxes)

        # ===== 8) ATR% =====
        if show_atr_pct_panel and (ax_atr_pct is not None):
            if 'ATR_PCT' in df_pos.columns and not df_pos['ATR_PCT'].isna().all():
                ax_atr_pct.plot(df_pos.index, df_pos['ATR_PCT'], linewidth=1.2, label='ATR %')
                self._add_safe_axhline(ax_atr_pct, 1.0, linestyle=':', linewidth=0.8, alpha=0.6)
                self._add_safe_axhline(ax_atr_pct, 2.0, linestyle=':', linewidth=0.8, alpha=0.6)
                ax_atr_pct.set_ylabel('ATR %')
                ax_atr_pct.set_title('ATR / Price (%)')
                ax_atr_pct.legend(loc='upper left', framealpha=0.9)
            else:
                ax_atr_pct.text(0.02, 0.7, "ATR% non disponibile", transform=ax_atr_pct.transAxes)

        # ---- X axis ----
        bottom_ax = axes[-1]
        self._setup_date_axis(bottom_ax, df0, df_pos.index)

        for ax in axes:
            ax.grid(True, alpha=0.35)

        name = getattr(self, "tickerName", None) or self.fetch_ticker_name()
        fig.suptitle(f"{name} ({self.ticker})", fontsize=14, fontweight="bold")
        plt.subplots_adjust(hspace=0.35, top=0.93, bottom=0.08, left=0.08, right=0.92)

        if save:
            if not filename:
                base = (self.ticker or "chart").replace("/", "_")
                filename = f"{base}_dashboard.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Grafico salvato: {filename}")

        return fig



    # Alias per compatibilità con il tuo script di test
    def plot_indicator_dashboard(self, *args, **kwargs):
        """Wrapper che richiama plot_ta_dashboard per retrocompatibilità."""
        return self.plot_ta_dashboard(*args, **kwargs)
