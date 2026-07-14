
import pandas as pd
import numpy as np

import pandas as pd


def build_conditions(df, conditions_spec):
    """
    Costruisce condizioni di confronto sia con valori che tra colonne

    Args:
        df: DataFrame contenente i dati
        conditions_spec: lista di condizioni come restituite da create_conditions_from_json

    Returns:
        lista di condizioni (lambda functions) pronte per l'uso
    """
    conditions = []

    for cond in conditions_spec:
        if cond['type'] == 'value_comparison':
            # Condizione normale (colonna vs valore)
            col = cond['col']
            op = cond['op']
            val = cond['val']

            if op == '>':
                conditions.append(lambda df, c=col, v=val: df[c] > v)
            elif op == '<':
                conditions.append(lambda df, c=col, v=val: df[c] < v)
            elif op == '>=':
                conditions.append(lambda df, c=col, v=val: df[c] >= v)
            elif op == '<=':
                conditions.append(lambda df, c=col, v=val: df[c] <= v)
            elif op == '==':
                conditions.append(lambda df, c=col, v=val: df[c] == v)
            elif op == '!=':
                conditions.append(lambda df, c=col, v=val: df[c] != v)

        elif cond['type'] == 'column_comparison':
            # Nuova condizione (colonna vs colonna)
            col1 = cond['col']
            op = cond['op']
            col2 = cond['col2']

            if op == '>':
                conditions.append(lambda df, c1=col1, c2=col2: df[c1] > df[c2])
            elif op == '<':
                conditions.append(lambda df, c1=col1, c2=col2: df[c1] < df[c2])
            elif op == '>=':
                conditions.append(lambda df, c1=col1, c2=col2: df[c1] >= df[c2])
            elif op == '<=':
                conditions.append(lambda df, c1=col1, c2=col2: df[c1] <= df[c2])
            elif op == '==':
                conditions.append(lambda df, c1=col1, c2=col2: df[c1] == df[c2])
            elif op == '!=':
                conditions.append(lambda df, c1=col1, c2=col2: df[c1] != df[c2])

    return conditions


def parse_condition_string(condition_str):
    """Convert condition string to dictionary"""
    operators = ['==', '!=', '>=', '<=', '>', '<']

    # Find operator
    op = next((op for op in operators if op in condition_str), None)
    if not op:
        raise ValueError(f"Invalid operator in condition: {condition_str}")

    parts = [p.strip() for p in condition_str.split(op)]
    if len(parts) != 2:
        raise ValueError(f"Invalid condition format: {condition_str}")

    col, val = parts

    if val.startswith('$'):
        return {'col': col, 'op': op, 'col2': val[1:]}
    else:
        try:
            val = float(val) if '.' in val else int(val)
        except ValueError:
            pass
        return {'col': col, 'op': op, 'val': val}


def create_conditions(*condition_strings):
    """Create conditions from multiple strings"""
    return [parse_condition_string(s) for s in condition_strings]


def parse_condition_json(condition_json):
    """Parse condition from JSON/dict"""
    if not isinstance(condition_json, dict):
        raise ValueError("Condition must be a dictionary")

    required = ['col', 'op']
    if not all(key in condition_json for key in required):
        raise ValueError(f"Condition must contain {required}")

    condition = condition_json.copy()
    valid_ops = ['==', '!=', '>=', '<=', '>', '<']

    if condition['op'] not in valid_ops:
        raise ValueError(f"Invalid operator: {condition['op']}. Must be one of: {valid_ops}")

    if 'val' in condition and 'col2' in condition:
        raise ValueError("Cannot specify both 'val' and 'col2'")
    elif 'val' not in condition and 'col2' not in condition:
        raise ValueError("Must specify either 'val' or 'col2'")

    if 'val' in condition and isinstance(condition['val'], str):
        try:
            condition['val'] = float(condition['val']) if '.' in condition['val'] else int(condition['val'])
        except ValueError:
            pass

    return condition


def create_conditions_from_jsonv0(json_input):
    """Create conditions from JSON input"""
    if isinstance(json_input, list):
        return [parse_condition_json(cond) for cond in json_input]
    elif isinstance(json_input, dict):
        return [parse_condition_json(json_input)]
    raise ValueError("Input must be a JSON object or array")


def create_conditions_from_json(json_conditions):
    """
    Processa le condizioni JSON aggiungendo supporto per confronti tra colonne

    Ora supporta sia:
    - {"col": "RSI", "op": ">", "val": 50} (confronto con valore)
    - {"col": "EMA_30", "op": ">", "col2": "Close"} (confronto tra colonne)
    """
    conditions = []
    for cond in json_conditions:
        # Se c'è 'col2' invece di 'val', è un confronto tra colonne
        if 'col2' in cond:
            conditions.append({
                'col': cond['col'],
                'op': cond['op'],
                'col2': cond['col2'],
                'type': 'column_comparison'
            })
        else:
            conditions.append({
                'col': cond['col'],
                'op': cond['op'],
                'val': cond['val'],
                'type': 'value_comparison'
            })
    return conditions