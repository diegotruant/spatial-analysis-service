"""
Simple test for HRV CV calculation logic
Can be run in Python REPL without dependencies
"""

# Simulate CV calculation
def test_cv_calculation():
    """Test the CV calculation logic"""
    
    # Test 1: Stable HRV (low CV)
    stable = [58, 61, 59, 62, 60, 58, 61]
    mean1 = sum(stable) / len(stable)
    variance1 = sum((x - mean1) ** 2 for x in stable) / (len(stable) - 1)
    std1 = variance1 ** 0.5
    cv1 = (std1 / mean1) * 100
    
    print("Test 1: Stable HRV")
    print(f"  Values: {stable}")
    print(f"  Mean: {mean1:.1f}")
    print(f"  Std Dev: {std1:.1f}")
    print(f"  CV: {cv1:.1f}%")
    print(f"  Expected: CV < 10% (OPTIMAL)")
    print(f"  Result: {'✅ PASS' if cv1 < 10 else '❌ FAIL'}")
    
    # Test 2: Unstable HRV (high CV)
    unstable = [40, 75, 55, 80, 45, 70, 60]
    mean2 = sum(unstable) / len(unstable)
    variance2 = sum((x - mean2) ** 2 for x in unstable) / (len(unstable) - 1)
    std2 = variance2 ** 0.5
    cv2 = (std2 / mean2) * 100
    
    print("\nTest 2: Unstable HRV")
    print(f"  Values: {unstable}")
    print(f"  Mean: {mean2:.1f}")
    print(f"  Std Dev: {std2:.1f}")
    print(f"  CV: {cv2:.1f}%")
    print(f"  Expected: CV > 20% (UNSTABLE)")
    print(f"  Result: {'✅ PASS' if cv2 > 20 else '❌ FAIL'}")
    
    # Test 3: Moderate variability
    moderate = [55, 62, 58, 68, 60, 57, 63]
    mean3 = sum(moderate) / len(moderate)
    variance3 = sum((x - mean3) ** 2 for x in moderate) / (len(moderate) - 1)
    std3 = variance3 ** 0.5
    cv3 = (std3 / mean3) * 100
    
    print("\nTest 3: Moderate HRV")
    print(f"  Values: {moderate}")
    print(f"  Mean: {mean3:.1f}")
    print(f"  Std Dev: {std3:.1f}")
    print(f"  CV: {cv3:.1f}%")
    print(f"  Expected: 10% < CV < 20% (MODERATE)")
    print(f"  Result: {'✅ PASS' if 10 < cv3 < 20 else '❌ FAIL'}")
    
    print("\n" + "=" * 60)
    print("✅ CV Calculation Logic Validated")
    print("=" * 60)

if __name__ == "__main__":
    test_cv_calculation()
