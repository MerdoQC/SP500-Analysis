import unittest
from datetime import date
from backend.diagnostics import portfolio_risk, stale_signal, technical_indicators, weighted_score

class DiagnosticsTests(unittest.TestCase):
    def test_stale_model(self):
        self.assertEqual(stale_signal("2026-09-07T07:24:56Z", date(2026, 11, 17))["status"], "STALE")

    def test_missing_scores(self):
        self.assertEqual(weighted_score({"ml": 80, "analyst": None}, {"ml": .6, "analyst": .4})["status"], "INCOMPLETE")

    def test_score(self):
        self.assertEqual(weighted_score({"ml": 80, "analyst": 50}, {"ml": .6, "analyst": .4})["score"], 68)

    def test_concentration(self):
        result = portfolio_risk({"A": .7, "B": .3}, {"A": "Technology", "B": "Technology"})
        self.assertEqual(result["sector_breaches"]["Technology"], 1)

    def test_technical(self):
        self.assertEqual(technical_indicators([float(i) for i in range(1, 202)])["status"], "OK")
        self.assertEqual(technical_indicators([100.] * 20)["status"], "INSUFFICIENT_DATA")

if __name__ == "__main__":
    unittest.main()
