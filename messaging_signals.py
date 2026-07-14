# messaging_signals.py

import os
from datetime import datetime
import pandas as pd
from messaging import messaging
from typing import Optional

# -----------------------------------
# Config: mercato -> canale Telegram
# -----------------------------------
TELEGRAM_CHANNELS = {
    "MIB30": 1,
    "ETC": 1,
    "Preferite":1,
    "ETF": 2,
}

# -----------------------------------
# Formatter messaggio ENTER
# -----------------------------------


def send_document(
    ms: messaging,
    df: pd.DataFrame,
    *,
    market: str,
    trading_state: str,
    output_dir: str = "./telegram_exports",
    filename_extra: str = "",
    caption: Optional[str] = None
):
    """
    Salva un DataFrame in Excel e lo invia come documento Telegram.

    :param ms: istanza di messaging già inizializzata col canale corretto
    :param df: DataFrame da esportare
    :param market: nome mercato (MIB30, ETF, ecc)
    :param trading_state: ENTER / PREPARE
    :param output_dir: cartella dove salvare il file
    :param filename_extra: stringa opzionale per distinguere il file
    :param caption: caption Telegram (se None viene generata automaticamente)
    """

    if df is None or df.empty:
        return

    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    extra = f"_{filename_extra}" if filename_extra else ""
    filename = f"{market}_{trading_state}{extra}_{ts}.xlsx"
    filepath = os.path.join(output_dir, filename)

    # Salva tutto il DF (Open, Close, Layer, ecc)
    df.to_excel(filepath, index=False)

    if caption is None:
        caption = f"{market} — {trading_state} ({len(df)} titoli)"

    # usa la tua classe messaging
    ms.send_document(filepath, caption=caption)
def fmt(x):
    try:
        if x is None:
            return "n/a"
        return f"{float(x):.2f}"
    except Exception:
        return str(x)

def format_trading_state_message(
    market: str,
    df_state: pd.DataFrame,
    trading_state: str,
    max_send: int = 20
) -> str:
    """
    Crea un messaggio HTML Telegram con i titoli
    nello stato di trading passato (ENTER / PREPARE / altro).
    """
    n_total = len(df_state)
    to_send = min(max_send, n_total)

    header = (
        f"<b>{market} — TITOLI IN {trading_state}</b>\n"
        f"Totale: {n_total} | Mostro: {to_send}\n"
        f"Ordinati per Layer2_Score ↓\n"
    )

    lines = [header]

    for _, r in df_state.head(to_send).iterrows():
        ticker = str(r.get("Ticker", "")).strip()
        name   = str(r.get("Name", "")).strip()

        l1 = r.get("Layer1_Action", "n/a")
        l2 = r.get("Layer2_Label", "n/a")
        l2s = r.get("Layer2_Score", "n/a")

        pctv = r.get("PCTV_1D", "n/a")
        rsi = r.get("RSI", "n/a")

        # Attenzione: nel tuo file potrebbero chiamarsi "Stochastic_K/D" oppure "Stoch_K/D"
        stoch_k = r.get("Stochastic_K", r.get("Stoch_K", "n/a"))
        stoch_d = r.get("Stochastic_D", r.get("Stoch_D", "n/a"))

        mcs = r.get("MCS", "n/a")

        url = f"https://finance.yahoo.com/quote/{ticker}/" if ticker else ""

        if url:
            lines.append(
                f'<a href="{url}">{name}</a> ({ticker}) | '
                f'L1:{l1} | L2:{l2} | Score:{l2s} | '
                f'PCTV_1D:{fmt(pctv)}% | RSI:{fmt(rsi)} | StochK:{fmt(stoch_k)} | StochD:{fmt(stoch_d)} | MCS:{fmt(mcs)}'

            )
        else:
            lines.append(
                f'<a href="{url}">{name}</a> ({ticker}) | '
                f'L1:{l1} | L2:{l2} | Score:{l2s} | '
                f'PCTV_1D:{fmt(pctv)}% | RSI:{fmt(rsi)} | StochK:{fmt(stoch_k)} | StochD:{fmt(stoch_d)} | MCS:{fmt(mcs)}'

            )

    return "\n".join(lines)

# -----------------------------------
# Sender principale
# -----------------------------------
def send_trading_state_to_telegram(
    all_results: dict,
    markets,
    *,
    trading_state: str = "ENTER",
    max_send: int = 20,
    send_excel: bool = False
):
    for market in markets:
        if market not in all_results:
            continue

        df = all_results[market]
        if df is None or df.empty:
            continue

        if "Trading_State" not in df.columns:
            print(f"⚠️ {market}: colonna Trading_State mancante")
            continue

        df_state = (
            df[df["Trading_State"] == trading_state]
            .sort_values(by="Layer2_Score", ascending=False)
            .copy()
        )

        channel = TELEGRAM_CHANNELS.get(market, 4)
        ms = messaging(chatTarget=channel)

        if df_state.empty:
            ms.sendURLs(f"<b>{market}</b> — Nessun titolo in {trading_state}.")
            continue

        msg = format_trading_state_message(
            market,
            df_state,
            trading_state,
            max_send=max_send
        )

        ms.sendURLs(msg)

        if send_excel:
            send_document(
                ms,
                df_state,
                market=market,
                trading_state=trading_state
            )

        print(f"--- Telegram OK | {market} | {trading_state} ---")

def send_trading_state_to_telegramv1(
    all_results: dict,
    markets,
    *,
    trading_state: str = "ENTER",
    max_send: int = 20,
    send_excel: bool = True
):
    #versione con invio file excel non opzionale
    for market in markets:
        if market not in all_results:
            continue

        df = all_results[market]
        if df is None or df.empty:
            continue

        if "Trading_State" not in df.columns:
            print(f"⚠️ {market}: colonna Trading_State mancante")
            continue

        df_state = (
            df[df["Trading_State"] == trading_state]
            .sort_values(by="Layer2_Score", ascending=False)
            .copy()
        )

        channel = TELEGRAM_CHANNELS.get(market, 4)
        ms = messaging(chatTarget=channel)

        if df_state.empty:
            ms.sendURLs(f"<b>{market}</b> — Nessun titolo in {trading_state}.")
            continue

        # 1️⃣ messaggio testuale
        msg = format_trading_state_message(
            market,
            df_state,
            trading_state,
            max_send=max_send
        )
        ms.sendURLs(msg)

        # 2️⃣ allegato Excel
        if send_excel:
            send_document(
                ms,
                df_state,
                market=market,
                trading_state=trading_state,
                caption=f"{market} — Dettaglio titoli {trading_state}"
            )

        print(f"--- Telegram OK | {market} | {trading_state} ---")

def send_trading_state_to_telegramv0(
    all_results: dict,
    markets,
    *,
    trading_state: str = "ENTER",
    max_send: int = 20,
):
    """
    Invia su Telegram i titoli in uno stato di trading
    (ENTER / PREPARE) separati per mercato.
    """
    for market in markets:
        if market not in all_results:
            continue

        df = all_results[market]
        if df is None or df.empty:
            continue

        if "Trading_State" not in df.columns:
            print(f"⚠️ {market}: colonna Trading_State mancante")
            continue

        df_state = (
            df[df["Trading_State"] == trading_state]
            .sort_values(by="Layer2_Score", ascending=False)
            .copy()
        )

        channel = TELEGRAM_CHANNELS.get(market, 4)
        ms = messaging(chatTarget=channel)

        if df_state.empty:
            ms.sendURLs(f"<b>{market}</b> — Nessun titolo in {trading_state}.")
            continue

        msg = format_trading_state_message(
            market,
            df_state,
            trading_state,
            max_send=max_send
        )

        ms.sendURLs(msg)
        print(f"--- Messaggio Telegram inviato market {market} per titoli in {trading_state}---")
