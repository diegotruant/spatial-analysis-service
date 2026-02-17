"""
Test script for 3-Point CP Model
Compares 2-point and 3-point CP calculations
"""

def test_2point_cp():
    """Test 2-point linear model (manual calculation)"""
    print("=" * 70)
    print("Test 1: 2-POINT CP MODEL (Linear)")
    print("=" * 70)
    
    # Sample data
    mmp6 = 320  # 6min power
    mmp15 = 280  # 15min power
    
    t6 = 360
    t15 = 900
    
    work6 = mmp6 * t6
    work15 = mmp15 * t15
    
    cp = (work15 - work6) / (t15 - t6)
    w_prime = work6 - cp * t6
    
    print(f"Input MMP values:")
    print(f"  6min (360s): {mmp6}W")
    print(f"  15min (900s): {mmp15}W")
    print(f"\nResults:")
    print(f"  CP = {cp:.1f}W")
    print(f"  W' = {w_prime:.0f}J ({w_prime/1000:.1f}kJ)")
    print(f"  Model: 2-point linear (Monod-Scherrer)")
    
    return cp, w_prime


def test_3point_theoretical():
    """Test theoretical 3-point model behavior"""
    print("\n" + "=" * 70)
    print("Test 2: 3-POINT CP MODEL (Theoretical)")
    print("=" * 70)
    
    # Sample data with 3 points
    mmp_data = {
        180: 350,   # 3min
        420: 310,   # 7min
        720: 290    # 12min
    }
    
    print(f"Input MMP values:")
    for duration, power in sorted(mmp_data.items()):
        print(f"  {duration//60}min ({duration}s): {power}W")
    
    print(f"\nWith 3 points, we can fit the hyperbolic curve: P = CP + W'/t")
    print(f"This gives a more accurate CP estimate, especially for athletes with high W'")
    print(f"\nNote: Actual calculation requires scipy (not tested here)")
    
    # Simple estimate using first and last point
    durations = sorted(mmp_data.keys())
    t1, t3 = durations[0], durations[-1]
    p1, p3 = mmp_data[t1], mmp_data[t3]
    
    work1 = p1 * t1
    work3 = p3 * t3
    cp_estimate = (work3 - work1) / (t3 - t1)
    w_prime_estimate = work1 - cp_estimate * t1
    
    print(f"\nSimple 2-point estimate (using 3min and 12min):")
    print(f"  CP ≈ {cp_estimate:.1f}W")
    print(f"  W' ≈ {w_prime_estimate:.0f}J ({w_prime_estimate/1000:.1f}kJ)")


def test_comparison():
    """Compare different scenarios"""
    print("\n" + "=" * 70)
    print("Test 3: WHY 3-POINT IS BETTER")
    print("=" * 70)
    
    print("\nScenario: Athlete with HIGH W' (explosive)")
    print("-" * 70)
    print("Power curve:")
    print("  3min: 400W")
    print("  6min: 330W  (high - good anaerobic capacity)")
    print("  15min: 280W")
    
    # 2-point using 6' and 15'
    w6_1 = 330 * 360
    w15_1 = 280 * 900
    cp_2pt_1 = (w15_1 - w6_1) / (900 - 360)
    wprime_2pt_1 = w6_1 - cp_2pt_1 * 360
    
    print(f"\n2-point model (6min, 15min):")
    print(f"  CP = {cp_2pt_1:.1f}W")
    print(f"  W' = {wprime_2pt_1:.0f}J ({wprime_2pt_1/1000:.1f}kJ)")
    
    # 2-point using 3' and 15'
    w3_1 = 400 * 180
    cp_2pt_alt = (w15_1 - w3_1) / (900 - 180)
    wprime_2pt_alt = w3_1 - cp_2pt_alt * 180
    
    print(f"\n2-point model (3min, 15min) - for comparison:")
    print(f"  CP = {cp_2pt_alt:.1f}W")
    print(f"  W' = {wprime_2pt_alt:.0f}J ({wprime_2pt_alt/1000:.1f}kJ)")
    
    print(f"\n⚠️ Notice: Different CP values depending on points chosen!")
    print(f"   Difference: {abs(cp_2pt_1 - cp_2pt_alt):.1f}W")
    print(f"\n3-point model would fit ALL points simultaneously,")
    print(f"giving a more robust CP estimate less sensitive to outliers.")


print("\n" + "=" * 70)
print("CP MODEL COMPARISON TEST SUITE")
print("=" * 70)

test_2point_cp()
test_3point_theoretical()
test_comparison()

print("\n" + "=" * 70)
print("✅ All tests completed!")
print("=" * 70)
print("\nKey Takeaways:")
print("  • 2-point model: Simple but sensitive to point selection")
print("  • 3-point model: More robust, fits hyperbolic curve P = CP + W'/t")
print("  • Benefit highest for athletes with high anaerobic capacity")
print("  • 3-point requires scipy for non-linear regression")
print("  • Backward compatible: defaults to 2-point if scipy unavailable")
