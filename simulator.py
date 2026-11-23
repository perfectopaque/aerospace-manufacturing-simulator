"""Show initial states of the casting and heat-treatment equipment.

This entry point creates representative machines but does not run an
automated manufacturing cycle.
"""

from aero_simulator.equipment import Equipment, CASTING_PHASES, HEAT_TREATMENT_PHASES, next_phase

casting = Equipment(
    equipment_id="EQ-CAST-001",
    name="Investment Casting Equipment",
    cycle_phase="MOLD READY"
)

heat_treatment = Equipment(
    equipment_id="EQ-HT-001",
    name="Heat-Treatment Furnace",
    cycle_phase="NOT STARTED"
)


if __name__ == "__main__":
    for machine in [casting, heat_treatment]:
        print(
            f"{machine.equipment_id} | "
            f"{machine.operating_state} | "
            f"{machine.cycle_phase}"
        )
