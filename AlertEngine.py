# -*- coding: utf-8 -*-

import json
import time
import re
from pathlib import Path
from datetime import datetime, timezone
import html
import yaml
import pandas as pd

from messaging import messaging


class AlertEngine:
    """
    Uso semplice:

        from alert_engine import AlertEngine

        engine = AlertEngine(
            analyses_dir=r"C:\\...\\analyses",
            markets=["MIB30", "Preferite", "ETF", "ETC"],
            telegram_channel=5
        )
        engine.run()   # esegue tutti i mercati con lo stesso canale
    """

    # ============================
    # INIT
    # ============================

    def __init__(self, analyses_dir: str, markets: list[str], telegram_channel: int):
        self.analyses_dir = Path(analyses_dir)
        self.markets = [str(m).strip() for m in (markets or []) if str(m).strip()]
        self.telegram_channel = int(telegram_channel)

        if not self.analyses_dir.exists():
            raise FileNotFoundError(f"analyses_dir non trovato: {self.analyses_dir}")
        if not self.markets:
            raise ValueError("La lista 'markets' Ã¨ vuota.")
        if not isinstance(self.telegram_channel, int):
            raise ValueError("telegram_channel deve essere un int.")

    def _tickers_in_scope(self, rule: dict, df: pd.DataFrame) -> list[str]:
        scope = (rule.get("scope") or {})

        # 1) caso classico: lista ticker esplicita
        tickers = scope.get("tickers") or []
        if tickers:
            return [str(t).strip() for t in tickers if str(t).strip()]

        # 2) caso market-wide: filtri "where"
        where = scope.get("where") or []
        if not where:
            return []

        d = df.copy()
        for c in where:
            field = c.get("field")
            op = c.get("op")
            value = c.get("value")

            if field not in d.columns:
                continue

            # numeric vs string compare
            if isinstance(value, (int, float)):
                s = pd.to_numeric(d[field], errors="coerce")
            else:
                s = d[field].astype(str)

            if op == "==":
                d = d[s == value]
            elif op == ">":
                d = d[s > value]
            elif op == "<":
                d = d[s < value]
            elif op == ">=":
                d = d[s >= value]
            elif op == "<=":
                d = d[s <= value]

        return d["Ticker"].astype(str).str.strip().tolist()

    def get_targets_for_rule(self, rule: dict, rows_by_ticker: dict) -> list[str]:
        scope = (rule.get("scope", {}) or {})
        tickers = scope.get("tickers", []) or []

        # normalizza lista tickers se presente
        if tickers:
            return [str(t).strip() for t in tickers if str(t).strip()]

        # NEW: filtro dinamico
        where = scope.get("where", []) or []
        if where:
            out = []
            for t, row in rows_by_ticker.items():
                ok = True
                for c in where:
                    field = c["field"]
                    op = c["op"]
                    val = c["value"]
                    if not self._eval_op(row.get(field), op, val):
                        ok = False
                        break
                if ok:
                    out.append(str(t).strip())
            return out

        return []

    def _describe_rule(self, rule: dict) -> str:
        """
        Crea una descrizione leggibile del tipo di alert
        es: 'Close > 10' oppure '0 < MACD_vs_Signal < 4'
        """
        conds = rule.get("when", {}).get("all", [])
        parts = []

        for c in conds:
            field = c.get("field", "?")
            op = c.get("op", "?")
            val = c.get("value", "?")
            parts.append(f"{field} {op} {val}")

        if not parts:
            return "Custom rule"

        return " AND ".join(parts)

    # ============================
    # UTILS (interni)
    # ============================
    @staticmethod
    def _now_ts() -> int:
        return int(time.time())

    @staticmethod
    def _today_key_local() -> str:
        # Giorno "locale" della macchina: "YYYY-MM-DD"
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _safe_float(x):
        try:
            if x is None or pd.isna(x):
                return None

            # âœ… gestisce numeri come "1,0" o " 1,57E+08 "
            if isinstance(x, str):
                x = x.strip().replace("\u202f", "").replace(" ", "").replace(",", ".")

            return float(x)
        except Exception:
            return None

    @staticmethod
    def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.astype(str).str.strip()
        if "Ticker" in df.columns:
            df["Ticker"] = df["Ticker"].astype(str).str.strip()
        if {"Stoch_K", "Stoch_D"}.issubset(df.columns):
            df["Stoch_KvsD"] = pd.to_numeric(df["Stoch_K"], errors="coerce") - pd.to_numeric(df["Stoch_D"], errors="coerce")
        if {"PLUS_DI", "MINUS_DI"}.issubset(df.columns):
            df["DI_diff"] = pd.to_numeric(df["PLUS_DI"], errors="coerce") - pd.to_numeric(df["MINUS_DI"], errors="coerce")
        if "EMA_30" in df.columns:
            df["EMA30"] = pd.to_numeric(df["EMA_30"], errors="coerce")
        return df

    # ============================
    # PATHS
    # ============================
    def rules_path(self, market: str) -> Path:
        return self.analyses_dir / f"alert_rules_{market}.yaml"

    def excel_path(self, market: str) -> Path:
        return self.analyses_dir / f"{market}_TA_Analyses.xlsx"

    def state_path(self, market: str) -> Path:
        return self.analyses_dir / f"alert_state_{market}.json"

    # ============================
    # IO
    # ============================
    def load_rules(self, market: str) -> dict:
        rp = self.rules_path(market)
        if not rp.exists():
            base = {
                "version": 1,
                "defaults": {"cooldown_minutes": 240, "send_on_first_match_only": True},
                "rules": [],
            }
            with open(rp, "w", encoding="utf-8") as f:
                yaml.safe_dump(base, f, sort_keys=False, allow_unicode=True)

        with open(rp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        data.setdefault("defaults", {})
        data.setdefault("rules", [])
        return data

    def load_df(self, market: str) -> pd.DataFrame:
        fp = self.excel_path(market)
        if not fp.exists():
            raise FileNotFoundError(fp)
        df = pd.read_excel(fp)
        return self._normalize_df(df)

    def load_state(self, market: str) -> dict:
        sp = self.state_path(market)
        if not sp.exists():
            return {}
        with open(sp, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_state(self, market: str, state: dict):
        sp = self.state_path(market)
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    # ============================
    # LOGIC
    # ============================
    def _eval_op(self, left, op, right) -> bool:
        l = self._safe_float(left)
        r = self._safe_float(right)

        if l is not None and r is not None:
            if op == ">": return l > r
            if op == "<": return l < r
            if op == ">=": return l >= r
            if op == "<=": return l <= r
            if op == "==": return l == r
            if op == "!=": return l != r
            return False

        ls = str(left).strip()
        rs = str(right).strip()
        if op == "==": return ls == rs
        if op == "!=": return ls != rs
        return False

    def rule_matches_row(self, rule: dict, row: dict) -> bool:
        scope = (rule.get("scope") or {})
        tickers = scope.get("tickers") or []

        # 1) Se la regola Ã¨ per tickers espliciti, applico il filtro
        if tickers:
            tickers_norm = {str(t).strip() for t in tickers if str(t).strip()}
            if str(row.get("Ticker", "")).strip() not in tickers_norm:
                return False

        # 2) Se la regola Ã¨ market-wide con scope.where, applico anche quello come filtro scope
        where = scope.get("where") or []
        if where:
            for c in where:
                field = c.get("field")
                op = c.get("op")
                val = c.get("value")
                if not self._eval_op(row.get(field), op, val):
                    return False

        # 3) Poi applico le condizioni "when"
        conds = (rule.get("when") or {}).get("all") or []
        for c in conds:
            field = c.get("field")
            op = c.get("op")
            val = c.get("value")
            if not self._eval_op(row.get(field), op, val):
                return False

        return True

    def render_message(self, rule: dict, row: dict, market: str) -> str:
        msg = rule.get("message", {}) or {}

        title_tpl = str(msg.get("title", "ðŸ”” Alert"))
        body_tpl = str(msg.get("body", ""))

        ticker_raw = str(row.get("Ticker", "")).strip()
        market_raw = str(market).strip()
        name_raw = str(row.get("Name", "")).strip()
        rule_id_raw = str(rule.get("id", "")).strip() or "-"
        cond_raw = self._describe_rule(rule)

        volume_raw = row.get("Volume", "")
        pctv_1d_raw = row.get("PCTV_1D", "")
        pctv_5d_raw = row.get("PCTV_5D", "")
        pctv_10d_raw = row.get("PCTV_10D", "")

        # -----------------------
        # formatter numeri
        # -----------------------

        def fmt_int(val):
            num = self._safe_float(val)
            if num is None:
                return str(val).strip()
            return f"{num:,.0f}".replace(",", ".")

        def fmt_pct(val):
            num = self._safe_float(val)
            if num is None:
                return str(val).strip()
            return f"{num:+.2f}%".replace(".", ",")

        volume_fmt = fmt_int(volume_raw)
        pctv_1d_fmt = fmt_pct(pctv_1d_raw)
        pctv_5d_fmt = fmt_pct(pctv_5d_raw)
        pctv_10d_fmt = fmt_pct(pctv_10d_raw)

        # -----------------------
        # placeholder replacement
        # -----------------------

        title_raw = title_tpl
        body_raw = body_tpl

        for k, v in row.items():
            title_raw = title_raw.replace(f"{{{{{k}}}}}", str(v))
            body_raw = body_raw.replace(f"{{{{{k}}}}}", str(v))

        title_raw = title_raw.replace("{{market}}", market_raw)
        body_raw = body_raw.replace("{{market}}", market_raw)
        # Normalize common mojibake fragments from legacy saved templates.
        title_raw = title_raw.replace("ðŸ””", "🔔").replace("â€¢", "•")
        body_raw = body_raw.replace("ðŸ””", "🔔").replace("â€¢", "•")
        # Keep exactly one bell in final output: strip bells from title text,
        # then add one icon in the output line.
        title_raw = title_raw.lstrip()
        while title_raw.startswith("🔔"):
            title_raw = title_raw[1:].lstrip()

        # Keep Telegram title coherent with current row value.
        # Example: "MACD_vs_Signal = 1" becomes "... = 4" when row value is 4.
        if "{{MACD_vs_Signal}}" not in title_tpl and "MACD_vs_Signal" in title_raw:
            macd_val = row.get("MACD_vs_Signal", "")
            macd_num = self._safe_float(macd_val)
            if macd_num is None:
                macd_str = str(macd_val).strip()
            else:
                macd_str = str(int(macd_num)) if float(macd_num).is_integer() else str(macd_num)
            title_raw = re.sub(
                r"(MACD_vs_Signal\s*[=!<>]+\s*)([^ ,)\]]+)",
                lambda m: f"{m.group(1)}{macd_str}",
                title_raw,
            )

        # -----------------------
        # rimuove Date dal body
        # -----------------------

        lines = body_raw.splitlines()
        lines = [l for l in lines if not l.strip().lower().startswith("date:")]
        body_raw = "\n".join(lines)

        # -----------------------
        # escape HTML
        # -----------------------

        title_safe = html.escape(title_raw)
        body_safe = html.escape(body_raw)
        ticker_safe = html.escape(ticker_raw)
        market_safe = html.escape(market_raw)
        name_safe = html.escape(name_raw)
        rule_id_safe = html.escape(rule_id_raw)
        cond_safe = html.escape(cond_raw)

        volume_safe = html.escape(volume_fmt)
        pctv_1d_safe = html.escape(pctv_1d_fmt)
        pctv_5d_safe = html.escape(pctv_5d_fmt)
        pctv_10d_safe = html.escape(pctv_10d_fmt)

        # -----------------------
        # URL ticker
        # -----------------------

        url = f"http://theoiziruam.ddns.net:8503/?market={market_raw}&ticker={ticker_raw}"
        url_safe = html.escape(url, quote=True)
        link = f'<a href="{url_safe}">{ticker_safe}</a>'

        # -----------------------
        # data e ora messaggio
        # -----------------------

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_safe = html.escape(now_str)
        icon_market = "\U0001F9ED"
        icon_bell = "\U0001F514"
        icon_link = "\U0001F517"
        icon_name = "\U0001F3F7"
        icon_vol = "\U0001F4CA"
        icon_pct = "\U0001F4C8"
        icon_time = "\U0001F552"
        icon_rule = "\U0001F9FE"
        icon_cond = "\U0001F9EA"

        # -----------------------
        # output finale
        # -----------------------

        out = (
            f"{icon_market} <b>Market:</b> {market_safe}\n"
            f"{icon_bell} {title_safe}\n"
            f"{icon_rule} <b>RuleID:</b> {rule_id_safe}\n"
            f"{icon_cond} <b>Condizione:</b> {cond_safe}\n"
            f"{icon_link} {link}\n"
            f"{icon_name} <b>Name:</b> {name_safe}\n"
            f"{icon_vol} <b>Volume:</b> {volume_safe}\n"
            f"{icon_pct} <b>PCTV 1D:</b> {pctv_1d_safe}\n"
            f"{icon_pct} <b>PCTV 5D:</b> {pctv_5d_safe}\n"
            f"{icon_pct} <b>PCTV 10D:</b> {pctv_10d_safe}\n"
            f"{body_safe}\n"
            f"{icon_time} <b>Data/Ora:</b> {now_safe}"
        )

        return out

    def render_messagev0(self, rule: dict, row: dict, market: str) -> str:
        msg = rule.get("message", {}) or {}

        title_tpl = str(msg.get("title", "ðŸ”” Alert"))
        body_tpl = str(msg.get("body", ""))

        ticker_raw = str(row.get("Ticker", "")).strip()
        market_raw = str(market).strip()
        name_raw = str(row.get("Name", "")).strip()

        volume_raw = row.get("Volume", "")
        pctv_1d_raw = row.get("PCTV_1D", "")
        pctv_5d_raw = row.get("PCTV_5D", "")
        pctv_10d_raw = row.get("PCTV_10D", "")

        # ---------- formatter ----------
        def fmt_number(val, decimals=3):
            num = self._safe_float(val)
            if num is None:
                return str(val).strip()
            return f"{num:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

        def fmt_int(val):
            num = self._safe_float(val)
            if num is None:
                return str(val).strip()
            return f"{num:,.0f}".replace(",", ".")

        def fmt_pct(val):
            num = self._safe_float(val)
            if num is None:
                return str(val).strip()
            return f"{num:+.2f}%".replace(".", ",")

        volume_fmt = fmt_int(volume_raw)
        pctv_1d_fmt = fmt_pct(pctv_1d_raw)
        pctv_5d_fmt = fmt_pct(pctv_5d_raw)
        pctv_10d_fmt = fmt_pct(pctv_10d_raw)

        # Data/ora corrente in fondo messaggio
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---------- placeholder replacement ----------
        title_raw = title_tpl
        body_raw = body_tpl

        for k, v in row.items():
            title_raw = title_raw.replace(f"{{{{{k}}}}}", str(v))
            body_raw = body_raw.replace(f"{{{{{k}}}}}", str(v))

        title_raw = title_raw.replace("{{market}}", market_raw)
        body_raw = body_raw.replace("{{market}}", market_raw)
        # Normalize common mojibake fragments from legacy saved templates.
        title_raw = title_raw.replace("ðŸ””", "🔔").replace("â€¢", "•")
        body_raw = body_raw.replace("ðŸ””", "🔔").replace("â€¢", "•")
        # Keep exactly one bell in final output: strip bells from title text,
        # then add one icon in the output line.
        title_raw = title_raw.lstrip()
        while title_raw.startswith("🔔"):
            title_raw = title_raw[1:].lstrip()

        # ---------- HTML escape ----------
        title_safe = html.escape(title_raw)
        body_safe = html.escape(body_raw)
        ticker_safe = html.escape(ticker_raw)
        market_safe = html.escape(market_raw)
        name_safe = html.escape(name_raw)
        volume_safe = html.escape(volume_fmt)
        pctv_1d_safe = html.escape(pctv_1d_fmt)
        pctv_5d_safe = html.escape(pctv_5d_fmt)
        pctv_10d_safe = html.escape(pctv_10d_fmt)
        now_safe = html.escape(now_str)
        icon_market = "\U0001F9ED"
        icon_bell = "\U0001F514"
        icon_link = "\U0001F517"
        icon_name = "\U0001F3F7"
        icon_vol = "\U0001F4CA"
        icon_pct = "\U0001F4C8"
        icon_time = "\U0001F552"

        # ---------- URL ----------
        url = f"http://theoiziruam.ddns.net:8503/?market={market_raw}&ticker={ticker_raw}"
        url_safe = html.escape(url, quote=True)
        link = f'<a href="{url_safe}">{ticker_safe}</a>'

        # ---------- output ----------

        out = (
            f"{icon_market} <b>Market:</b> {market_safe}\n"
            f"{icon_bell} {title_safe}\n"
            f"{icon_link} {link}\n"
            f"{icon_name} <b>Name:</b> {name_safe}\n"
            f"{icon_vol} <b>Volume:</b> {volume_safe}\n"
            f"{icon_pct} <b>PCTV 1D:</b> {pctv_1d_safe}\n"
            f"{icon_pct} <b>PCTV 5D:</b> {pctv_5d_safe}\n"
            f"{icon_pct} <b>PCTV 10D:</b> {pctv_10d_safe}\n"
            f"{body_safe}\n"
            f"{icon_time} <b>Data/Ora:</b> {now_safe}"
        )

        return out



    # ============================
    # PUBLIC API (semplice)
    # ============================
    def run(self) -> dict:
        """
        Esegue tutti i mercati impostati in __init__ sullo stesso canale telegram.
        Ritorna un dict con lo stato per mercato: {"MIB30":"ok", "ETF":"ok", ...} oppure errori.
        """
        results = {}
        for market in self.markets:
            try:
                self.run_market(market)
                results[market] = "ok"
            except Exception as e:
                results[market] = f"error: {type(e).__name__}: {e}"
        return results

    def run_market(self, market: str):
        """
        Esegue un singolo mercato usando il canale unico definito in __init__.
        """

        print("=== MARKET:", market)
        print("rules file:", self.rules_path(market), "exists:", self.rules_path(market).exists())
        print("excel file:", self.excel_path(market), "exists:", self.excel_path(market).exists())

        rules_data = self.load_rules(market)
        defaults = rules_data.get("defaults", {})
        rules = [r for r in rules_data["rules"] if r.get("enabled", True)]
        print("rules loaded:", [r.get("id") for r in rules])

        df = self.load_df(market)
        rows = {r["Ticker"]: r for r in df.to_dict(orient="records")}

        state = self.load_state(market)
        bot = messaging(chatTarget=self.telegram_channel)

        for rule in rules:
            rid = str(rule.get("id", "")).strip()
            if not rid:
                continue

            cooldown = int(rule.get("cooldown_minutes", defaults.get("cooldown_minutes", 0)))
            max_per_day = int(rule.get("max_per_day", defaults.get("max_per_day", 3)))
            min_gap_minutes = int(rule.get("min_gap_minutes", defaults.get("min_gap_minutes", 0)))

            # âœ… prende tickers espliciti oppure dinamici via scope.where
            targets = self.get_targets_for_rule(rule, rows)
            print("RULE:", rid, "targets:", len(targets))
            if "scope" in rule:
                print("  scope:", rule.get("scope"))
            print("  when:", rule.get("when"))

            if not targets:
                continue

            for t in targets:
                t = str(t).strip()
                row = rows.get(t)
                if not row:
                    continue

                # âœ… stato per (regola + ticker) => non blocca gli altri tickers
                state_key = f"{rid}__{t}"

                st = state.get(state_key, {
                    "was_true": False,
                    "last_sent_ts": 0,
                    "sent_day": "",
                    "sent_count": 0,
                    "sent_total": 0
                })

                last_sent_ts = int(st.get("last_sent_ts", 0) or 0)
                sent_day = str(st.get("sent_day", "") or "")
                sent_count = int(st.get("sent_count", 0) or 0)
                sent_total = int(st.get("sent_total", 0) or 0)

                is_true = self.rule_matches_row(rule, row)

                # ===== daily repeat =====
                today = self._today_key_local()
                if sent_day != today:
                    sent_day = today
                    sent_count = 0

                do_send = False
                if is_true and sent_count < max_per_day:
                    cooldown_ok = True
                    if cooldown > 0 and (self._now_ts() - last_sent_ts) < cooldown * 60:
                        cooldown_ok = False

                    gap_ok = True
                    if min_gap_minutes > 0 and (self._now_ts() - last_sent_ts) < min_gap_minutes * 60:
                        gap_ok = False

                    do_send = cooldown_ok and gap_ok

                if do_send:
                    text = self.render_message(rule, row, market)
                    print("SENDING:", market, rid, t)
                    try:
                        res = bot.sendURLs(text)
                        print("SENT OK:", res)
                    except Exception as e:
                        print("SEND ERROR:", type(e).__name__, e)
                        # se fallisce, non consumare contatori
                        continue

                    last_sent_ts = self._now_ts()
                    sent_count += 1
                    sent_total += 1

                # âœ… salva stato per ticker
                state[state_key] = {
                    "was_true": bool(is_true),
                    "last_sent_ts": last_sent_ts,
                    "sent_day": sent_day,
                    "sent_count": sent_count,
                    "sent_total": sent_total,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

        self.save_state(market, state)



