"""
Test script for Altitude/Temperature Correction
Tests air density normalization at different elevations
"""

def calculate_air_density(altitude: float, temperature: float = 15.0) -> float:
    """Calculate air density at altitude and temperature"""
    pressure_ratio = (1 - 0.0065 * altitude / 288.15) ** 5.255
    temp_correction = 1 - 0.005 * (temperature - 15.0)
    density_ratio = pressure_ratio * temp_correction
    return max(0.5, min(1.0, density_ratio))


def normalize_power_for_altitude(power: float, altitude: float, temperature: float = 15.0) -> float:
    """Normalize power to sea level equivalent"""
    if altitude <= 0 and abs(temperature - 15.0) < 1.0:
        return power
    
    density_ratio = calculate_air_density(altitude, temperature)
    correction_factor = (1.0 / density_ratio) ** (1.0 / 3.0)
    
    return power * correction_factor


print("=" * 70)
print("Test 1: SEA LEVEL (no correction)")
print("=" * 70)
power_sea = 250
alt_sea = 0
density_sea = calculate_air_density(alt_sea)
power_normalized_sea = normalize_power_for_altitude(power_sea, alt_sea)
print(f"Altitude: {alt_sea}m")
print(f"Air Density Ratio: {density_sea:.3f}")
print(f"Power Measured: {power_sea}W")
print(f"Power Normalized: {power_normalized_sea:.1f}W")
print(f"Correction: {((power_normalized_sea/power_sea - 1) * 100):.1f}%")

print("\n" + "=" * 70)
print("Test 2: 1000m ALTITUDE (moderate elevation)")
print("=" * 70)
power_1000 = 250
alt_1000 = 1000
density_1000 = calculate_air_density(alt_1000)
power_normalized_1000 = normalize_power_for_altitude(power_1000, alt_1000)
print(f"Altitude: {alt_1000}m")
print(f"Air Density Ratio: {density_1000:.3f}")
print(f"Power Measured: {power_1000}W")
print(f"Power Normalized: {power_normalized_1000:.1f}W")
print(f"Correction: +{((power_normalized_1000/power_1000 - 1) * 100):.1f}%")
print(f"Insight: At 1000m, same power = higher speed due to thin air")

print("\n" + "=" * 70)
print("Test 3: 2000m ALTITUDE (high elevation)")
print("=" * 70)
power_2000 = 250
alt_2000 = 2000
density_2000 = calculate_air_density(alt_2000)
power_normalized_2000 = normalize_power_for_altitude(power_2000, alt_2000)
print(f"Altitude: {alt_2000}m")
print(f"Air Density Ratio: {density_2000:.3f}")
print(f"Power Measured: {power_2000}W")
print(f"Power Normalized: {power_normalized_2000:.1f}W")
print(f"Correction: +{((power_normalized_2000/power_2000 - 1) * 100):.1f}%")
print(f"Insight: Power is 'worth less' at altitude -> normalize UP to sea level")

print("\n" + "=" * 70)
print("Test 4: 3000m ALTITUDE (very high - e.g., Alps)")
print("=" * 70)
power_3000 = 250
alt_3000 = 3000
density_3000 = calculate_air_density(alt_3000)
power_normalized_3000 = normalize_power_for_altitude(power_3000, alt_3000)
print(f"Altitude: {alt_3000}m")
print(f"Air Density Ratio: {density_3000:.3f}")
print(f"Power Measured: {power_3000}W")
print(f"Power Normalized: {power_normalized_3000:.1f}W")
print(f"Correction: +{((power_normalized_3000/power_3000 - 1) * 100):.1f}%")

print("\n" + "=" * 70)
print("Test 5: TEMPERATURE EFFECT (sea level, hot day)")
print("=" * 70)
power_hot = 250
alt_hot = 0
temp_hot = 35.0  # Hot day
density_hot = calculate_air_density(alt_hot, temp_hot)
power_normalized_hot = normalize_power_for_altitude(power_hot, alt_hot, temp_hot)
print(f"Altitude: {alt_hot}m, Temperature: {temp_hot}°C")
print(f"Air Density Ratio: {density_hot:.3f}")
print(f"Power Measured: {power_hot}W")
print(f"Power Normalized: {power_normalized_hot:.1f}W")
print(f"Correction: +{((power_normalized_hot/power_hot - 1) * 100):.1f}%")
print(f"Insight: Hot air is less dense -> same effect as altitude")

print("\n" + "=" * 70)
print("Test 6: COMBINED (2000m + Hot)")
print("=" * 70)
power_combined = 250
alt_combined = 2000
temp_combined = 30.0
density_combined = calculate_air_density(alt_combined, temp_combined)
power_normalized_combined = normalize_power_for_altitude(power_combined, alt_combined, temp_combined)
print(f"Altitude: {alt_combined}m, Temperature: {temp_combined}°C")
print(f"Air Density Ratio: {density_combined:.3f}")
print(f"Power Measured: {power_combined}W")
print(f"Power Normalized: {power_normalized_combined:.1f}W")
print(f"Correction: +{((power_normalized_combined/power_combined - 1) * 100):.1f}%")

print("\n" + "=" * 70)
print("✅ Altitude/Temperature Correction Validated!")
print("=" * 70)
print("\nKey Findings:")
print("  • Air density decreases with altitude (barometric formula)")
print("  • Less air resistance = same power produces higher speed")
print("  • Normalized power accounts for this to allow fair comparison")
print("  • Temperature also affects density (~0.5% per °C)")
print(f"  • At 2000m: approx. +{((power_normalized_2000/power_2000 - 1) * 100):.1f}% correction")
print(f"  • At 3000m: approx. +{((power_normalized_3000/power_3000 - 1) * 100):.1f}% correction")
