import json
import math
import re


ALERT_FIELDS = (
    "Close", "RSI", "ADX", "MACD_Hist", "MACD_vs_Signal", "DI_diff",
    "Stoch_K", "Stoch_D", "Williams_R", "Volume",
    "Vol_Perc_vs_MA5", "Vol_Perc_vs_MA10", "Vol_Perc_vs_MA20",
)

ALERT_CONTRACT = (
    "REGOLE VINCOLANTI PER LE CONDIZIONI ATTIVABILI, prevalgono sugli esempi precedenti: "
    "proponi UN SOLO scenario operativo coerente. Tutte le conditions sono collegate in AND "
    "e devono potersi verificare nella stessa osservazione. Non mescolare breakout e pullback alternativi. "
    "Ogni condition deve avere field, op, value, indicator, trigger, description. "
    f"field deve essere uno di: {', '.join(ALERT_FIELDS)}. "
    "op deve essere >, >=, <, <=, == o !=; value deve essere un numero finito. "
    "indicator deve coincidere con field, trigger deve essere esattamente op seguito dal valore numerico. "
    "description spiega SOLO quel confronto: non aggiungere conferme, rimbalzi, sequenze temporali, "
    "crescita o confronti con altri campi non codificati. Per volumi sopra MA10 usa "
    "Vol_Perc_vs_MA10 > 0; per MACD sopra Signal usa MACD_vs_Signal > 0. "
    "Scegli soglie fondate sui dati disponibili. Non usare numeri inventati per completare lo schema. "
    "Includi sempre un unico blocco JSON con conditions e critical_levels. "
    "Se nessuno scenario misurabile e giustificato e disponibile, conditions deve essere [] "
    "e il testo deve spiegare il motivo. Gli scenari alternativi possono essere discussi nel testo, "
    "ma non devono figurare tra le condizioni da attivare."
)


def validate_alert_analysis(text: str) -> None:
    blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text or "", re.IGNORECASE)
    payloads = []
    for block in blocks:
        try:
            item = json.loads(block)
        except ValueError:
            continue
        if isinstance(item, dict) and "conditions" in item:
            payloads.append(item)
    if len(payloads) != 1 or not isinstance(payloads[0]["conditions"], list):
        raise ValueError("Serve un unico blocco JSON con conditions come lista.")
    for condition in payloads[0]["conditions"]:
        if not isinstance(condition, dict):
            raise ValueError("Ogni condizione deve essere un oggetto.")
        field, op, value = (condition.get(key) for key in ("field", "op", "value"))
        if field not in ALERT_FIELDS or op not in (">", ">=", "<", "<=", "==", "!="):
            raise ValueError("Campo o operatore non supportato nelle condizioni.")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("La soglia deve essere numerica e finita.")
        if condition.get("indicator") != field:
            raise ValueError("Indicatore visualizzato diverso dal campo monitorato.")
        trigger = re.fullmatch(r"(>=|<=|!=|==|>|<)\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", str(condition.get("trigger", "")).strip())
        if not trigger or trigger[1] != op or float(trigger[2]) != value:
            raise ValueError("Trigger visualizzato diverso dalla soglia monitorata.")
    conditions = payloads[0]["conditions"]
    for field in ALERT_FIELDS:
        lower, upper = -math.inf, math.inf
        lower_strict = upper_strict = False
        for condition in conditions:
            if condition["field"] != field:
                continue
            op, value = condition["op"], condition["value"]
            if op in (">", ">=", "=="):
                if value > lower:
                    lower, lower_strict = value, op == ">"
                elif value == lower:
                    lower_strict |= op == ">"
            if op in ("<", "<=", "=="):
                if value < upper:
                    upper, upper_strict = value, op == "<"
                elif value == upper:
                    upper_strict |= op == "<"
        if lower > upper or (lower == upper and (lower_strict or upper_strict)):
            raise ValueError(f"Soglie incompatibili per {field}.")
