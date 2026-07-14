# ts_web_editor.py

import os
import json
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Importa dal tuo progetto
from backTestingvBATCHv0FileJSON_MULTILOGIC import (
    calculateTAIndicators,
    calculateScoring,
    load_trading_systems,
    PRECOMPUTE_FUNCS,
    _make_block_series,
    _resolve_logics,
)
from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManagerBt import AlligatorChartManager

# Path di base (stessa cartella di questo file)
ROOT = os.path.dirname(os.path.abspath(__file__))
SYSTEMS_DIR = os.path.join(ROOT, "tradingSystems")


# ========== Helper per salvare/caricare JSON ==================================

def list_system_json_files() -> List[str]:
    """Elenca i file .json nella cartella tradingSystems."""
    if not os.path.isdir(SYSTEMS_DIR):
        return []
    return [f for f in os.listdir(SYSTEMS_DIR) if f.lower().endswith(".json")]


def load_systems(file_name: str) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """Wrappa load_trading_systems usando SYSTEMS_DIR."""
    json_path = os.path.join(SYSTEMS_DIR, file_name)
    return load_trading_systems(json_path), json_path


def save_systems(json_path: str, systems_cfg: Dict[str, Dict[str, Any]]) -> None:
    """Salva il dizionario completo dei sistemi sul file JSON."""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(systems_cfg, f, indent=2, ensure_ascii=False)


# ========== Indicator columns per builder =====================================

@st.cache_data(show_spinner=False)
def get_indicator_columns_for_ui(ticker: str, period: str) -> List[str]:
    """
    Scarica dati + indicatori e ritorna le colonne disponibili per il builder.
    Cache per evitare download ripetuti.
    """
    ta = TechnicalAnalyzer(ticker, period=period)
    ta = calculateTAIndicators(ta)
    ta = calculateScoring(ta)
    cols = list(ta.dataframe.columns)

    # opzionale: filtra solo indicatori (escludi OHLCV base)
    base_cols = {
        "Open", "High", "Low", "Close", "Adj Close", "Volume",
        "Date", "Ticker", "Name"
    }
    return sorted([c for c in cols if c not in base_cols])


# ========== Builder UI per condizioni =========================================

OPS = ["==", "!=", ">", ">=", "<", "<="]

def _auto_cast_value(val_txt: str) -> Any:
    """Converte testo in bool/int/float quando possibile, altrimenti stringa."""
    if isinstance(val_txt, str) and val_txt.lower() in ["true", "false"]:
        return val_txt.lower() == "true"
    try:
        if "." in val_txt:
            return float(val_txt)
        return int(val_txt)
    except Exception:
        return val_txt

def condition_row_ui(prefix: str, cols: List[str], idx: int) -> Dict[str, Any]:
    """
    Crea una riga UI per una condizione e ritorna dict compatibile col tuo JSON.
    UI migliorata per leggibilità: colonne più larghe + tooltip con nome completo.
    Supporta val numerico/stringa/bool oppure confronto con col2.
    """

    c1, c2, c3, c4 = st.columns([4.0, 1.4, 2.0, 2.6])

    with c1:
        col = st.selectbox(
            f"{prefix}_col_{idx}",
            cols,
            key=f"{prefix}_col_{idx}",
            label_visibility="collapsed",
            help="Seleziona indicatore (puoi scrivere per cercare)"
        )
        # Mostra sempre il valore completo sotto la select (leggibilità)
        st.caption(f"📌 {col}")

    with c2:
        op = st.selectbox(
            f"{prefix}_op_{idx}",
            OPS,
            key=f"{prefix}_op_{idx}",
            label_visibility="collapsed"
        )

    with c3:
        mode = st.radio(
            f"{prefix}_mode_{idx}",
            ["val", "col2"],
            horizontal=True,
            key=f"{prefix}_mode_{idx}",
            label_visibility="collapsed"
        )

    with c4:
        if mode == "val":
            val_txt = st.text_input(
                f"{prefix}_val_{idx}",
                value="0",
                key=f"{prefix}_val_{idx}",
                label_visibility="collapsed",
                help="Valore di confronto (es: 0, 20, true, Bullish)"
            )
            val = _auto_cast_value(val_txt)
            return {"col": col, "op": op, "val": val}
        else:
            col2 = st.selectbox(
                f"{prefix}_col2_{idx}",
                cols,
                key=f"{prefix}_col2_{idx}",
                label_visibility="collapsed",
                help="Seconda colonna per confronto (es: MACD_Signal)"
            )
            st.caption(f"📌 col2: {col2}")
            return {"col": col, "op": op, "col2": col2}


# ========== Funzione di backtest "web" (ritorna fig) ==========================

def run_backtest_single_for_web(
    ticker: str,
    period: str,
    system_name: str,
    system_cfg: Dict[str, Any],
    freq: str = "1D",
    force_long_logic: Optional[str] = None,
    force_short_logic: Optional[str] = None,
    default_prefer_short_on_conflict: bool = True,
    days_chart: int = 200,
) -> (Optional[pd.Series], Optional[plt.Figure]):
    """
    Esegue il backtest di UN sistema e ritorna (stats, fig) per Streamlit.
    """
    try:
        ta = TechnicalAnalyzer(ticker, period=period)
        ta = calculateTAIndicators(ta)
        ta = calculateScoring(ta)

        # Precompute indicato nel JSON (sig_ma_sar, alligator, ecc.)
        pre_key = system_cfg.get("precompute")
        pre_fn = PRECOMPUTE_FUNCS.get(pre_key)
        if callable(pre_fn):
            ta = pre_fn(ta)

        # ---- blocchi LONG/SHORT come in batch_backtest ----------------------
        blocks_long = system_cfg.get("long_blocks")
        blocks_short = system_cfg.get("short_blocks")
        blocks_long_logic = (system_cfg.get("long_blocks_logic")
                             or system_cfg.get("long_logic")
                             or "AND").upper()
        blocks_short_logic = (system_cfg.get("short_blocks_logic")
                              or system_cfg.get("short_logic")
                              or "AND").upper()

        if blocks_long:
            long_cols, ta.dataframe = _make_block_series(
                ta.dataframe, blocks_long, prefix=f"{system_name}_LONG"
            )
            json_long = [{"col": c, "op": "==", "val": True} for c in long_cols]
            long_logic = blocks_long_logic
        else:
            json_long = system_cfg.get("long", [])
            long_logic = (system_cfg.get("long_logic") or "AND").upper()

        if blocks_short:
            short_cols, ta.dataframe = _make_block_series(
                ta.dataframe, blocks_short, prefix=f"{system_name}_SHORT"
            )
            json_short = [{"col": c, "op": "==", "val": True} for c in short_cols]
            short_logic = blocks_short_logic
        else:
            json_short = system_cfg.get("short", [])
            short_logic = (system_cfg.get("short_logic") or "AND").upper()

        # preferenza short-on-conflict
        _, _, prefer_short = _resolve_logics(
            {
                "long_logic": long_logic,
                "short_logic": short_logic,
                "prefer_short_on_conflict": system_cfg.get(
                    "prefer_short_on_conflict",
                    default_prefer_short_on_conflict,
                ),
            },
            force_long_logic,
            force_short_logic,
            default_prefer_short_on_conflict,
        )

        signal_name = system_cfg.get("signal_name", "Trading_Signal")

        # Lancia il backtest SENZA grafico interno (lo facciamo noi)
        stats = ta.backTestingVBTLogic(
            plotChart=False,
            freq=freq,
            json_long=json_long,
            json_short=json_short,
            long_logic=long_logic,
            short_logic=short_logic,
            signal_name=signal_name,
            prefer_short_on_conflict=prefer_short,
        )

        # Helper per estrarre ultimo valore intero
        def _last_int(series) -> Optional[int]:
            s = pd.to_numeric(series, errors="coerce").dropna()
            return int(s.iloc[-1]) if len(s) else np.nan

        sig_last = _last_int(ta.dataframe.get(signal_name, pd.Series(dtype="float64")))
        long_last = _last_int(ta.dataframe.get("Long_Days", pd.Series(dtype="float64")))
        short_last = _last_int(ta.dataframe.get("Short_Days", pd.Series(dtype="float64")))

        stats = stats.copy()
        stats["__ticker__"] = ticker
        stats["__system__"] = system_name
        stats["__period__"] = period
        stats["Trading_Signal"] = sig_last
        stats["Long_Days"] = long_last
        stats["Short_Days"] = short_last

        # ==== FIGURA DASHBOARD COMPLETA =====
        cm = AlligatorChartManager(technical_analyzer=ta)

        # Height ratios: [Price, Volume, ADX, MACD, MCS, TechScore, Oscillators]
        custom_height_ratios = [9.0, 2.0, 2.2, 2.5, 2.5, 2.0, 2.8]

        fig = cm.plot_ta_dashboard(
            days=days_chart,
            chart_type="candlestick",
            show_signal6_bg=True,
            show_sar=True,
            show_mas=True,
            show_mcs=True,
            show_rsi=True,
            show_stoch=True,
            show_willr=True,
            auto_compute_missing=True,
            max_candles=days_chart,
            figsize=(18, 17),
            dpi=120,
            save=False,
            show_volume=True,
            volume_ma=(10, 5),
            show_adx=True,
            show_atr_band=False,
            show_chandelier=True,
            show_atr_pct_panel=False,
            show_tech_score=True,
            show_entries_exits=True,
            height_ratios=custom_height_ratios,
        )

        # --- LEGENDA COMPLETA (linee principali + ingressi/uscite) ---
        if fig.axes:
            ax_price = fig.axes[0]

            leg = ax_price.get_legend()
            if leg is not None:
                leg.remove()

            allowed_labels = {
                "Long Entry", "Long Exit", "Short Entry", "Short Exit",
                "Jaw (Blue)", "Teeth (Red)", "Lips (Green)",
                "SAR (Buy)", "SAR (Sell)", "CE Long", "CE Short",
                "EMA_30", "EMA_50", "Candlesticks", "Close Price",
            }

            handles_map = {}
            for artist in list(ax_price.lines) + list(ax_price.collections):
                label = artist.get_label()
                if label in allowed_labels and label not in handles_map:
                    handles_map[label] = artist

            if handles_map:
                labels = list(handles_map.keys())
                handles = [handles_map[l] for l in labels]
                ax_price.legend(
                    handles, labels,
                    loc="upper left",
                    frameon=True,
                    fontsize=9,
                    ncol=3,
                )

        return stats, fig

    except Exception as e:
        st.error(f"[ERRORE] {ticker} | {system_name}: {e}")
        return None, None


# ========== UI Streamlit ======================================================

def main():
    st.set_page_config(page_title="Trading Systems JSON Editor", layout="wide")

    # CSS globale per allargare i widget del builder
    st.markdown("""
    <style>
      div[data-testid="stSelectbox"] > div { min-width: 380px !important; }
      div[data-testid="stTextInput"] > div { min-width: 220px !important; }
      .stRadio [role="radiogroup"] { gap: 0.4rem; }
    </style>
    """, unsafe_allow_html=True)

    st.title("📈 Editor Trading Systems + Builder Visuale + Dashboard Tecnica")

    # --- Selezione file JSON --------------------------------------------------
    st.sidebar.header("⚙️ Configurazione")
    json_files = list_system_json_files()
    if not json_files:
        st.sidebar.error("Nessun file .json trovato in 'tradingSystems/'.")
        st.stop()

    selected_file = st.sidebar.selectbox("File sistemi JSON", json_files, index=0)
    systems_cfg, json_path = load_systems(selected_file)

    # ====== BUILDER: nuovo trading system dinamico ==========================
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧱 Crea nuovo Trading System (NO JSON manuale)")

    builder_ticker = st.sidebar.text_input(
        "Ticker per leggere indicatori",
        value="A2A.MI",
        key="builder_ticker"
    )
    builder_period = st.sidebar.selectbox(
        "Periodo (builder)",
        ["6mo", "1y", "2y", "5y", "max"],
        index=2,
        key="builder_period"
    )

    indicator_cols = get_indicator_columns_for_ui(builder_ticker, builder_period)
    if not indicator_cols:
        st.sidebar.warning("Nessun indicatore trovato. Controlla ticker/periodo.")
    else:
        with st.sidebar.expander("➕ Nuovo sistema", expanded=False):
            new_sys_name = st.text_input("Nome nuovo sistema", value="My_New_System")

            precompute_key = st.selectbox(
                "precompute (opzionale)",
                ["None"] + sorted([k for k in PRECOMPUTE_FUNCS.keys() if k]),
                index=0
            )
            precompute_val = None if precompute_key == "None" else precompute_key

            long_logic_new = st.selectbox("Long logic", ["AND", "OR"], index=0)
            short_logic_new = st.selectbox("Short logic", ["AND", "OR"], index=0)

            st.markdown("**LONG conditions**")
            n_long = st.number_input(
                "Numero condizioni LONG",
                min_value=1, max_value=10, value=3, step=1
            )
            long_conds = []
            for i in range(int(n_long)):
                long_conds.append(condition_row_ui("new_long", indicator_cols, i))

            st.markdown("**SHORT conditions**")
            n_short = st.number_input(
                "Numero condizioni SHORT",
                min_value=1, max_value=10, value=2, step=1
            )
            short_conds = []
            for i in range(int(n_short)):
                short_conds.append(condition_row_ui("new_short", indicator_cols, i))

            prefer_short_conflict = st.checkbox(
                "Prefer short on conflict",
                value=True
            )

            if st.button("✅ Aggiungi sistema al file"):
                if not new_sys_name.strip():
                    st.error("Nome sistema vuoto.")
                elif new_sys_name in systems_cfg:
                    st.error("Esiste già un sistema con questo nome.")
                else:
                    new_cfg = {
                        "precompute": precompute_val,
                        "long": long_conds,
                        "short": short_conds,
                        "long_logic": long_logic_new,
                        "short_logic": short_logic_new,
                        "prefer_short_on_conflict": prefer_short_conflict,
                        "signal_name": "Trading_Signal"
                    }
                    systems_cfg[new_sys_name] = new_cfg
                    save_systems(json_path, systems_cfg)
                    st.success(f"Sistema '{new_sys_name}' salvato in {selected_file}.")
                    st.experimental_rerun()

    # --- Selezione sistema ----------------------------------------------------
    st.sidebar.markdown("---")
    system_names = sorted(list(systems_cfg.keys()))
    selected_system = st.sidebar.selectbox("Trading System", system_names)

    current_cfg = systems_cfg[selected_system]

    # --- Editor JSON del singolo sistema -------------------------------------
    st.subheader(f"🧩 Config JSON per sistema: `{selected_system}`")
    default_text = json.dumps(current_cfg, indent=2, ensure_ascii=False)
    edited_text = st.text_area(
        "Modifica qui il JSON del sistema (solo oggetto del sistema, non tutto il file):",
        value=default_text,
        height=350,
        key="json_editor",
    )

    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("💾 Salva modifiche nel file JSON", type="primary"):
            try:
                new_cfg = json.loads(edited_text)
                if not isinstance(new_cfg, dict):
                    st.error("Il JSON modificato deve essere un oggetto/dizionario.")
                else:
                    systems_cfg[selected_system] = new_cfg
                    save_systems(json_path, systems_cfg)
                    st.success(f"Sistema '{selected_system}' salvato in '{selected_file}'.")
            except json.JSONDecodeError as e:
                st.error(f"Errore nel JSON: {e}")
    with col_reset:
        if st.button("↩️ Ripristina dal file"):
            st.experimental_rerun()

    st.markdown("---")

    # --- Parametri per il backtest/grafico -----------------------------------
    st.subheader("🚀 Esegui Backtest & Visualizza Grafici Tecnici")

    col_left, col_right = st.columns(2)
    with col_left:
        ticker = st.text_input("Ticker", value="STMMI.MI")
        period = st.selectbox("Periodo dati (download)", ["6mo", "1y", "2y", "5y", "max"], index=2)
        freq = st.selectbox("Freq logica (backtest)", ["1D", "1H", "4H"], index=0)

    with col_right:
        days_chart = st.slider(
            "Numero di giorni da visualizzare nei grafici",
            min_value=60, max_value=500,
            value=200, step=10
        )
        force_long_logic = st.selectbox("FORCE_LONG_LOGIC", ["None", "AND", "OR"], index=0)
        force_short_logic = st.selectbox("FORCE_SHORT_LOGIC", ["None", "AND", "OR"], index=0)
        prefer_short_default = st.checkbox("DEFAULT_PREFER_SHORT_ON_CONFLICT", value=True)

    force_long_logic_val = None if force_long_logic == "None" else force_long_logic
    force_short_logic_val = None if force_short_logic == "None" else force_short_logic  # FIX BUG

    # --- Pulsanti: Preview, singolo backtest, tutti i sistemi ----------------
    col_bt1, col_bt2, col_bt3 = st.columns(3)
    with col_bt1:
        preview_btn = st.button("🔍 Aggiorna solo grafici (TS selezionato)", key="preview_btn")
    with col_bt2:
        backtest_btn = st.button("▶️ Backtest TS selezionato", type="primary", key="backtest_btn")
    with col_bt3:
        backtest_all_btn = st.button("🧪 Backtest TUTTI i sistemi del file", key="backtest_all_btn")

    def _parse_cfg_from_editor(text: str) -> Optional[Dict[str, Any]]:
        """Parsa il JSON dall'editor e verifica che sia un dict."""
        try:
            cfg = json.loads(text)
            if not isinstance(cfg, dict):
                st.error("Il JSON modificato deve essere un oggetto/dizionario.")
                return None
            return cfg
        except json.JSONDecodeError as e:
            st.error(f"Errore nel JSON (prima dell'esecuzione): {e}")
            return None

    # --- PREVIEW GRAFICI (TS selezionato) -----------------------------------
    if preview_btn:
        cfg_for_run = _parse_cfg_from_editor(edited_text)
        if cfg_for_run is not None:
            with st.spinner("Aggiornamento grafici con la nuova configurazione..."):
                stats, fig = run_backtest_single_for_web(
                    ticker=ticker,
                    period=period,
                    system_name=selected_system,
                    system_cfg=cfg_for_run,
                    freq=freq,
                    force_long_logic=force_long_logic_val,
                    force_short_logic=force_short_logic_val,
                    default_prefer_short_on_conflict=prefer_short_default,
                    days_chart=days_chart,
                )

            if fig is not None:
                st.info("Grafici aggiornati usando la configurazione corrente dell'editor.")
                st.subheader("📉 Dashboard Tecnica Completa – TS selezionato")
                st.pyplot(fig)
            else:
                st.error("Impossibile generare i grafici.")

    # --- BACKTEST COMPLETO (TS selezionato) ---------------------------------
    if backtest_btn:
        cfg_for_run = _parse_cfg_from_editor(edited_text)
        if cfg_for_run is not None:
            with st.spinner("Esecuzione backtest (TS selezionato)..."):
                stats, fig = run_backtest_single_for_web(
                    ticker=ticker,
                    period=period,
                    system_name=selected_system,
                    system_cfg=cfg_for_run,
                    freq=freq,
                    force_long_logic=force_long_logic_val,
                    force_short_logic=force_short_logic_val,
                    default_prefer_short_on_conflict=prefer_short_default,
                    days_chart=days_chart,
                )

            if stats is not None and fig is not None:
                st.success("Backtest completato.")
                st.subheader("📊 Statistiche backtest – TS selezionato")
                stats_df = stats.to_frame(name="Valore")
                st.dataframe(stats_df)
                st.subheader("📉 Dashboard Tecnica Completa – TS selezionato")
                st.pyplot(fig)
            else:
                st.error("Backtest non riuscito.")

    # --- BACKTEST DI TUTTI I SISTEMI DEL FILE -------------------------------
    if backtest_all_btn:
        cfg_for_selected = _parse_cfg_from_editor(edited_text)
        if cfg_for_selected is not None:
            systems_for_run = dict(systems_cfg)
            systems_for_run[selected_system] = cfg_for_selected

            comparison_rows = []
            figs: Dict[str, plt.Figure] = {}

            st.info(
                "Esecuzione del backtest per TUTTI i sistemi nel file selezionato.\n"
                "Per il sistema selezionato viene usata la configurazione corrente dell'editor."
            )

            for sys_name, sys_cfg in systems_for_run.items():
                with st.spinner(f"Backtest in corso: {sys_name}"):
                    stats, fig = run_backtest_single_for_web(
                        ticker=ticker,
                        period=period,
                        system_name=sys_name,
                        system_cfg=sys_cfg,
                        freq=freq,
                        force_long_logic=force_long_logic_val,
                        force_short_logic=force_short_logic_val,
                        default_prefer_short_on_conflict=prefer_short_default,
                        days_chart=days_chart,
                    )

                if stats is None:
                    continue

                row: Dict[str, Any] = {"System": sys_name}

                candidate_metrics = [
                    "Total Return [%]", "Total Return", "Total Return [€]",
                    "Sharpe Ratio", "Max Drawdown [%]", "Max Drawdown",
                    "Win Rate [%]", "SQN", "Expectancy",
                ]
                for m in candidate_metrics:
                    if m in stats.index:
                        row[m] = stats[m]

                for extra in ["Trading_Signal", "Long_Days", "Short_Days"]:
                    if extra in stats.index:
                        row[extra] = stats[extra]

                comparison_rows.append(row)
                if fig is not None:
                    figs[sys_name] = fig

            if comparison_rows:
                comp_df = pd.DataFrame(comparison_rows).set_index("System")

                for col in ["Total Return [%]", "Total Return", "Total Return [€]"]:
                    if col in comp_df.columns:
                        comp_df = comp_df.sort_values(by=col, ascending=False)
                        break

                st.subheader("🏁 Confronto tra tutti i Trading Systems del file")
                st.dataframe(comp_df)

                if figs:
                    st.subheader("📉 Seleziona un sistema per visualizzare il grafico")
                    sys_for_chart = st.selectbox(
                        "Grafico per Trading System",
                        list(figs.keys()),
                        index=0,
                    )
                    st.pyplot(figs[sys_for_chart])
                else:
                    st.warning("Backtest eseguiti, ma nessun grafico disponibile.")
            else:
                st.error("Nessun backtest è andato a buon fine per i sistemi del file.")


if __name__ == "__main__":
    main()
