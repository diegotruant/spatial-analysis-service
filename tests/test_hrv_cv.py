"""
Test script for HRV CV enhancement
Tests the new Coefficient of Variation functionality
"""
import sys
sys.path.insert(0, r'c:\Users\Diego Truant\Desktop\00DDTraining\spatial-cosmic\spatial-analysis-service')

from hrv_engine import HRVEngine

print("=" * 60)
print("Test 1: HRV stabile (low CV)")
print("=" * 60)
# HRV con valori stabili intorno a 60ms
stable_hrv = [58, 61, 59, 62, 60, 58, 61]
baseline_stable = HRVEngine.calculate_baseline(stable_hrv)
print(f"Values: {stable_hrv}")
print(f"Mean: {baseline_stable['mean']} ms")
print(f"Std Dev: {baseline_stable['std_dev']} ms")
print(f"CV: {baseline_stable['cv']}%")
print(f"CV Status: {baseline_stable['cv_status']}")
print(f"Stability: {baseline_stable['stability']}")

traffic_stable = HRVEngine.calculate_traffic_light(60, baseline_stable['mean'])
rec_stable = HRVEngine.get_recommendation(
    traffic_stable['status'], 
    traffic_stable['deviation'],
    0,
    baseline_stable['cv_status']
)
print(f"\nRecommendation: {rec_stable}")

print("\n" + "=" * 60)
print("Test 2: HRV instabile (high CV)")
print("=" * 60)
# HRV con valori molto variabili (stesso mean ma alta variabilità)
unstable_hrv = [40, 75, 55, 80, 45, 70, 60]
baseline_unstable = HRVEngine.calculate_baseline(unstable_hrv)
print(f"Values: {unstable_hrv}")
print(f"Mean: {baseline_unstable['mean']} ms")
print(f"Std Dev: {baseline_unstable['std_dev']} ms")
print(f"CV: {baseline_unstable['cv']}%")
print(f"CV Status: {baseline_unstable['cv_status']}")
print(f"Stability: {baseline_unstable['stability']}")

traffic_unstable = HRVEngine.calculate_traffic_light(60, baseline_unstable['mean'])
rec_unstable = HRVEngine.get_recommendation(
    traffic_unstable['status'],
    traffic_unstable['deviation'],
    0,
    baseline_unstable['cv_status']
)
print(f"\nRecommendation: {rec_unstable}")

print("\n" + "=" * 60)
print("Test 3: HRV moderatamente variabile")
print("=" * 60)
moderate_hrv = [55, 62, 58, 68, 60, 57, 63]
baseline_moderate = HRVEngine.calculate_baseline(moderate_hrv)
print(f"Values: {moderate_hrv}")
print(f"Mean: {baseline_moderate['mean']} ms")
print(f"Std Dev: {baseline_moderate['std_dev']} ms")
print(f"CV: {baseline_moderate['cv']}%")
print(f"CV Status: {baseline_moderate['cv_status']}")
print(f"Stability: {baseline_moderate['stability']}")

traffic_moderate = HRVEngine.calculate_traffic_light(61, baseline_moderate['mean'])
rec_moderate = HRVEngine.get_recommendation(
    traffic_moderate['status'],
    traffic_moderate['deviation'],
    0,
    baseline_moderate['cv_status']
)
print(f"\nRecommendation: {rec_moderate}")

print("\n" + "=" * 60)
print("Test 4: HRV bassa MA instabile (worst case)")
print("=" * 60)
low_unstable = [30, 55, 35, 50, 32, 48, 38]
baseline_low_unstable = HRVEngine.calculate_baseline(low_unstable)
print(f"Values: {low_unstable}")
print(f"Mean: {baseline_low_unstable['mean']} ms")
print(f"Std Dev: {baseline_low_unstable['std_dev']} ms")
print(f"CV: {baseline_low_unstable['cv']}%")
print(f"CV Status: {baseline_low_unstable['cv_status']}")
print(f"Stability: {baseline_low_unstable['stability']}")

traffic_low = HRVEngine.calculate_traffic_light(35, baseline_low_unstable['mean'])
rec_low = HRVEngine.get_recommendation(
    traffic_low['status'],
    traffic_low['deviation'],
    0,
    baseline_low_unstable['cv_status']
)
print(f"\nRecommendation: {rec_low}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
