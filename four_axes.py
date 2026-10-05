"""I quattro assi che descrivono un titolo, e il punteggio tecnico derivato.

Sostituisce la cascata di `Market_Phase` (6 stati), `Trend_Phase_Detail` (15),
`TECH_SCORE` (media di 6 misure ridondanti + penalità occulta) e la duplicazione
delle stesse soglie in `main.py`, `backend/app/services/watchlist_service.py` e
`frontend/src/components/WatchlistCard.tsx`.

Principi:
  * quattro letture **indipendenti** (direzione, forza, momento, rischio), ognuna
    leggibile da sola;
  * tutte le soglie in un unico blocco (`SOGLIE`);
  * il punteggio è la **somma visibile** dei contributi, ancorata a 50 = nessuna
    convinzione e nessun rischio;
  * nessun uso di dati non ancora disponibili: si usano solo colonne già calcolate
    (EMA50, ADX, DI, MACD, ATR%).

Documentazione completa: docs/tech-score-semplificazione.md
"""
from __future__ import annotations

import pandas as pd

# ─────────────────────────── SOGLIE (unico punto di taratura) ────────────────
SOGLIE: dict[str, float] = {
    "adx_forte": 22.0,          # Forza: ADX da cui il movimento è convincente
    "slope_piatta_pct": 0.5,    # Direzione: pendenza EMA50 su 5 sedute
    "macd_momento_sedute": 3,   # Momento: confronto dell'istogramma su N sedute
    "atr_teso_pct": 3.0,        # Rischio: ATR% da cui il titolo è teso
    "atr_estremo_pct": 5.0,
    "dist_tesa_pct": 5.0,       # Rischio: distanza da EMA50
    "dist_estrema_pct": 9.0,
}

# Contributi in punti: la somma va da -150 a +130, l'ancora 50 vale a somma 0.
PUNTI: dict[str, dict[str, int]] = {
    "Direzione": {"SU": 60, "PIATTO": 0, "GIU": -60},
    "Forza": {"FORTE_SU": 35, "DEBOLE": 0, "FORTE_GIU": -35},
    "Momento": {"CRESCENTE": 35, "STABILE": 0, "CALANTE": -35},
    "Rischio": {"NORMALE": 0, "TESO": -10, "ESTREMO": -20},
}
SCALA = 50.0 / 150.0  # somma +150 -> 100, somma 0 -> 50, somma -150 -> 0

# Soglie dell'indicazione operativa (ex cascata `Action`).
AZIONI: dict[str, float] = {
    "tech_buy": 65.0,        # TECH_SCORE minimo per ENTRA
    "tech_sell": 35.0,       # TECH_SCORE massimo per EVITA
    "stoch_overbought": 80.0,
    "stoch_oversold": 20.0,
    "atr_alto_pct": 3.0,
}

COLONNE_ASSI = ("Direzione_Trend", "Forza_Trend", "Momento_Trend", "Rischio_Trend")
FASI = ("TENDENZA", "RIPRESA", "LATERALE", "RIBASSO")
INDICAZIONI = ("ENTRA", "OSSERVA", "ATTENDI", "EVITA")


def _num(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(float("nan"), index=df.index, dtype=float)


def compute_axes(df: pd.DataFrame, soglie: dict[str, float] | None = None) -> pd.DataFrame:
    """Calcola i quattro assi. Non modifica l'input: restituisce un nuovo frame."""
    s = {**SOGLIE, **(soglie or {})}
    idx = df.index

    close = _num(df, "Close")
    ema50 = _num(df, "EMA_50")
    adx = _num(df, "ADX")
    plus_di = _num(df, "PLUS_DI")
    minus_di = _num(df, "MINUS_DI")
    macd = _num(df, "MACD")
    macd_signal = _num(df, "MACD_Signal")
    atr_pct = _num(df, "ATR_PCT")

    # ── Asse 1: DIREZIONE. Prezzo rispetto all'EMA50, con la pendenza della media.
    # La soglia di pendenza non è l'unico criterio: se l'ADX dice che c'è tendenza,
    # la direzione la dà il prezzo rispetto alla media anche con pendenza modesta
    # (senza questo, un ribasso lento con ADX forte risultava "piatto").
    slope = (ema50 / ema50.shift(5) - 1.0) * 100.0
    ha_tendenza = adx >= s["adx_forte"]
    sopra = close > ema50
    sotto = close < ema50
    direzione = pd.Series("PIATTO", index=idx, dtype=object)
    direzione = direzione.mask(sopra & ((slope > s["slope_piatta_pct"]) | ha_tendenza), "SU")
    direzione = direzione.mask(sotto & ((slope < -s["slope_piatta_pct"]) | ha_tendenza), "GIU")

    # ── Asse 2: FORZA. ADX più la direzione dei DI.
    forza = pd.Series("DEBOLE", index=idx, dtype=object)
    forza = forza.mask((adx >= s["adx_forte"]) & (plus_di > minus_di), "FORTE_SU")
    forza = forza.mask((adx >= s["adx_forte"]) & (minus_di > plus_di), "FORTE_GIU")

    # ── Asse 3: MOMENTO. Solo MACD: distanza dal segnale e sua variazione.
    diff = macd - macd_signal
    n = int(s["macd_momento_sedute"])
    diff_prec = diff.shift(n)
    momento = pd.Series("STABILE", index=idx, dtype=object)
    momento = momento.mask((diff > 0) & (diff > diff_prec), "CRESCENTE")
    momento = momento.mask((diff < 0) & (diff < diff_prec), "CALANTE")

    # ── Asse 4: RISCHIO. Volatilità e distanza dalla media.
    dist = ((close / ema50) - 1.0).abs() * 100.0
    rischio = pd.Series("NORMALE", index=idx, dtype=object)
    rischio = rischio.mask((atr_pct >= s["atr_teso_pct"]) | (dist >= s["dist_tesa_pct"]), "TESO")
    rischio = rischio.mask((atr_pct >= s["atr_estremo_pct"]) | (dist >= s["dist_estrema_pct"]), "ESTREMO")

    return pd.DataFrame({
        "Direzione_Trend": direzione,
        "Forza_Trend": forza,
        "Momento_Trend": momento,
        "Rischio_Trend": rischio,
    }, index=idx)


def phase_from_axes(assi: pd.DataFrame) -> pd.Series:
    """Quattro fasi, dalla sola combinazione degli assi."""
    direzione = assi["Direzione_Trend"]
    forza = assi["Forza_Trend"]
    momento = assi["Momento_Trend"]

    fase = pd.Series("LATERALE", index=assi.index, dtype=object)
    tendenza = (direzione == "SU") & (forza == "FORTE_SU") & (momento != "CALANTE")
    fase = fase.mask(tendenza, "TENDENZA")
    fase = fase.mask((direzione == "SU") & ~tendenza, "RIPRESA")
    fase = fase.mask(direzione == "GIU", "RIBASSO")
    return fase


def detail_from_axes(assi: pd.DataFrame, fase: pd.Series) -> pd.Series:
    """Dettaglio della fase, per compatibilità con i filtri esistenti della GUI."""
    return fase.map({
        "TENDENZA": "EXPANSION",
        "RIPRESA": "EARLY_TREND",
        "RIBASSO": "DOWNTREND",
        "LATERALE": "RANGE",
    }).fillna("RANGE")


def score_from_axes(assi: pd.DataFrame) -> pd.Series:
    """Punteggio 0-100: somma visibile dei contributi, 50 = neutro."""
    somma = pd.Series(0, index=assi.index, dtype=float)
    for asse, pesi in PUNTI.items():
        colonna = f"{asse}_Trend"
        somma = somma + assi[colonna].map(pesi).fillna(0).astype(float)
    return (50.0 + somma * SCALA).clip(0.0, 100.0)


def indication_from_axes(assi: pd.DataFrame, fase: pd.Series) -> pd.Series:
    """Indicazione operativa, derivata dai quattro assi.

    Il solo momento crescente non basta per OSSERVA: serve una direzione
    rialzista, altrimenti in laterale si promuoveva troppo (39% su ETF).
    """
    direzione = assi["Direzione_Trend"]
    forza = assi["Forza_Trend"]
    momento = assi["Momento_Trend"]
    rischio = assi["Rischio_Trend"]

    indicazione = pd.Series("ATTENDI", index=assi.index, dtype=object)
    osservabile = (fase == "RIPRESA") | ((direzione == "SU") & (momento == "CRESCENTE"))
    indicazione = indicazione.mask(osservabile, "OSSERVA")
    indicazione = indicazione.mask(
        (fase == "TENDENZA") & (momento != "CALANTE") & (rischio == "NORMALE"), "ENTRA"
    )
    indicazione = indicazione.mask((fase == "RIBASSO") & (forza == "FORTE_GIU"), "EVITA")
    return indicazione


def action_from_axes(assi: pd.DataFrame, fase: pd.Series, liquidita: pd.Series) -> pd.Series:
    """Azione operativa (BUY/ADD/HOLD/REDUCE/EXIT/WAIT/AVOID) dai quattro assi.

    La liquidità ha la precedenza: AVOID esclude, diverso da OK sospende.
    """
    direzione = assi["Direzione_Trend"]
    forza = assi["Forza_Trend"]
    momento = assi["Momento_Trend"]
    rischio = assi["Rischio_Trend"]
    liq = liquidita.astype(str).str.strip().str.upper()

    azione = pd.Series("HOLD", index=assi.index, dtype=object)
    azione = azione.mask(direzione == "GIU", "AVOID")
    azione = azione.mask((direzione == "SU") & (forza != "FORTE_SU"), "ADD")
    azione = azione.mask((direzione == "SU") & (momento == "CALANTE") & (forza != "FORTE_SU"), "WAIT")
    azione = azione.mask(
        (fase == "TENDENZA") & (momento != "CALANTE") & (rischio == "TESO"), "HOLD"
    )
    azione = azione.mask(
        (fase == "TENDENZA") & ((rischio == "ESTREMO") | (momento == "CALANTE")), "REDUCE"
    )
    azione = azione.mask(
        (fase == "TENDENZA") & (momento != "CALANTE") & (rischio == "NORMALE"), "BUY"
    )
    azione = azione.mask(liq.eq("AVOID"), "AVOID")
    azione = azione.mask(liq.ne("OK") & liq.ne("AVOID"), "WAIT")
    return azione


def reason_from_axes(assi: pd.DataFrame, fase: pd.Series, azione: pd.Series) -> pd.Series:
    """Spiegazione leggibile dell'azione, senza gergo interno."""
    def testo(i: int) -> str:
        d = assi["Direzione_Trend"].iloc[i]
        f = assi["Forza_Trend"].iloc[i]
        m = assi["Momento_Trend"].iloc[i]
        r = assi["Rischio_Trend"].iloc[i]
        a = azione.iloc[i]
        if a == "AVOID" and d == "GIU":
            return "Direzione ribassista: fuori dal perimetro operativo"
        if a == "AVOID":
            return "Liquidità insufficiente"
        if a == "WAIT":
            return "Liquidità non ottimale o momento incerto"
        if a == "BUY":
            return "Tendenza confermata: direzione su, forza e momento allineati"
        if a == "ADD":
            return "Ripresa in corso: direzione su, forza non ancora confermata"
        if a == "REDUCE":
            return f"Tendenza ma rischio {r.lower()}: ridurre l'esposizione"
        if r == "ESTREMO":
            return "Titolo estremamente esteso"
        if m == "CRESCENTE":
            return "Laterale con momento in miglioramento"
        return "Nessuna configurazione operativa"

    return pd.Series([testo(i) for i in range(len(assi))], index=assi.index)


def warning_from_axes(assi: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
    """Avvisi sintetici, al posto delle 7 etichette sparse del vecchio Layer3."""
    def testo(i: int) -> str:
        avvisi = []
        r = assi["Rischio_Trend"].iloc[i]
        m = assi["Momento_Trend"].iloc[i]
        if r == "ESTREMO":
            avvisi.append("Estensione elevata")
        elif r == "TESO":
            avvisi.append("Titolo teso")
        if m == "CALANTE":
            avvisi.append("Momento in calo")
        return ", ".join(avvisi) if avvisi else "OK"

    return pd.Series([testo(i) for i in range(len(assi))], index=assi.index)


def _levels_from_axes(out: pd.DataFrame, assi: pd.DataFrame, fase: pd.Series, azione: pd.Series) -> None:
    """Livelli operativi coerenti con le nuove fasi (prima usavano UPTREND)."""
    def num(column: str) -> pd.Series:
        return _num(out, column)

    close = num("Close")
    ema30 = num("EMA_30")
    ema50 = num("EMA_50")
    atr = num("ATR")
    sar = num("SAR")

    in_tendenza = fase.isin(["TENDENZA", "RIPRESA"])
    buy_add = azione.isin(["BUY", "ADD"])
    reduce = azione.eq("REDUCE")

    stop = ema50
    out["Trend_Stop_Level"] = stop.where(in_tendenza & buy_add)
    out["Trend_Stop_Invalidation"] = (close < stop).where(in_tendenza & buy_add)
    out["Trend_Stop_Type"] = pd.Series("", index=out.index).mask(in_tendenza & buy_add, "STRUTTURA_EMA50")

    protetto = ema30 - 0.25 * atr
    if "SAR" in out.columns:
        protetto = pd.concat([protetto, sar], axis=1).max(axis=1)
    out["Profit_Protect_Level"] = protetto.where(in_tendenza & reduce)
    out["Profit_Protect_Invalidation"] = (close < protetto).where(in_tendenza & reduce)
    out["Profit_Protect_Type"] = pd.Series("", index=out.index).mask(in_tendenza & reduce, "TIGHT_EMA30_ATR")


def apply_to(df: pd.DataFrame, soglie: dict[str, float] | None = None) -> pd.DataFrame:
    """Aggiunge assi, fase, dettaglio, punteggio, indicazione, azione e avvisi."""
    out = df.copy()
    assi = compute_axes(out, soglie)
    for colonna in COLONNE_ASSI:
        out[colonna] = assi[colonna].values
    fase = phase_from_axes(assi)
    out["Market_Phase"] = fase.values
    out["Trend_Phase_Detail"] = detail_from_axes(assi, fase).values
    out["TECH_SCORE"] = score_from_axes(assi).round(2).values
    out["Entry_Signal"] = indication_from_axes(assi, fase).values

    liquidita = out["Liquidity"] if "Liquidity" in out.columns else pd.Series("OK", index=out.index)
    azione = action_from_axes(assi, fase, liquidita)
    out["Action"] = azione.values
    out["Action_Reason"] = reason_from_axes(assi, fase, azione).values
    out["Layer3_Warning"] = warning_from_axes(assi, out).values
    _levels_from_axes(out, assi, fase, azione)
    return out
