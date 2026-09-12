import json
import unittest

from app.ai.alert_contract import validate_alert_analysis


def report(conditions):
    return '```json\n' + json.dumps({'conditions': conditions, 'critical_levels': []}) + '\n```'


def clause(op='>', value=12.02):
    return dict(field='Close', indicator='Close', op=op, value=value, trigger=f'{op} {value}')


class AlertContractTests(unittest.TestCase):
    def test_numeric_conditions_and_empty_scenario(self):
        validate_alert_analysis(report([clause()]))
        validate_alert_analysis(report([]))

    def test_narrative_pullback_is_rejected_before_display(self):
        with self.assertRaises(ValueError):
            validate_alert_analysis(report([dict(indicator='Pullback', trigger='Rimbalzo confermato su 11.60')]))

    def test_display_must_match_saved_threshold(self):
        condition = clause()
        condition['trigger'] = '> 11.74'
        with self.assertRaises(ValueError):
            validate_alert_analysis(report([condition]))

    def test_conflicting_scenarios_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_alert_analysis(report([clause('>', 12.02), clause('<', 11.74)]))

    def test_missing_json_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_alert_analysis('Analisi senza condizioni strutturate')


if __name__ == '__main__':
    unittest.main()
