# ta_llm_analyst.py
# -*- coding: utf-8 -*-

import os
import json
from typing import Optional, Union, List, Dict, Any
from datetime import date
import pandas as pd
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Your technical engine
from TechnicalAnalyzer import TechnicalAnalyzer


class TAOpenAIAnalyst:
    """
    Build compact LLM payloads from well-known indicators and query an LLM.
    Supports an optional `show_io` flag to return full inputs (system, user, payload) and output.
  """
    # Include OHLC for candlestick reading + SAR details
    SNAPSHOT_COLS = [
        # trend / momentum you already had
        "EMA_30", "EMA_50",
        "RSI", "Stoch_K", "Stoch_D", "Williams_R",
        "MACD", "MACD_Signal", "MACD_Hist",
        "SAR", "SAR_Above_Price",
        "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips",
        "Close",
        "PCTV_1D", "PCTV_5D", "PCTV_10D", "PCTV_30D",
        "Vol_Perc_vs_MA20", "Vol_Perc_vs_MA5",
        "Volume",
        # ⬇︎ NEW — ATR suite
        "ATR", "ATR_PCT", "ATR_Upper", "ATR_Lower",
        "CE_Long", "CE_Short", "ATR_Long_OK", "ATR_Short_OK",
        # ⬇︎ NEW — ADX suite
        "ADX", "PLUS_DI", "MINUS_DI", "ADX_Strong", "ADX_Trend", "ADX_Cross",
    ]

    SERIES_KEYS = [
        # OHLC + core
        "Open", "High", "Low", "Close",
        "Volume",
        "MACD_Hist", "RSI",
        "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips",
        "SAR", "SAR_Above_Price",
        # ⬇︎ NEW — for drawing ATR bands / CE in the chart and giving LLM context
        "ATR_Upper", "ATR_Lower", "CE_Long", "CE_Short", "ATR_PCT",
        # ⬇︎ NEW — ADX context (trend strength & DI relationship)
        "ADX", "PLUS_DI", "MINUS_DI",
    ]

    def __init__(self,
                 model: str = "gpt-4o-mini",
                 temperature: float = 0.0,
                 period: str = "2y",
                 tail_bars: int = 30):
        load_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not found. Put it in a .env or as an environment variable.")

        self.model_name = model
        self.temperature = temperature
        self.period = period
        self.tail_bars = tail_bars

        self._client = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature
        )

    # ---------- utils ----------
    @staticmethod
    def _to_jsonable(val):
        """Convert Pandas/Numpy to JSON-serializable types."""
        if pd.isna(val):
            return None
        if isinstance(val, (pd.Timestamp, pd.Timedelta)):
            return str(val)
        try:
            return val.item()
        except Exception:
            return val

    def _ensure_client(self, temperature: Optional[float] = None):
        if temperature is None or temperature == self.temperature:
            return self._client
        return ChatOpenAI(model=self.model_name, temperature=temperature)

    # ---------- payload builder ----------
    def prepare_payload_for_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Build a compact payload with well-known indicators + Alligator + Volume % + Parabolic SAR + OHLC series.
        """
        ta = TechnicalAnalyzer(ticker, period=self.period)
        ta.calculate_TA_Indicators(
            indicators="ADX,ATR,MACD, RSI, WILLR, STOCH, EMA_30, EMA_50, ALLIGATOR, PCTV, SAR, VOL_PERC"
        )

        df = ta.dataframe.copy()
        df.index = pd.to_datetime(df.index)

        # Last bar snapshot
        last_idx = df.index.max()
        snap = {"ticker": ticker}
        for c in self.SNAPSHOT_COLS:
            if c in df.columns:
                snap[c] = self._to_jsonable(df.loc[last_idx, c])

        # Lightweight trailing window for shape/context (incl. OHLC for candlesticks)
        tail = df.tail(self.tail_bars)
        series_tail = {"index": [d.strftime("%Y-%m-%d") for d in tail.index]}
        for k in self.SERIES_KEYS:
            if k in tail.columns:
                vals = []
                for x in tail[k].tolist():
                    if isinstance(x, float) and pd.isna(x):
                        vals.append(None)
                    else:
                        vals.append(self._to_jsonable(x))
                series_tail[k] = vals

        payload = {
            "as_of": date.today().isoformat(),
            "period_used": self.period,
            "ticker": ticker,
            "snapshot": snap,
            "series_tail": series_tail,
            "legend": {
                "EMA_30/50": "Exponential moving averages for trend bias.",
                "RSI": "0–100; >70 overbought, <30 oversold.",
                "Stoch_K/Stoch_D": "Stochastic oscillator (momentum).",
                "Williams_R": "Momentum oscillator from -100 to 0.",
                "MACD/MACD_Signal/MACD_Hist": "Trend & momentum; histogram shows shifts.",
                "SAR": "Parabolic SAR value (often used as trailing stop proxy).",
                "SAR_Above_Price": "True if SAR dot is above price (typically bearish).",
                "Alligator_Jaw/Teeth/Lips": "Bill Williams smoothed MAs for trend structure.",
                "PCTV_*D": "Price change vs N trading days ago, in percent.",
                "Vol_Perc_vs_MA20/MA5": "Volume vs its MA (percent).",
                "Open/High/Low/Close": "Recent OHLC for candlestick pattern reading.",
                "ATR": "Average True Range (absolute).",
                "ATR_PCT": "ATR as % of price; quick relative volatility read.",
                "ATR_Upper/ATR_Lower": "Dynamic envelope: Close above/below may flag breakout/exhaustion.",
                "CE_Long/CE_Short": "Chandelier Exit trailing levels for long/short risk control.",
                "ATR_Long_OK/ATR_Short_OK": "Volatility filter flags for long/short setups.",
                "ADX": "Trend strength (0–100). Roughly: <20 weak, ~25+ trending.",
                "PLUS_DI/MINUS_DI": "+DI vs -DI direction bias; crosses can signal shifts.",
                "ADX_Strong": "Boolean: strong-trend regime (often ADX≥25).",
                "ADX_Trend": "Bullish/Bearish label (from +DI/-DI or your engine).",
                "ADX_Cross": "Last DI cross (BullCross/BearCross) if any."
            }
        }
        return payload

    def build_payloads(self, tickers: List[str]) -> List[Dict[str, Any]]:
        out = []
        for t in tickers:
            try:
                out.append(self.prepare_payload_for_ticker(t))
            except Exception as e:
                print(f"[WARN] {t}: {e}")
        return out

    # ---------- prompts ----------
    def _build_prompt(self, payload: Dict[str, Any], max_words: int) -> Dict[str, str]:
        """
        Build prompt per generare un commento discorsivo stile:
        '📘 GenAI Insight — Versione Long', con sezione finale "🧠 Conclusione Finale".
        Lo stile di riferimento è quello dell'esempio su AMP.MI | Amplifon.
        """
        ticker = payload.get("ticker", "N/A")
        system = (
            "Sei un analista tecnico professionale e scrivi COMMENTI DI MERCATO in italiano. "
            "Il tuo compito è generare un commento discorsivo, strutturato, in stile editoriale, "
            "non un elenco puntato (eccetto nelle sezioni obbligatorie finali). "
            "Usa SOLO i dati del JSON e non inventare mai numeri o indicatori. "
            "Puoi commentare trend, momentum, volatilità, struttura tecnica, livelli chiave, "
            "indicatori compositi (ad es. TechScore, MCS, segnali S6) e livelli di Chandelier Exit, "
            "Indica alla fine segnali di trading espliciti (Buy/Sell/Hold o altro ) o altri a tua discrezione. "
            "Il testo deve avere tono serio, analitico e professionale."
        )

        snapshot_json = json.dumps(payload.get("snapshot", {}), ensure_ascii=False)
        tail = payload.get("series_tail", {})
        tail_json = json.dumps(tail, ensure_ascii=False)
        n_bars = len(tail.get("index", []))

        # >>> ESEMPIO DI STILE: quello che hai scritto per AMP.MI | Amplifon <<<
        example_long = (
            "📘 GenAI Insight — Versione Long\n\n"
            "AMP.MI | Amplifon\n\n"
            "Amplifon (AMP.MI) sta attraversando una fase di graduale miglioramento tecnico dopo un periodo "
            "esteso di debolezza. Il prezzo mostra segnali di recupero sopra alcune medie dinamiche di breve "
            "orizzonte, mentre i volumi risultano nettamente superiori alle medie degli ultimi giorni "
            "(+54% rispetto a MA5 e +80% rispetto a MA20), indicando un ritorno di interesse sul titolo. "
            "Nonostante il recente rimbalzo, la struttura complessiva rimane inserita in un contesto ribassista "
            "di medio periodo, evidenziata dalla classificazione S6 come Downtrend_revS3Sig+++ e dai drawdown "
            "ancora pesanti sul 30D e 180D.\n\n"
            "Il quadro del momentum appare più costruttivo: il MACD, pur negativo da molte sedute, mostra un "
            "istogramma positivo da 11 giorni consecutivi, segnale che la pressione ribassista sta gradualmente "
            "rallentando. Anche l’RSI (52.7) si è riportato in area neutro-positiva con un trend ascendente negli "
            "ultimi tre giorni, mentre lo Stocastico descrive un recupero vigoroso, coerente con movimenti di "
            "rimbalzo in fasi di eccesso ribassista. Questi elementi suggeriscono un miglioramento del sentiment "
            "tecnico, pur senza evidenziare ancora una vera inversione strutturale.\n\n"
            "Sul fronte della forza del trend, l’ADX a 32.6 indica la persistenza di un regime direzionale definito, "
            "con prevalenza ribassista: il –DI rimane superiore al +DI, nonostante quest’ultimo stia tentando un "
            "recupero. Ciò significa che il rimbalzo attuale, sebbene tecnicamente supportato dagli oscillatori, si "
            "inserisce all’interno di una tendenza predominante ancora orientata verso il basso. L’espansione dello "
            "spazio verso la banda superiore (+7.72%) conferma potenziale ulteriore per movimenti di recupero, ma il "
            "rischio di pullback resta elevato.\n\n"
            "La volatilità misurata da ATR (0.357, pari al 2.6%) suggerisce un livello di rischio moderato, mentre i "
            "livelli di equilibrio del Chandelier Exit (CE Long: 13.563 e CE Short: 13.892) indicano un prezzo attuale "
            "molto vicino ai valori tecnici di transizione, con un leggero vantaggio per la componente di rimbalzo. La "
            "presenza del segnale MCS BULL IMPROVING conferma un miglioramento dell’impostazione di breve periodo, pur "
            "restando all’interno di una cornice ribassista ampia e non ancora compromessa.\n\n"
            "In sintesi, Amplifon mostra un mix complesso: momentum in miglioramento, oscillatori in recupero, volumi "
            "forti e un ADX ancora ben orientato al ribasso. Lo scenario può evolvere positivamente se il prezzo "
            "riuscirà a riconquistare in modo stabile le medie principali e invertire il predominio del –DI.\n\n"
            "📌 Outlook: Neutrale / Rialzista di breve, ancora Ribassista nel medio\n"
            "📌 Setup Long: Possibile ma non confermato\n"
            "📌 Livelli da monitorare: 13.89 (CE Short), 13.56 (CE Long)\n\n"
            "🧠 Conclusione Finale\n"
            "Il titolo mostra segnali convincenti di miglioramento del momentum (MACDH positivo, RSI in recupero, "
            "stocastico forte), ma non ha ancora invertito il trend ribassista dominante. La struttura resta fragile "
            "e influenzata dalla pressione del –DI nonostante l’aumento dei volumi.\n\n"
            "👉 Short ancora OK nel medio periodo\n"
            "👉 Long prematuro: consentito solo come rimbalzo speculativo\n"
            "👉 Scenario in miglioramento ma NON ancora confermato\n"
        )
        user = (
            f"Scrivi in italiano.\n\n"
            f"Genera un COMMENTO TECNICO DISCORSIVO in stile 'GenAI Insight — Versione Long'.\n\n"
            f"FORMATO OBBLIGATORIO:\n"
            f"1️⃣ Titolo iniziale: '📘 GenAI Insight — Versione Long'\n"
            f"2️⃣ (Facoltativo ma preferito) una riga con 'TICKER | Nome' se nel JSON è presente anche il nome.\n"
            f"3️⃣ 3–5 paragrafi narrativi, senza bullet, che commentano trend, momentum, ADX, volatilità, "
            f"volumi vs medie, eventuali indicatori compositi (TechScore, MCS, segnali S6) e livelli di CE.\n"
            f"4️⃣ Chiusura con 3 righe obbligatorie nel formato:\n"
            f"   📌 Outlook: ...\n"
            f"   📌 Setup Long: ...\n"
            f"   📌 Livelli da monitorare per eventuale ingresso o uscita se dentro: ...\n"
            f"   📌 Indicazione di trading Buy, Exit, Hold: ...\n"
            f"5️⃣ Sezione finale obbligatoria: '🧠 Conclusione Finale'\n"
            f"   - Deve contenere 2–4 frasi di sintesi operativa NON vincolante.\n"
            f"   - Può includere brevi bullet con emoji 👉 per esprimere valutazioni come:\n"
            f"       'trend non confermato', 'long prematuro', 'scenario in miglioramento',\n"
            f"       'dominanza ribassista', 'struttura in consolidamento', ecc.\n"
            f"   - Deve contenere Buy/Sell/Hold  espliciti per indicare all'utente cosa fare.\n\n"
            f"STILE OBBLIGATORIO:\n"
            f"- Professionale, editoriale, fluido, coerente.\n"
            f"- Nessuna inventata di numeri: usa solo ciò che appare nei dati.\n"
            f"- Lunghezza massima: {max_words} parole.\n\n"
            f"Esempio di stile (da imitare nel tono, NON nei valori):\n\n"
            f"{example_long}\n\n"
            f"Ora genera un nuovo commento per:\n"
            f"Ticker: {ticker}\n\n"
            f"SNAPSHOT (ultima barra):\n{snapshot_json}\n\n"
            f"SERIES_TAIL (ultime {n_bars} barre):\n{tail_json}\n"
        )
        return {"system": system, "user": user}



    # ---------- LLM wrappers ----------
    def get_completion_from_messages(self,
                                     system_content: str,
                                     user_content: str,
                                     temperature: Optional[float] = None,
                                     show_io: bool = False,
                                     include_payload: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any]]:
        """
        If show_io=False: returns the model's text output.
        If show_io=True: returns a dict with output_text, system, user, and payload (if provided).
        """
        client = self._ensure_client(temperature)
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ]
        result = client.invoke(messages)
        text = result.content

        if show_io:
            return {
                "output_text": text,
                "system": system_content,
                "user": user_content,
                "payload": include_payload if include_payload is not None else None
            }
        return text

    def analyze_payload(self,
                        payload: Dict[str, Any],
                        max_words: int = 120,
                        temperature: Optional[float] = None,
                        show_io: bool = False) -> Union[str, Dict[str, Any]]:
        prompts = self._build_prompt(payload, max_words=max_words)
        return self.get_completion_from_messages(
            prompts["system"],
            prompts["user"],
            temperature=temperature,
            show_io=show_io,
            include_payload=payload if show_io else None
        )

    # ---------- simple public API usata dall'applicazione WEB ----------
    def analyze(self,
                ticker_or_list: Union[str, List[str]],
                max_words: int = 120,
                temperature: Optional[float] = None,
                save_payload_path: Optional[str] = None,
                save_results_path: Optional[str] = None,
                show_io: bool = False) -> Dict[str, Union[str, Dict[str, Any]]]:
        """
        Analyze 1 ticker or a list of tickers.
        Returns:
          - if show_io=False: {ticker: "llm text"}
          - if show_io=True:  {ticker: {output_text, system, user, payload}}
        """
        tickers = [ticker_or_list] if isinstance(ticker_or_list, str) else list(ticker_or_list)

        # Build payloads
        payloads = self.build_payloads(tickers)

        # Save payloads if requested
        if save_payload_path:
            os.makedirs(os.path.dirname(save_payload_path), exist_ok=True)
            with open(save_payload_path, "w", encoding="utf-8") as f:
                json.dump(payloads, f, ensure_ascii=False, indent=2)

        # LLM calls
        results: Dict[str, Union[str, Dict[str, Any]]] = {}
        for p in payloads:
            t = p.get("ticker", "N/A")
            try:  #Questa e` la funzione che viene chiamata per triggerare LLM - > all'interno di questa funzione
                  #viene costruito il prompt e poi invocata get_completion_from_message che invoca la LLM
                out = self.analyze_payload(
                    p,
                    max_words=max_words,
                    temperature=temperature,
                    show_io=show_io
                )
                results[t] = out
            except Exception as e:
                results[t] = f"[ERR] {e}"

        # Save results if requested
        if save_results_path:
            os.makedirs(os.path.dirname(save_results_path), exist_ok=True)
            with open(save_results_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return results

    def summarize_filtered_market(
            self,
            market: str,
            df_filtered: "pd.DataFrame",
            *,
            top_n: int = 15,
            max_words: int = 320,
            temperature: Optional[float] = None,
            show_io: bool = False,
    ) -> "Union[str, Dict[str, Any]]":
        """
        Report market-wide sui titoli già filtrati/ordinati, usando SOLO i dati nel DataFrame.

        Output stile:
        ✅ TITOLI DA COMPRARE (BUY)
        👀 WATCHLIST
        ❌ DA EVITARE

        Per ogni ticker: motivazione multi-indicatore + livelli Entry/Stop/TP1/TP2 + mini-strategia.
        """
        import json
        import pandas as pd
        from datetime import date

        if df_filtered is None or df_filtered.empty:
            return "Nessun titolo soddisfa i filtri: dataset vuoto."

        dff = df_filtered.head(int(top_n)).copy()

        cols_wanted = [
            "Date", "Ticker", "Name", "Category",
            # price
            "Close", "Open", "High", "Low",
            # Momentum / trend
            "MACD", "MACD_Signal", "MACD_Hist", "MACDH_Trend", "MACDH_Trend_Days",
            "MACD_vs_Signal",
            "RSI", "RSI_Trend", "RSI_Trend_Days",
            "Stoch_K", "Stoch_D", "SK_Trend", "SK_Trend_Days",
            # Trend strength
            "ADX", "PLUS_DI", "MINUS_DI", "ADX_Strong", "ADX_Trend", "ADX_Cross",
            # Risk / volatility
            "ATR", "ATR_PCT", "ATR_Upper", "ATR_Lower", "CE_Long", "CE_Short",
            "ATR_Long_OK", "ATR_Short_OK",
            # Trend overlays
            "EMA_30", "EMA_50", "SAR_Above_Price",
            "Signal6", "Signal6_Trend_Days",
            # Composite
            "MCS", "MCS_Smoothed", "MCS_Conf",
            "TECH_SCORE",
            # Performance / volume
            "PCTV_1D", "PCTV_5D", "PCTV_10D", "PCTV_30D", "PCTV_180D",
            "Vol_Perc_vs_MA20", "Vol_Perc_vs_MA5", "Volume",
            "Liquidity",
        ]
        cols_present = [c for c in cols_wanted if c in dff.columns]

        def _to_jsonable(v):
            if pd.isna(v):
                return None
            if isinstance(v, (pd.Timestamp, pd.Timedelta)):
                return str(v)
            try:
                return v.item()
            except Exception:
                return v

        rows = []
        for _, r in dff[cols_present].iterrows():
            rows.append({c: _to_jsonable(r.get(c)) for c in cols_present})

        payload = {
            "as_of": date.today().isoformat(),
            "market": market,
            "top_n": int(top_n),
            "columns_included": cols_present,
            "rows": rows,
            "rules": {
                "no_dup_tickers": True,
                "use_only_json": True,
                "must_output_levels": True
            }
        }

        system = (
            "Sei un analista tecnico e risk manager. Scrivi in italiano. "
            "Usa SOLO i dati presenti nel JSON. "
            "Non inventare numeri, livelli o indicatori mancanti. "
            "Se un dato manca, non citarlo e usa alternative presenti."
        )

        user = (
                f"Genera un report operativo sui titoli forniti per il mercato {market}.\n\n"
                "OBIETTIVO:\n"
                "- Dividi i titoli in 3 sezioni: BUY / WATCHLIST / AVOID.\n"
                "- Ogni ticker deve comparire UNA SOLA VOLTA in UNA SOLA sezione.\n\n"

                "FORMATO OBBLIGATORIO:\n"
                "✅ TITOLI DA COMPRARE (BUY)\n"
                "👀 WATCHLIST\n"
                "❌ TITOLI DA EVITARE\n\n"

                "PER OGNI TICKER (FORMATO FISSO):\n"
                "1) Riga titolo: 'TICKER (Nome)'\n"
                "2) Riga sintesi indicatori (comma-separated) scegliendo SOLO campi presenti:\n"
                "   - Trend: Trend/Signal6/EMA_30/EMA_50/SAR_Above_Price/ADX/PLUS_DI/MINUS_DI\n"
                "   - Momentum: MACD/MACD_Hist/MACD_vs_Signal/RSI/Stoch_K/Stoch_D/MCS\n"
                "   - Rischio: ATR/ATR_PCT/CE_Long/CE_Short/ATR_Long_OK\n"
                "   - Volume/Perf: Volume/Vol_Perc_vs_MA20/Vol_Perc_vs_MA5/PCTV_5D/10D/30D/Liquidity\n"
                "3) Livelli operativi (SEMPRE):\n"
                "   - Entry: (zona o trigger)\n"
                "   - Stop: (preferibilmente vicino a CE_Long o usando ATR)\n"
                "   - Target 1:\n"
                "   - Target 2:\n"
                "   Se hai CE_Long/CE_Short e Close, usa quelli come ancoraggi. "
                "   Altrimenti usa ATR_Upper/ATR_Lower. "
                "   Se nulla è disponibile, scrivi 'Livelli non disponibili'.\n"
                "4) Mini-strategia 1 riga che dica come eseguire:\n"
                "   - 'Buy on dip verso CE_Long' oppure 'Buy breakout sopra …' oppure 'Hold in watchlist finché …'\n\n"

                "REGOLE DI CLASSIFICAZIONE (usa SOLO indicatori del JSON):\n"
                "- BUY: Trend Bullish o Signal6 in ripartenza (wakeup/uptrend), momentum positivo "
                "(MACD_vs_Signal > 0 o MACD_Hist in miglioramento), rischio accettabile (ATR_Long_OK True o ATR_PCT non eccessivo) "
                "e preferibilmente volumi/vol_ratio non negativi.\n"
                "- WATCHLIST: segnali misti oppure trend giovane (ADX basso) o momentum non ancora confermato.\n"
                "- AVOID: Trend Bearish/Signal6 Downtrend o momentum negativo persistente o ATR_Long_OK False.\n\n"

                "VINCOLO: non basarti solo su MACD. "
                "Per ogni ticker devi citare almeno 3 famiglie tra Trend, Momentum, Rischio, Volume/Perf.\n\n"

                f"Massimo {max_words} parole.\n\n"
                "JSON:\n" + json.dumps(payload, ensure_ascii=False)
        )

        return self.get_completion_from_messages(
            system_content=system,
            user_content=user,
            temperature=temperature,
            show_io=show_io,
            include_payload=payload if show_io else None
        )

    def summarize_filtered_market_structured(
            self,
            market: str,
            df_filtered: "pd.DataFrame",
            *,
            top_n: int = 25,
            max_words: int = 700,
            temperature: "Optional[float]" = None,
            show_io: bool = False,
    ) -> "Union[str, Dict[str, Any]]":
        """
        Genera un report TRADING OPERATIVO in italiano con struttura fissa:

        ✅ BUY
        👀 WATCHLIST
        ❌ AVOID

        Per ogni ticker:
          - Prezzo attuale (Close)
          - Entry (pullback) + distanza
          - Entry (breakout) + distanza (se sensato)
          - Stop
          - Target 1
          - Target 2
          - Mini-strategia 1 riga

        Usa SOLO i dati del DataFrame (Excel). Non inventa numeri mancanti.
        """
        import json
        import pandas as pd
        from datetime import date

        if df_filtered is None or df_filtered.empty:
            return "Nessun titolo soddisfa i filtri: dataset vuoto."

        dff = df_filtered.head(int(top_n)).copy()

        # Colonne (include Close + ATR_Upper/Lower per livelli)
        cols_wanted = [
            "Date", "Ticker", "Name", "Category",

            # Price
            "Close", "Adj Close", "Open", "High", "Low",

            # Trend / momentum
            "ADX", "ADX_Strong", "ADX_Trend", "ADX_Cross", "PLUS_DI", "MINUS_DI",
            "Signal6", "Signal6_Trend_Days",
            "MACD", "MACD_Signal", "MACD_Hist", "MACDH_Trend", "MACDH_Trend_Days",
            "MACD_vs_Signal",
            "RSI", "RSI_Trend", "RSI_Trend_Days",
            "Stoch_K", "Stoch_D", "SK_Trend", "SK_Trend_Days",

            # Risk / levels
            "ATR", "ATR_PCT", "ATR_Upper", "ATR_Lower",
            "CE_Long", "CE_Short", "ATR_Long_OK", "ATR_Short_OK",

            # Composite
            "MCS", "MCS_Smoothed", "MCS_Conf",
            "TECH_SCORE",

            # Volume/perf (opzionali)
            "PCTV_1D", "PCTV_5D", "PCTV_10D", "PCTV_30D",
            "Vol_Perc_vs_MA20", "Vol_Perc_vs_MA5", "Volume",
            "Liquidity",
        ]
        cols_present = [c for c in cols_wanted if c in dff.columns]

        # json-safe
        def _to_jsonable(v):
            if pd.isna(v):
                return None
            if isinstance(v, (pd.Timestamp, pd.Timedelta)):
                return str(v)
            try:
                return v.item()
            except Exception:
                return v

        rows = []
        for _, r in dff[cols_present].iterrows():
            rows.append({c: _to_jsonable(r.get(c)) for c in cols_present})

        payload = {
            "as_of": date.today().isoformat(),
            "market": market,
            "top_n": int(top_n),
            "columns_included": cols_present,
            "rows": rows
        }

        system = (
            "Sei un analista tecnico e risk manager. Scrivi in italiano. "
            "Usa SOLO i dati nel JSON. Non inventare prezzi o livelli. "
            "Se un campo manca, scrivi 'n/a' e non stimare. "
            "Devi produrre un output operativo e ripetibile."
        )

        # ESEMPIO (come lo vuoi tu)
        example = (
            "ESEMPIO DI OUTPUT (solo per capire il formato — NON usare questi numeri):\n"
            "✅ BUY\n"
            "🥇 ABC.MI (Esempio Spa)\n"
            "- Prezzo attuale (Close): 64.52\n"
            "- Entry (pullback): 61.00–62.00  | distanza: -3.52 / -2.52\n"
            "- Entry (breakout): > 65.00      | distanza: +0.48\n"
            "- Stop: 59.70\n"
            "- Target 1: 67.70\n"
            "- Target 2: 72.00\n"
            "👉 Strategia: buy on dip verso CE_Long; parziale a T1, trailing sotto ATR/CE_Long.\n\n"
            "👀 WATCHLIST\n"
            "XYZ.MI (Altro Nome)\n"
            "- Prezzo attuale (Close): 41.07\n"
            "- Entry (breakout): > 43.30 | distanza: +2.23\n"
            "- Stop: 39.20\n"
            "- Target 1: 45.00\n"
            "- Target 2: n/a\n"
            "👉 Strategia: attendi conferma sopra CE_Short; niente ingresso in congestione.\n\n"
            "❌ AVOID\n"
            "BAD.MI (Titolo Debole)\n"
            "- Prezzo attuale (Close): 1.23\n"
            "👉 Strategia: evita long finché ATR_Long_OK non torna True e trend non gira.\n"
        )

        user = (
                f"Genera un report di TRADING OPERATIVO per il mercato {market} usando i titoli nel JSON.\n\n"
                "OBIETTIVO:\n"
                "- Dividi i titoli in 3 sezioni: ✅ BUY, 👀 WATCHLIST, ❌ AVOID.\n"
                "- Ogni ticker deve comparire UNA SOLA VOLTA in UNA SOLA sezione (vietate ripetizioni).\n"
                "- Usa indicatori MULTIPLI: Trend (ADX_Trend/Signal6), Momentum (MACD_vs_Signal/MACD_Hist/RSI/MCS), "
                "Rischio (ATR/ATR_PCT/ATR_Long_OK) e, se disponibili, volume/performance.\n\n"
                f"{example}\n\n"
                "REGOLE DI CLASSIFICAZIONE (coerenti con setup long):\n"
                "- ✅ BUY: ATR_Long_OK = True (se presente) AND (ADX_Trend contiene 'Bull' OR Signal6 contiene 'Uptrend'/'wakeup') "
                "AND momentum non negativo (MACD_vs_Signal > 0 OR MACD_Hist trend Up OR RSI_Trend Up).\n"
                "- 👀 WATCHLIST: segnali misti o reversal non confermato (es. Signal6 contiene 'rev' o ADX_Trend Bearish ma momentum migliora).\n"
                "- ❌ AVOID: ATR_Long_OK = False OR trend chiaramente Bearish/Downtrend con momentum debole.\n"
                "Se sei indeciso, scegli SEMPRE la categoria più prudente.\n\n"
                "PER OGNI TICKER — FORMATO OBBLIGATORIO:\n"
                "Riga 1: 'TICKER (Nome)'\n"
                "Riga 2: '- Prezzo attuale (Close): <numero>' (usa Close se presente, altrimenti Adj Close; se manca: n/a)\n"
                "Riga 3: Livelli:\n"
                "  - Entry (pullback): usa CE_Long se presente; altrimenti usa ATR_Lower o scrivi n/a.\n"
                "  - Entry (breakout): usa CE_Short se presente; altrimenti (Close + 0.5*ATR) se ATR presente; altrimenti n/a.\n"
                "  - Stop: preferibilmente ATR_Lower o CE_Long; altrimenti (Close - 1.2*ATR) se ATR presente; altrimenti n/a.\n"
                "  - Target 1: preferibilmente CE_Short; altrimenti ATR_Upper; altrimenti (Close + 1.5*ATR) se ATR presente; altrimenti n/a.\n"
                "  - Target 2: preferibilmente ATR_Upper; altrimenti (Close + 2.5*ATR) se ATR presente; altrimenti n/a.\n"
                "Riga 4: per Entry pullback e breakout, aggiungi sempre 'distanza' dal prezzo attuale:\n"
                "  distanza = Entry - Close (mostra segno + o -). Se è un range, mostra entrambi i lati.\n"
                "Riga 5: '👉 Strategia: ...' una sola frase operativa (pullback vs breakout, take profit parziale, trailing).\n\n"
                "VINCOLI:\n"
                f"- Max {max_words} parole\n"
                "- Non inventare numeri\n"
                "- Non citare colonne non presenti nel JSON\n\n"
                "JSON:\n"
                + json.dumps(payload, ensure_ascii=False)
        )

        return self.get_completion_from_messages(
            system_content=system,
            user_content=user,
            temperature=temperature,
            show_io=show_io,
            include_payload=payload if show_io else None
        )

    def summarize_entry_now_structured(
            self,
            market: str,
            df_filtered: "pd.DataFrame",
            *,
            top_n: int = 25,
            max_words: int = 550,
            temperature: "Optional[float]" = None,
            show_io: bool = False,
    ) -> "Union[str, Dict[str, Any]]":
        """
        Genera un report OPERATIVO "posso entrare ora?" con struttura fissa:

        ✅ ENTRABILI ORA (a mercato)
        ⚠️ ENTRABILI ORA MA SOLO PARZIALI / AGGRESSIVI
        ❌ NON ENTRARE ORA (attendere livelli)

        Per ogni ticker:
          - Prezzo attuale (Close o Adj Close)
          - Entry NOW (range o prezzo singolo) + distanza dal prezzo attuale
          - Se NON entrare ora: livelli da guardare (Entry pullback / Entry breakout) + distanza
          - Stop loss
          - Target 1 / Target 2
          - 1 riga strategia

        Usa SOLO i dati presenti nel JSON. Se mancano campi, scrivi n/a e non stimare.
        """
        import json
        import pandas as pd
        from datetime import date

        if df_filtered is None or df_filtered.empty:
            return "Nessun titolo soddisfa i filtri: dataset vuoto."

        dff = df_filtered.head(int(top_n)).copy()

        cols_wanted = [
            "Date", "Ticker", "Name", "Category",

            # Price
            "Close", "Adj Close",

            # Trend / momentum
            "ADX", "ADX_Strong", "ADX_Trend", "ADX_Cross",
            "Signal6", "Signal6_Trend_Days",
            "MACD", "MACD_Signal", "MACD_Hist", "MACDH_Trend", "MACDH_Trend_Days",
            "MACD_vs_Signal",
            "RSI", "RSI_Trend", "RSI_Trend_Days",

            # Risk / levels
            "ATR", "ATR_PCT", "ATR_Upper", "ATR_Lower",
            "CE_Long", "CE_Short", "ATR_Long_OK",

            # Composite
            "MCS", "TECH_SCORE",

            # opzionali
            "PCTV_5D", "PCTV_30D", "Volume", "Vol_Perc_vs_MA20", "Liquidity",
        ]
        cols_present = [c for c in cols_wanted if c in dff.columns]

        def _to_jsonable(v):
            if pd.isna(v):
                return None
            if isinstance(v, (pd.Timestamp, pd.Timedelta)):
                return str(v)
            try:
                return v.item()
            except Exception:
                return v

        rows = []
        for _, r in dff[cols_present].iterrows():
            rows.append({c: _to_jsonable(r.get(c)) for c in cols_present})

        payload = {
            "as_of": date.today().isoformat(),
            "market": market,
            "top_n": int(top_n),
            "columns_included": cols_present,
            "rows": rows
        }

        system = (
            "Sei un analista tecnico e risk manager. Scrivi in italiano. "
            "Usa SOLO i dati nel JSON. Non inventare numeri o livelli. "
            "Se un dato manca scrivi 'n/a'. "
            "Output operativo, breve e ripetibile."
        )

        example = (
            "ESEMPIO DI OUTPUT (solo formato — NON usare questi numeri):\n"
            "✅ ENTRABILI ORA (a mercato)\n"
            "MB.MI (Mediobanca)\n"
            "- Prezzo attuale (Close): 17.49\n"
            "- Entry ORA: 17.40–17.60 | distanza: -0.09 / +0.11\n"
            "- Stop: 16.28\n"
            "- Target 1: 18.10\n"
            "- Target 2: 18.69\n"
            "👉 Strategia: entra parziale ora, aggiungi su pullback verso CE_Long, parziale a T1.\n\n"
            "⚠️ ENTRABILI ORA MA SOLO PARZIALI / AGGRESSIVI\n"
            "BPSO.MI (Banca Popolare di Sondrio)\n"
            "- Prezzo attuale (Close): 16.52\n"
            "- Entry ORA: 16.45–16.60 | distanza: -0.07 / +0.08\n"
            "- Stop: 15.18\n"
            "- Target 1: 17.54\n"
            "- Target 2: 18.70\n"
            "👉 Strategia: RSI alto: solo size ridotta; meglio attendere pullback su CE_Long.\n\n"
            "❌ NON ENTRARE ORA (attendere livelli)\n"
            "DIA.MI (Diasorin)\n"
            "- Prezzo attuale (Close): 64.52\n"
            "- Entry (pullback): 61.00–62.00 | distanza: -3.52 / -2.52\n"
            "- Entry (breakout): > 65.00 | distanza: +0.48\n"
            "- Stop: 59.70\n"
            "- Target 1: 67.70\n"
            "- Target 2: 72.00\n"
            "👉 Strategia: non inseguire; entra solo su pullback o breakout confermato.\n"
        )

        user = (
                f"Genera un report 'POSSO ENTRARE ORA?' per il mercato {market} usando SOLO i dati nel JSON. Vorrei vedere anche"
                f"i titoli buoni da non entrare ora per i quali indichi i livelli ad esempio da attendere per entrare con un pullback\n\n"
                "OBIETTIVO:\n"
                "- Dividi i ticker in 3 sezioni: ✅ ENTRABILI ORA, ⚠️ ENTRABILI ORA MA SOLO PARZIALI/AGGRESSIVI, ❌ NON ENTRARE ORA.\n"
                "- Ogni ticker deve comparire UNA sola volta.\n"
                "- Non scrivere market summary discorsivi: voglio livelli e distanza.\n\n"
                f"{example}\n\n"
                "CRITERI (prudenti) PER 'ENTRABILI ORA':\n"
                "- ✅ ENTRABILI ORA: trend/momentum favorevoli (ADX_Trend contiene 'Bull' oppure Signal6 contiene 'Uptrend'/'wakeup'), "
                "ATR_Long_OK True (se presente), e prezzo vicino a una zona d'ingresso sensata.\n"
                "- ⚠️ ENTRABILI ORA MA SOLO PARZIALI/AGGRESSIVI: trend ok ma prezzo tirato (es. RSI alto, distanza grande da CE_Long, "
                "oppure trend giovane/pausa tipo 'sleep').\n"
                "- ❌ NON ENTRARE ORA: trend Bearish/Downtrend o reversal non confermato; qui devi indicare chiaramente i livelli da guardare.\n"
                "Se sei indeciso, scegli la categoria più prudente.\n\n"
                "PER OGNI TICKER — FORMATO OBBLIGATORIO:\n"
                "1) 'TICKER (Nome)'\n"
                "2) '- Prezzo attuale (Close): X' (usa Close se presente, altrimenti Adj Close)\n"
                "3) Se ✅ o ⚠️: '- Entry ORA: <range o prezzo> | distanza: ...'\n"
                "   Se ❌: '- Entry (pullback): ... | distanza: ...' e '- Entry (breakout): ... | distanza: ...'\n"
                "4) '- Stop: ...'\n"
                "5) '- Target 1: ...'\n"
                "6) '- Target 2: ...'\n"
                "7) '👉 Strategia: ...' una sola frase\n\n"
                "COME CALCOLARE I LIVELLI (usa SOLO se disponibili):\n"
                "- Entry pullback: vicino a CE_Long (se presente) altrimenti ATR_Lower.\n"
                "- Entry breakout: > CE_Short (se presente) altrimenti n/a.\n"
                "- Entry ORA: se il Close è molto vicino (entro ~0.5*ATR) a CE_Long o CE_Short, proponi un piccolo range attorno al Close; "
                "altrimenti NON proporre Entry ORA (mettilo in ❌ o ⚠️).\n"
                "- Stop: ATR_Lower o CE_Long.\n"
                "- Target 1: CE_Short.\n"
                "- Target 2: ATR_Upper.\n"
                "- Distanza: Entry - Close (se range mostra entrambi i lati).\n\n"
                "VINCOLI:\n"
                f"- Max {max_words} parole\n"
                "- Non inventare numeri\n"
                "- Non citare colonne non presenti nel JSON\n\n"
                "JSON:\n"
                + json.dumps(payload, ensure_ascii=False)
        )

        return self.get_completion_from_messages(
            system_content=system,
            user_content=user,
            temperature=temperature,
            show_io=show_io,
            include_payload=payload if show_io else None
        )

# ======== Example usage ========
#if __name__ == "__main__":
#    analyst = TAOpenAIAnalyst(
#        model="gpt-4o-mini",
#        temperature=0.0,
#        period="2y",
#        tail_bars=30
#    )

    # 1) Single ticker, normal output
    #out1 = analyst.analyze("AAPL", max_words=140, show_io=False)
    #print("\n=== AAPL (text only) ===\n", out1.get("AAPL", ""))

    # 2) Single ticker, with full I/O
    #out1_debug = analyst.analyze("AAPL", max_words=140, show_io=True)
    #print("\n=== AAPL (full I/O) ===\n", json.dumps(out1_debug["AAPL"], indent=2))

    # 3) Multiple tickers, full I/O
    #out_many = analyst.analyze(["MSFT", "NVDA"], max_words=140, show_io=True)
    #for tk, blob in out_many.items():
    #    print(f"\n=== {tk} (full I/O) ===\n{json.dumps(blob, indent=2)}")
