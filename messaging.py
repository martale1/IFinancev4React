import pandas as pd
import os
import json
from urllib import request, parse
from filehandling import  fileHandling
from pathlib import Path
from typing import Optional

try:
    import telepot  # type: ignore
except Exception:
    telepot = None


def _load_local_env_file() -> None:
    """
    Lightweight .env loader (no external dependency).
    Loads only missing vars from project .env.
    """
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_local_env_file()

TOKEN_ENV_BY_CHANNEL = {
    0: "TELEGRAM_BOT_TOKEN_CH0",
    1: "TELEGRAM_BOT_TOKEN_CH1",
    2: "TELEGRAM_BOT_TOKEN_CH2",
    3: "TELEGRAM_BOT_TOKEN_CH3",
    4: "TELEGRAM_BOT_TOKEN_CH4",
    5: "TELEGRAM_BOT_TOKEN_CH5",
}

DEFAULT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN_DEFAULT"
RECEIVER_ENV = "TELEGRAM_RECEIVER_ID"


class messaging:
    def __init__(self, chatTarget=0):
        target = int(chatTarget)
        env_name = TOKEN_ENV_BY_CHANNEL.get(target, DEFAULT_TOKEN_ENV)
        token = os.getenv(env_name) or os.getenv(DEFAULT_TOKEN_ENV)

        if not token:
            raise ValueError(
                f"Telegram token mancante. Imposta {env_name} (o {DEFAULT_TOKEN_ENV}) nel file .env"
            )

        receiver_id = os.getenv(RECEIVER_ENV, "").strip()
        if not receiver_id:
            raise ValueError(f"Telegram receiver id mancante. Imposta {RECEIVER_ENV} nel file .env")

        self.token = token
        self.receiver_id = receiver_id

    #https://api.telegram.org /bot6545897515:AAE6hz2p8vbaypT96kUVKHzotfs0wcjOhc4/getUpdates

    def send(self,testo):
        self._send_message(testo, parse_mode=None)

    def sendURLs(self,testo):
        self._send_message(testo + "\u200B", parse_mode="HTML")

    def _send_message(self, text: str, parse_mode: Optional[str] = None):
        if telepot is not None:
            bot = telepot.Bot(self.token)
            if parse_mode:
                return bot.sendMessage(self.receiver_id, text, parse_mode=parse_mode)
            return bot.sendMessage(self.receiver_id, text)

        # Fallback without telepot: direct Telegram Bot API call (stdlib only)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.receiver_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        data = parse.urlencode(payload).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"ok": False, "raw": body}
        if not parsed.get("ok", False):
            raise RuntimeError(f"Telegram API error: {parsed}")
        return parsed

    def sort_within_group(self,group, sort_column='Volume'):
        return group.sort_values(by=sort_column, ascending=True)

    def ordina(self,d, sort_column='Volume'):
        d_sorted = d.sort_values(by='Scoring', ascending=False)
        grouped = d.groupby(pd.cut(d['Scoring'], bins=range(-5, 5), labels=False))
        sorted_groups = grouped.apply(lambda x: self.sort_within_group(x, sort_column))
        # sorted_groups = grouped.apply(sort_within_group)
        sorted_groups = sorted_groups.iloc[::-1]
        sorted_dataframe = sorted_groups.reset_index(drop=True)
        return sorted_dataframe

    def sendSignals(self,market, volumeThreshold=1500, telegramChannel=4):
        print("Signals for market " + market)
        # Apre il file con i segnali
        fh = fileHandling()
        df = fh.fromXLSXToDF("Best_" + market + ".xlsx")

        #############################################################
        #    Signal reverse uptrend with Alligator #
        #    Signal3: Price crossing the teeth
        #############################################################
        print("**************************************************************************")
        priceCrossingTeeth = df[((df['Signal3'] == 1)) & (df['Volume'] > volumeThreshold)]
        priceCrossingTeeth_sorted = priceCrossingTeeth.sort_values(by='Percent_Change_2', ascending=False)
        # Stampa le voci ordinate
        print("s3 Alligator signals price crossing the teeth:")
        print(priceCrossingTeeth.head(20).to_string())
        # Invia telegram
        self.sendTickerList(market + ": S3 Price crossing the teeth:", priceCrossingTeeth_sorted.head(20), 0,
                       telegramChannel)

        #############################################################
        #    Signal reverse uptren with Alligator #
        #    Signal4:Lips(Green) > Teeth(Red) and Lips(Green) < Jaw (Blu)
        #############################################################
        print("**************************************************************************")
        # | (df['Signal5'] == 1)
        LipsBetweenTeethAndJaw = df[((df['Signal4'] == 1)) & (df['Volume'] > volumeThreshold)]
        LipsBetweenTeethAndJaw_sorted = LipsBetweenTeethAndJaw.sort_values(by='Percent_Change_2', ascending=False)
        # Stampa le voci ordinate
        print("s4 Alligator signals:")
        print(LipsBetweenTeethAndJaw_sorted.head(20).to_string())
        # Invia telegram
        self.sendTickerList(market + ": S4 lips>teeth :", LipsBetweenTeethAndJaw_sorted.head(20), 0, telegramChannel)

        #############################################################
        #    Signal reverse boolinger #
        #    Signal5: Close>Upper Boolinger and previous 3 closes below upper Boolinger
        #############################################################
        print("**************************************************************************")
        priceAboveBoolingerUpper = df[((df['Signal5'] == 1)) & (df['Volume'] > volumeThreshold)]
        priceAboveBoolingerUpper_sorted = (priceAboveBoolingerUpper.sort_values(by='Percent_Change_2', ascending=False))
        # Stampa le voci ordinate
        print("s5 Boolinger signals:")
        print(priceAboveBoolingerUpper_sorted.head(20).to_string())
        # Invia telegram

        self.sendTickerList(market + ": S5 Close above Boolinger:", priceAboveBoolingerUpper_sorted.head(20), 0,
                       telegramChannel)



    def sendTickerList(self,market, df, executionTime, telegramChannel):
        filtered_df = df
        if len(df):
            sorted_df = df
            telegram_message = market + "\nStocks: " + str(len(filtered_df)) + "\n\n"
            telegram_message_simplified = market + " Trending stocks: " + str(len(filtered_df)) + "\n\n"
            for index, entry in sorted_df.iterrows():
                tname = entry['Ticker Name']
                ticker = entry['Ticker']
                volume = entry['Volume']
                pct2 = entry['Percent_Change_2']
                close = entry['Close']
                scoring = entry['Scoring']
                sl = entry['ATR_Trailing_Stop_Loss']
                atr = entry['ATR']
                AI = entry['AI']
                ADX = entry['ADX']
                RSI = entry['RSI']
                MACD = entry['MACD']
                MACDS = entry['MACD_Signal']
                MACD_Histogram = entry['MACD_Histogram']
                K = entry['Stochastic_K']
                D = entry['Stochastic_D']
                cplus = entry['cdlplus']
                cminus = entry['cdlminus']
                ticker = ticker.strip()
                candlespattern = entry['candlespattern']
                signal6=entry['Signal6']
                if (
                        'pippo' in market):  # Here you should put MylList, MIB, ETC, etc to trigger the candlestick pattern in the telegram message
                    # print("################## MIA LISTA ###########")
                    patternName = 'P:'

                else:
                    # print("%%%%%%%%%%%% Non e` la mia lista:"+market)
                    patternName = ''
                    candlespattern = ''
                # Genera il link HTML
                #url = f"<a href='https://it.finance.yahoo.com/quote/{ticker}/'>{ticker}</a>"
                url = f"<a href='http://theoiziruam.ddns.net:8503/?ticker={ticker}&scoring={scoring}&signal6={signal6}'>{ticker}</a>"
                #url=  f"<a http://theoiziruam.ddns.net:8503/?ticker={ticker}</a>"

                # print(url)
                # url = f"<a href='https://it.finance.yahoo.com/quote/{ticker}/'>{ticker}</a>"
                asterisk = ''
                if scoring == 4:
                    asterisk = '$$$$ '
                elif scoring == 3:
                    asterisk = '$$$ '
                elif scoring == 2:
                    asterisk = '$$ '
                elif scoring == 1:
                    asterisk = '$ '
                elif scoring == -4:
                    asterisk = '@@@@ '
                elif scoring == -3:
                    asterisk = '@@@ '
                elif scoring == -2:
                    asterisk = '@@ '
                elif scoring == -1:
                    asterisk = '@ '
                # print(f"Telegram channel {telegramChannel}")
                if (AI == None):
                    if (telegramChannel == 4):
                        entry_message = f"{asterisk}{tname} {url} c+:{cplus} c-:{cminus} Histogram:{MACD_Histogram} S_K:{K} V:{volume} p%:{pct2}%  S_D:{D} C:{close}  score:{scoring} SL:{sl}  MACD:{MACD} MACD_S:{MACDS}  RSI:{RSI}  ADX:{ADX}  {patternName} {candlespattern}\n\n"
                    else:
                        entry_message = f"{asterisk}{tname} {url} c+:{cplus} c-:{cminus} C:{close} V:{volume} p%:{pct2}%  score:{scoring} SL:{sl}  MACD:{MACD} MACD_S:{MACDS} S_K:{K} S_D:{D} RSI:{RSI}  ADX:{ADX} {patternName} {candlespattern} \n\n"
                else:
                    if (telegramChannel == 4):
                        entry_message = f"{asterisk}{tname} {url} c+:{cplus} c-:{cminus} Histogram:{MACD_Histogram} S_K:{K}  p%:{pct2}%  V:{volume} score:{scoring} C:{close}  SL:{sl}  MACD:{MACD} MACD_S:{MACDS}  S_D:{D} RSI:{RSI}  ADX:{ADX} {patternName} {candlespattern} AI:{AI} \n\n"
                    else:
                        entry_message = f"{asterisk}{tname} {url} c+:{cplus} c-:{cminus} Histogram:{MACD_Histogram} S_K:{K} C:{close} V:{volume} p%:{pct2}%  score:{scoring} SL:{sl}  MACD:{MACD} MACD_S:{MACDS}  S_D:{D} RSI:{RSI} ADX:{ADX} {patternName} {candlespattern} AI:{AI}\n\n"

                telegram_message += entry_message
                entry_message_simplified = f"{asterisk} {url}  p%:{pct2}% V:{volume} {tname}\n"
                telegram_message_simplified += entry_message_simplified
        else:
            telegram_message = market + " EMPTY"
            telegram_message_simplified = market + "EMPTY"
        telegram = messaging(chatTarget=telegramChannel)
        # print(telegram_message)
        # if(telegramChannel!=4): telegram_message +='Execution time:'+str(executionTime)+"s" #il canale 4 e` per i segnali, execution time non serve
        # telegram.sendURLs(telegram_message)
        if len(filtered_df):
            telegram.sendURLs(telegram_message_simplified)

    def sendTradingSystemsResultsWithScoring(self,d, executionTime, market, orderBy='Volume', firstXStocks=0,
                                             allScoringClasses=0, telegramChannel=0, telegramSend=0):
        # allScoring= 1=> All classes; 2 => Classes 4,3;  0 => Class  4 only
        # firstXStocks=0 visualizza tutto, altrimenti il valore indicato viene usato
        # telegramChannel: 0 (BestStocks/Watchlist), 1 (BuySignals/IT_ETC, MIB30), 2 (SellSignals/IT_ETF), 3 (US_stocks)
        # telegramSend: telegram message is sent only if this value is equh al to 1

        print("**** Function: sendTradingSystemsResultsWithScoring ***")
        df_ordered = self.ordina(d, sort_column=orderBy)  # Ordina per gruppo e poi per sort_colum all'interno del gruppo
        if allScoringClasses == 1:  # All classess are included
            print("-- Including all classes for telegram regadless the volume --")
            df_filtered = df_ordered  # Invalida precedente ordinamento ed ordina in base a variazioni percentuali
            df_filtered = df_filtered.sort_values(by='Percent_Change_2', ascending=False)
            a = 1
        elif allScoringClasses == 2:  # Class 4 and 3
            print("-- Including classes 4 and 3 with volume > 1000 for telegram--")
            df_filtered = df_ordered[
                ((df_ordered['Scoring'] == 4) | (df_ordered['Scoring'] == 3)) & (df_ordered['Volume'] > 1000)]
            # df_filtered = df_ordered[((df_ordered['Scoring'] == 4)  & (df_ordered['Volume'] > 1000)] #Scoring 4 and V>1000
            if len(df_filtered) == 0:
                df_filtered = df_ordered[
                    (df_ordered['Scoring'] == 3) & (df_ordered['Volume'] > 1000)]  # Scoring 4 and V>1000
        else:  # Only4
            print("-- Including classe 4 with  volume > 1000 for telegram  --")

            df_filtered = df_ordered[
                (df_ordered['Scoring'] == 4) & (df_ordered['Volume'] > 1000)]  # Scoring 4 and V>1000
            if len(df_filtered) == 0:
                df_filtered = df_ordered[
                    (df_ordered['Scoring'] == 3) & (df_ordered['Volume'] > 1000)]  # Scoring 4 and V>1000

        if firstXStocks:
            df_filtered = df_filtered.head(firstXStocks)
        print("Ordered scoring for " + market)
        print(df_ordered.to_string())
        if telegramSend:
            print("Items included in telegram message as Trading system result:")
            print(df_filtered.to_string())
            self.sendTickerList(market + ' ordered by ' + orderBy + '\n', df_filtered, executionTime,
                           telegramChannel)  # Invia messaggio telegram



    def sendSignalsAlligators(self,market, volumeThreshold=1000, telegramChannel=4):
        print("Signals for market " + market)

        # Apre il file con i segnali
        fh = fileHandling()
        df = fh.fromXLSXToDF("Best_" + market + ".xlsx")

        # Stampa il DataFrame per debug
        print(df.to_string())

        # Filtra il DataFrame per volume maggiore di 1000
        if 'Volume' in df.columns:
            df_filtered = df[df['Volume'] > volumeThreshold]
        else:
            print("La colonna 'Volume' non esiste nel DataFrame.")
            return

        filtered_df_uptrend = df_filtered[df_filtered['Signal6'] == 'Uptrend']
        sorted_df = filtered_df_uptrend.sort_values(by='Scoring', ascending=False)
        print(sorted_df.to_string())

        # Verifica se la colonna 'Signal6' esiste nel DataFrame filtrato
        if 'Signal6' in df_filtered.columns:
            # Conta le occorrenze di ciascun valore unico nella colonna 'Signal6'
            counts = df_filtered['Signal6'].value_counts()


            # Calcola il totale delle righe nel DataFrame filtrato
            total = len(df_filtered)

            # Calcola le percentuali per ogni valore unico
            percentages = round(((counts / total) * 100),2)

            # Crea un DataFrame con i risultati
            result_df = pd.DataFrame({
                'Count': counts,
                'Percentage': percentages
            })

            myDict=counts.to_dict()
            print(f"Numero entry in Uptrend: {myDict['Uptrend']}")


            # Riordina il DataFrame per i conteggi in ordine decrescente (opzionale)
            result_df = result_df.sort_values(by='Count', ascending=False)

            # Stampa il DataFrame dei risultati

            #sending summary to telegram
            # Prepare the 'testo' field to send
            testo = "Summary for market: {}\n\n".format(market)
            testo += "Signal6 Summary (Volume > {}):\n".format(volumeThreshold)
            testo += result_df.to_string(index=True, header=True)


            # If the DataFrame is large, you might want to add pagination or a brief summary instead
            if len(testo) > 4000:  # Telegram message limit is 4096 characters
                testo = testo[:4000] + "\n[Message truncated]"

            # Send the results via Telegram
            self.send(testo)
            #self.send(sorted_df.to_string())
        else:
            print("La colonna 'Signal6' non esiste nel DataFrame filtrato.")

    def send(self, testo):
        bot = telepot.Bot(self.token)
        bot.sendMessage(self.receiver_id, testo)

    def sendURLsWithFile(self, testo, image_filename=None):
        bot = telepot.Bot(self.token)

        if image_filename:
            # Definisci il percorso completo del file immagine nella cartella 'images'
            current_directory = os.getcwd()  # Ottieni la directory corrente
            images_directory = os.path.join(current_directory, 'images')  # Cartella 'images'
            image_path = os.path.join(images_directory, image_filename)  # Percorso completo dell'immagine

            # Verifica che il file esista prima di inviarlo
            if os.path.exists(image_path):
                with open(image_path, 'rb') as img_file:
                    bot.sendPhoto(self.receiver_id, img_file, caption=testo)
            else:
                print(f"Errore: Il file '{image_filename}' non esiste nella cartella 'images'.")
                bot.sendMessage(self.receiver_id, f"⚠️ Impossibile trovare il file: {image_filename}")

    def send_document(self, file_path, caption=""):
        import os
        import telepot

        bot = telepot.Bot(self.token)

        if not os.path.exists(file_path):
            print(f"⚠️ File non trovato: {file_path}")
            bot.sendMessage(self.receiver_id, f"⚠️ File non trovato: {file_path}")
            return

        try:
            with open(file_path, "rb") as f:
                bot.sendDocument(self.receiver_id, f, caption=caption)
        except Exception as e:
            print(f"Errore invio documento Telegram: {e}")

    def send_file(self, file_path):
        """
        Invia un file tramite Telegram.
        """
        bot = telepot.Bot(self.token)
        try:
            bot.sendPhoto(self.receiver_id, photo=open(file_path, 'rb'))
        except Exception as e:
            print(f"Errore durante l'invio del file: {e}")

    def load_market_excel(self, market: str, base_folder: str,
                          filename_suffix: str = "TA_Analyses.xlsx") -> pd.DataFrame:
        """
        Carica il file Excel di analisi tecnica per un mercato.
        Esempio path atteso: {base_folder}/{market}_TA_Analyses.xlsx
        """
        market = market.strip()
        file_path = os.path.join(base_folder, f"{market}_{filename_suffix}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File non trovato: {file_path}")

        df = pd.read_excel(file_path, sheet_name=0)
        df.columns = df.columns.astype(str).str.strip()  # normalizza spazi
        return df

    def send_uptrend_buyadd_summary(
            self,
            market: str,
            base_folder: str,
            telegramChannel: int = 1,
            max_list: int = 15,
            send_list: bool = True
    ):
        """
        Invia su Telegram un summary per mercato:
        - conta titoli con Market_Phase=UPTREND e Action in {BUY, ADD}
        - opzionalmente invia anche una lista tickers (con link HTML) limitata a max_list
        """
        df = self.load_market_excel(market=market, base_folder=base_folder)

        # colonne richieste
        required = ["Ticker", "Market_Phase", "Action"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"Colonne mancanti nel file {market}: {missing}")

        # normalizza stringhe
        df["Market_Phase"] = df["Market_Phase"].astype(str).str.upper().str.strip()
        df["Action"] = df["Action"].astype(str).str.upper().str.strip()

        # filtro target
        df_hit = df[(df["Market_Phase"] == "UPTREND") & (df["Action"].isin(["BUY"]))].copy()

        n_total = len(df)
        n_hit = len(df_hit)


        # prepara testo summary
        testo = (
            f"📌 Market: {market}\n"
            f"Totale titoli: {n_total}\n"
            f"UPTREND & (BUY): {n_hit}\n"
        )

        # qualche extra utile se esistono
        extra_cols = []
        for c in ["Close", "TECH_SCORE", "Liquidity"]:
            if c in df.columns:
                extra_cols.append(c)

        # ordina lista: prima BUY poi ADD, e poi TECH_SCORE desc se esiste
        if n_hit and "TECH_SCORE" in df_hit.columns:
            df_hit = df_hit.sort_values(by=["Action", "TECH_SCORE"], ascending=[True, False])
        elif n_hit:
            df_hit = df_hit.sort_values(by=["Action", "Ticker"], ascending=[True, True])

        telegram = messaging(chatTarget=telegramChannel)

        # manda summary
        telegram.send(testo)

        # manda lista tickers (html link) se richiesto
        if send_list and n_hit:
            df_send = df_hit.head(max_list).copy()

            # costruisci un messaggio HTML semplice con link come già fai
            righe = []
            for _, r in df_send.iterrows():
                ticker = str(r["Ticker"]).strip()
                name = str(r["Name"]).strip() if "Name" in df_send.columns and pd.notna(r.get("Name")) else ""

                action = str(r.get("Action", "")).strip().upper()

                # numeri (gestione NaN)
                close_val = r.get("Close", None)
                score_val = r.get("TECH_SCORE", None)
                vol_val = r.get("Volume", None)
                p1d_val = r.get("PCTV_1D", None)
                p5d_val = r.get("PCTV_5D", None)

                close = f"{float(close_val):.2f}" if close_val is not None and pd.notna(close_val) else ""
                score = f"{float(score_val):.0f}" if score_val is not None and pd.notna(score_val) else ""
                volume = f"{int(vol_val):,}".replace(",", ".") if vol_val is not None and pd.notna(
                    vol_val) else ""  # 12.345 stile IT
                p1d = f"{float(p1d_val):.2f}%" if p1d_val is not None and pd.notna(p1d_val) else ""
                p5d = f"{float(p5d_val):.2f}%" if p5d_val is not None and pd.notna(p5d_val) else ""

                # link
                #url = f"<a href='http://theoiziruam.ddns.net:8503/?ticker={ticker}'>{ticker}</a>"
                url = f"<a href='http://theoiziruam.ddns.net:8503/?market={market}&ticker={ticker}'>{ticker}</a>"
                #url = f"<a href='http://192.168.68.116:8501/?market={market}&ticker={ticker}'>{ticker}</a>"

                label = f"{name} ({ticker})" if name else ticker

                # compone campi disponibili
                parts = []
                if close: parts.append(f"C:{close}")
                if score: parts.append(f"TS:{score}")
                if volume: parts.append(f"V:{volume}")
                if p1d: parts.append(f"1D:{p1d}")
                if p5d: parts.append(f"5D:{p5d}")

                # riga finale
                if parts:
                    righe.append(f"{action} {url}  {label}  " + "  ".join(parts))
                else:
                    righe.append(f"{action} {url}  {label}")

            msg_html = f"{market} — UPTREND BUY (top {min(max_list, n_hit)})\n\n" + "\n".join(righe)

            # Telegram limite 4096
            if len(msg_html) > 4000:
                msg_html = msg_html[:4000] + "\n[truncated]"

            telegram.sendURLs(msg_html)
        elif send_list and not n_hit:
            telegram.send(f"{market}: nessun titolo in UPTREND con BUY/ADD.")


#t=messaging()
#t.sendURLsWithFile("Here is the complete chart:", "COCO.MI.png")

#t.sendSignalsAlligators('MyList', volumeThreshold=1000, telegramChannel=4)

#m=messaging(chatTarget=1)
#m.send("PRova")
