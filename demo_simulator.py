"""Demonstrate implemented equipment behavior using fictional process values.

This is a standalone terminal demonstration, not an automated production
cycle or an integration with SCADA, OPC UA, databases, or security tooling.
"""

from aero_simulator.equipment import (
    CASTING_PHASES,
    HEAT_TREATMENT_PHASES,
    Equipment,
)


def show_equipment(equipment):
    """Print an equipment identifier, operating state, and process phase."""
    print(
        f"  {equipment.equipment_id} | "
        f"{equipment.operating_state} | {equipment.cycle_phase}"
    )


def demonstrate_casting():
    """Show casting phase transitions and safe handling of a sensor fault."""
    print("\n=== INVESTMENT CASTING ===")
    casting = Equipment(
        equipment_id="EQ-CAST-001",
        name="Investment Casting Equipment",
        cycle_phase="MOLD READY",
    )
    print("Initial state:")
    show_equipment(casting)

    # An idle machine must not advance its manufacturing process.
    try:
        casting.advance_phase(CASTING_PHASES)
    except ValueError as error:
        print(f"  Idle phase change rejected: {error}")

    casting.operating_state = "RUNNING"
    for _ in range(2):
        casting.advance_phase(CASTING_PHASES)
        print("Phase advanced:")
        show_equipment(casting)

    casting.activate_fault("SENSOR_FAILURE")
    print(f"  Active fault: {casting.fault_code}")
    print(f"  Fault history records: {len(casting.fault_history)}")
    print(
        "  Recorded at (UTC): "
        f"{casting.fault_history[-1]['timestamp'].isoformat()}"
    )

    try:
        casting.advance_phase(CASTING_PHASES)
    except ValueError as error:
        print(f"  Phase change blocked by fault: {error}")
    show_equipment(casting)


def demonstrate_heat_treatment():
    """Show heating, holding, and cooling with illustrative parameters."""
    print("\n=== HEAT TREATMENT ===")
    furnace = Equipment(
        equipment_id="EQ-HT-001",
        name="Heat-Treatment Furnace",
        cycle_phase="NOT STARTED",
    )
    print("Initial state:")
    show_equipment(furnace)

    furnace.operating_state = "RUNNING"
    furnace.actual_temperature_c = 25.0
    furnace.target_temperature_c = 125.0
    furnace.heating_rate_c_per_min = 50.0
    furnace.required_hold_seconds = 90.0
    furnace.cooling_rate_c_per_min = 25.0

    furnace.advance_phase(HEAT_TREATMENT_PHASES)
    print("Heating toward 125.0 C at 50.0 C/min:")
    for elapsed_seconds in (60, 60):
        furnace.apply_heating(elapsed_seconds)
        print(
            f"  After {elapsed_seconds} s: "
            f"{furnace.actual_temperature_c:.1f} C"
        )

    furnace.advance_phase(HEAT_TREATMENT_PHASES)
    furnace.apply_holding(45)
    print(
        "Holding at target: "
        f"{furnace.elapsed_hold_seconds:.0f} s elapsed, "
        f"{furnace.remaining_hold_seconds():.0f} s remaining"
    )
    furnace.apply_holding(45)
    print(
        "Holding complete: "
        f"{furnace.elapsed_hold_seconds:.0f} s elapsed, "
        f"{furnace.remaining_hold_seconds():.0f} s remaining"
    )

    furnace.advance_phase(HEAT_TREATMENT_PHASES)
    furnace.target_temperature_c = 75.0
    furnace.apply_cooling(120)
    print(f"Cooling toward 75.0 C: {furnace.actual_temperature_c:.1f} C")

    furnace.advance_phase(HEAT_TREATMENT_PHASES)
    print("Final simulated phase:")
    show_equipment(furnace)


def main():
    """Run a reproducible demonstration of existing simulator methods."""
    print("AEROSPACE MANUFACTURING SIMULATOR | TERMINAL DEMO")
    print("Fictional illustrative values; not an industrial process recipe.")
    demonstrate_casting()
    demonstrate_heat_treatment()
    print("\nDemo finished. No external systems were connected.")


if __name__ == "__main__":
    main()
