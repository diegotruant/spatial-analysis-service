import unittest
import numpy as np
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestExperimentalEndpoints(unittest.TestCase):

    def test_w_prime_balance_endpoint(self):
        # Simulate a 10-second activity with a sprint
        # CP = 250W, W' = 20000J
        # 5s at 100W (Recovery), 5s at 400W (Depletion)
        power_data = [100.0]*5 + [400.0]*5
        payload = {
            "power_data": power_data,
            "cp": 250,
            "w_prime": 20000
        }
        
        response = client.post("/experimental/w_prime_balance", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("w_prime_balance", data)
        balance = data["w_prime_balance"]
        
        self.assertEqual(len(balance), 10)
        
        # Check logic:
        # First 5s: Recovery (should stay near/at W')
        self.assertEqual(balance[0], 20000)
        self.assertEqual(balance[4], 20000)
        
        # Next 5s: Depletion (400W > 250W, so 150J/s depletion)
        # Balance[5] = 20000 - 150 = 19850
        self.assertEqual(balance[5], 19850)
        # Balance[9] = 20000 - 150*5 = 19250
        self.assertEqual(balance[9], 19250)

    def test_w_prime_validation_error(self):
        # Test physiological validation (CP > 600 should error)
        payload = {
            "power_data": [100.0, 100.0],
            "cp": 900, # Too high (> 600)
            "w_prime": 20000
        }
        response = client.post("/experimental/w_prime_balance", json=payload)
        self.assertEqual(response.status_code, 422) # Validation Error

    def test_banister_endpoint(self):
        daily_tss = [100.0, 0.0, 100.0, 0.0, 50.0]
        payload = {
            "daily_tss": daily_tss,
            "tau_fitness": 42,
            "tau_fatigue": 7
        }
        response = client.post("/experimental/banister", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("fitness", data)
        self.assertIn("fatigue", data)
        self.assertIn("performance", data)
        self.assertEqual(len(data["fitness"]), 5)

    def test_dfa_alpha1_endpoint(self):
        # Generate fake RR data (around 800ms +/- random noise)
        # 200 intervals is enough for >1 window
        rr_intervals = [800.0 + float(np.random.randint(-50, 50)) for _ in range(200)]
        
        payload = {
            "rr_intervals": rr_intervals,
            "window_seconds": 60
        }
        response = client.post("/experimental/dfa_alpha1", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("alpha1_series", data)
        series = data["alpha1_series"]
        
        # We expect at least one window if we passed sufficient data
        if len(series) > 0:
            self.assertIn("alpha1", series[0])

if __name__ == '__main__':
    unittest.main()
