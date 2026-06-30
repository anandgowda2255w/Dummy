# ==========================================================
# TEST FILE FOR ANALYTICS ENGINE
# ==========================================================

from analytics_engine import (
    calculate_oee,
    get_downtime_analytics,
    get_rejection_analytics,
    compare_machine_analytics
)

# ==========================================================
# TEST 1 : VALID OEE CALCULATION
# ==========================================================

print("\n" + "=" * 60)
print("TEST 1 : VALID OEE CALCULATION")
print("=" * 60)

result = calculate_oee(
    "M001",
    "2026-04-01",
    "2026-05-30"
)

print(result)

# ==========================================================
# TEST 2 : INVALID MACHINE ID
# ==========================================================

print("\n" + "=" * 60)
print("TEST 2 : INVALID MACHINE ID")
print("=" * 60)

result = calculate_oee(
    "M999",
    "2026-04-01",
    "2026-05-30"
)

print(result)

# ==========================================================
# TEST 3 : SINGLE DAY OEE CALCULATION
# ==========================================================

print("\n" + "=" * 60)
print("TEST 3 : SINGLE DAY OEE")
print("=" * 60)

result = calculate_oee(
    "M001",
    "2026-04-01",
    "2026-04-01"
)

print(result)

# ==========================================================
# TEST 4 : INVALID DATE RANGE
# ==========================================================

print("\n" + "=" * 60)
print("TEST 4 : INVALID DATE RANGE")
print("=" * 60)

result = calculate_oee(
    "M001",
    "2026-05-30",
    "2026-04-01"
)

print(result)

# ==========================================================
# TEST 5 : DOWNTIME ANALYTICS
# ==========================================================

print("\n" + "=" * 60)
print("TEST 5 : DOWNTIME ANALYTICS")
print("=" * 60)

result = get_downtime_analytics(
    "2026-04-01",
    "2026-05-30"
)

print(result)

# ==========================================================
# TEST 6 : MACHINE-WISE DOWNTIME DISPLAY
# ==========================================================

print("\n" + "=" * 60)
print("TEST 6 : MACHINE-WISE DOWNTIME")
print("=" * 60)

for machine in result["data"]:
    print(machine)

# ==========================================================
# TEST 7 : EMPTY DATE RANGE
# ==========================================================

print("\n" + "=" * 60)
print("TEST 7 : EMPTY DATE RANGE")
print("=" * 60)

result = get_downtime_analytics(
    "2030-01-01",
    "2030-01-31"
)

print(result)
# ==========================================================
# TEST 8 : REJECTION ANALYTICS
# ==========================================================

print("\n" + "=" * 60)
print("TEST 8 : REJECTION ANALYTICS")
print("=" * 60)

result = get_rejection_analytics(
    "2026-04-01",
    "2026-05-30"
)

print(result)

# ==========================================================
# TEST 9 : MACHINE COMPARISON
# ==========================================================

print("\n" + "=" * 60)
print("TEST 9 : MACHINE COMPARISON")
print("=" * 60)

result = compare_machine_analytics(
    "M001",
    "M002",
    "2026-04-01",
    "2026-05-30"
)

print(result)

# ==========================================================
# TEST 10 : INVALID MACHINE COMPARISON
# ==========================================================

print("\n" + "=" * 60)
print("TEST 10 : INVALID MACHINE COMPARISON")
print("=" * 60)

result = compare_machine_analytics(
    "M001",
    "M999",
    "2026-04-01",
    "2026-05-30"
)

print(result)

# ==========================================================
# TEST 11 : EMPTY REJECTION ANALYTICS
# ==========================================================

print("\n" + "=" * 60)
print("TEST 11 : EMPTY REJECTION ANALYTICS")
print("=" * 60)

result = get_rejection_analytics(
    "2030-01-01",
    "2030-01-31"
)

print(result)

# ==========================================================
# ALL TESTS COMPLETED
# ==========================================================

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)