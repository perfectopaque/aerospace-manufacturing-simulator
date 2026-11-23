"""Regression tests for equipment state, faults, and thermal process logic."""

import unittest
from simulator import Equipment


class TestEquipment(unittest.TestCase):
    """Exercise equipment independence, transitions, and process safeguards."""

    def test_initial_state(self):
        machine = Equipment(
            equipment_id="EQ-CAST-001",
            name="Investment Casting Equipment",
            cycle_phase="MOLD READY"
        )

        self.assertEqual(machine.operating_state, "IDLE")
        self.assertEqual(machine.alarm_state, "NORMAL")
        self.assertFalse(machine.fault_active)
        self.assertIsNone(machine.actual_temperature_c)

    def test_equipment_independence(self):
        casting = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        furnace = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        casting.operating_state = "RUNNING"

        self.assertEqual(furnace.operating_state, "IDLE")

    def test_casting_phase_transition(self):
        from simulator import next_phase, CASTING_PHASES

        result = next_phase("MOLD READY", CASTING_PHASES)

        self.assertEqual(result, "MELT READY")

    def test_heat_treatment_phase_transition(self):
        from simulator import next_phase, HEAT_TREATMENT_PHASES

        result = next_phase("HEATING", HEAT_TREATMENT_PHASES)

        self.assertEqual(result, "HOLDING")

    def test_equipment_advances_phase(self):
        from simulator import CASTING_PHASES

        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        machine.operating_state = "RUNNING"

        machine.advance_phase(CASTING_PHASES)

        self.assertEqual(machine.cycle_phase, "MELT READY")

    def test_idle_equipment_cannot_advance(self):
        from simulator import CASTING_PHASES

        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        with self.assertRaises(ValueError):
            machine.advance_phase(CASTING_PHASES)

        self.assertEqual(machine.cycle_phase, "MOLD READY")

    def test_fault_prevents_phase_advancement(self):
        from simulator import CASTING_PHASES

        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        machine.operating_state = "RUNNING"
        machine.fault_active = True

        with self.assertRaises(ValueError):
            machine.advance_phase(CASTING_PHASES)

        self.assertEqual(machine.cycle_phase, "MOLD READY")

    def test_fault_code_initialization(self):
        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        self.assertFalse(machine.fault_active)
        self.assertIsNone(machine.fault_code)

    def test_fault_activation(self):
        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        machine.activate_fault("SENSOR_FAILURE")

        self.assertTrue(machine.fault_active)
        self.assertEqual(machine.fault_code, "SENSOR_FAILURE")

    def test_empty_fault_code_rejected(self):
        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        with self.assertRaises(ValueError):
            machine.activate_fault("")

        self.assertFalse(machine.fault_active)
        self.assertIsNone(machine.fault_code)

    def test_whitespace_fault_code_rejected(self):
        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        with self.assertRaises(ValueError):
            machine.activate_fault("   ")

        self.assertFalse(machine.fault_active)
        self.assertIsNone(machine.fault_code)

    def test_activated_fault_blocks_manufacturing(self):
        from simulator import CASTING_PHASES

        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        machine.operating_state = "RUNNING"
        machine.activate_fault("SENSOR_FAILURE")

        with self.assertRaises(ValueError):
            machine.advance_phase(CASTING_PHASES)

        self.assertEqual(machine.cycle_phase, "MOLD READY")
        self.assertTrue(machine.fault_active)

    def test_fault_history_independence(self):
        casting = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        furnace = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        casting.fault_history.append({
            "fault_code": "SENSOR_FAILURE"
        })

        self.assertEqual(len(casting.fault_history), 1)
        self.assertEqual(len(furnace.fault_history), 0)

    def test_automatic_fault_history(self):
        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        machine.activate_fault("SENSOR_FAILURE")

        self.assertEqual(len(machine.fault_history), 1)

        record = machine.fault_history[0]

        self.assertEqual(record["equipment_id"], "EQ-CAST-001")
        self.assertEqual(record["fault_code"], "SENSOR_FAILURE")
        self.assertIsNotNone(record["timestamp"])

    def test_fault_timestamp_uses_utc(self):
        from datetime import timezone

        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        machine.activate_fault("SENSOR_FAILURE")

        record = machine.fault_history[0]

        self.assertEqual(
            record["timestamp"].tzinfo,
            timezone.utc
        )

    def test_invalid_fault_not_recorded(self):
        machine = Equipment(
            "EQ-CAST-001",
            "Investment Casting Equipment",
            "MOLD READY"
        )

        with self.assertRaises(ValueError):
            machine.activate_fault("")

        self.assertEqual(len(machine.fault_history), 0)

    def test_temperature_initialization(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        self.assertIsNone(machine.actual_temperature_c)
        self.assertIsNone(machine.target_temperature_c)

    def test_target_temperature_assignment(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        machine.target_temperature_c = 100.0

        self.assertEqual(machine.target_temperature_c, 100.0)

    def test_actual_temperature_assignment(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        machine.actual_temperature_c = 25.0

        self.assertEqual(machine.actual_temperature_c, 25.0)

    def test_temperature_deviation_calculation(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        machine.actual_temperature_c = 95.0
        machine.target_temperature_c = 100.0

        deviation = machine.temperature_deviation_c()

        self.assertEqual(deviation, -5.0)

    def test_missing_temperature_deviation(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        machine.target_temperature_c = 100.0

        deviation = machine.temperature_deviation_c()

        self.assertIsNone(deviation)

    def test_heating_rate_initialization(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        self.assertIsNone(machine.heating_rate_c_per_min)

    def test_heating_rate_assignment(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        machine.heating_rate_c_per_min = 10.0

        self.assertEqual(
            machine.heating_rate_c_per_min,
            10.0
        )

    def test_heating_increase_calculation(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        machine.heating_rate_c_per_min = 10.0

        increase = machine.calculate_heating_increase(30)

        self.assertEqual(increase, 5.0)

    def test_heating_without_rate(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        increase = machine.calculate_heating_increase(30)

        self.assertIsNone(increase)

    def test_apply_heating(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 35.0)

    def test_heating_stops_at_target(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 95.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 100.0)

    def test_idle_furnace_cannot_heat(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 25.0)

    def test_furnace_cannot_heat_during_holding(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 100.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 100.0)

    def test_fault_prevents_furnace_heating(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        machine.activate_fault("SENSOR_FAILURE")

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 25.0)
        self.assertTrue(machine.fault_active)

    def test_negative_heating_time_rejected(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        with self.assertRaises(ValueError):
            machine.apply_heating(-60)

        self.assertEqual(machine.actual_temperature_c, 25.0)

    def test_heating_without_actual_temperature(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertIsNone(machine.actual_temperature_c)

    def test_heating_without_target_temperature(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.heating_rate_c_per_min = 10.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 25.0)
        self.assertIsNone(machine.target_temperature_c)

    def test_heating_without_heating_rate(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 25.0)
        self.assertIsNone(machine.heating_rate_c_per_min)

    def test_zero_heating_rate_rejected(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 0.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 25.0)

    def test_negative_heating_rate_rejected(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 25.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = -10.0

        with self.assertRaises(ValueError):
            machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 25.0)

    def test_heating_preserves_overtemperature(self):
        """Leave already-high temperatures unchanged during heating."""
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 105.0
        machine.target_temperature_c = 100.0
        machine.heating_rate_c_per_min = 10.0

        machine.apply_heating(60)

        self.assertEqual(machine.actual_temperature_c, 105.0)
        self.assertEqual(machine.temperature_deviation_c(), 5.0)

    def test_holding_duration_initialization(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        self.assertIsNone(machine.required_hold_seconds)

    def test_elapsed_hold_time_initialization(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "NOT STARTED"
        )

        self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_remaining_hold_time_calculation(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        machine.required_hold_seconds = 120.0
        machine.elapsed_hold_seconds = 45.0

        remaining = machine.remaining_hold_seconds()

        self.assertEqual(remaining, 75.0)

    def test_remaining_hold_time_without_requirement(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        remaining = machine.remaining_hold_seconds()

        self.assertIsNone(remaining)

    def test_remaining_hold_time_never_negative(self):
        """Clamp negative remaining hold time to zero."""
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        machine.required_hold_seconds = 120.0
        machine.elapsed_hold_seconds = 150.0

        remaining = machine.remaining_hold_seconds()

        self.assertEqual(remaining, 0.0)

    def test_holding_time_accumulates(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 100.0
        machine.target_temperature_c = 100.0
        machine.required_hold_seconds = 120.0

        machine.apply_holding(30)

        self.assertEqual(machine.elapsed_hold_seconds, 30.0)
        self.assertEqual(machine.remaining_hold_seconds(), 90.0)

    def test_idle_furnace_cannot_accumulate_holding_time(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        machine.actual_temperature_c = 100.0
        machine.target_temperature_c = 100.0
        machine.required_hold_seconds = 120.0

        with self.assertRaises(ValueError):
            machine.apply_holding(30)

        self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_heating_phase_cannot_accumulate_holding_time(self):
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HEATING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 100.0
        machine.target_temperature_c = 100.0
        machine.required_hold_seconds = 120.0

        with self.assertRaises(ValueError):
            machine.apply_holding(30)

        self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def make_holding_machine(self):
        """Create a running, on-target furnace ready for holding tests."""
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "HOLDING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 100.0
        machine.target_temperature_c = 100.0
        machine.required_hold_seconds = 120.0

        return machine

    def test_active_fault_blocks_holding(self):
        machine = self.make_holding_machine()
        machine.activate_fault("SENSOR_FAILURE")

        with self.assertRaises(ValueError):
            machine.apply_holding(30)

        self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_invalid_holding_time_rejected(self):
        for seconds in (0, -10):
            with self.subTest(seconds=seconds):
                machine = self.make_holding_machine()

                with self.assertRaises(ValueError):
                    machine.apply_holding(seconds)

                self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_invalid_holding_duration_rejected(self):
        for duration in (None, 0.0, -10.0):
            with self.subTest(duration=duration):
                machine = self.make_holding_machine()
                machine.required_hold_seconds = duration

                with self.assertRaises(ValueError):
                    machine.apply_holding(30)

                self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_missing_holding_temperature_rejected(self):
        """Reject missing thermal readings before holding time accrues."""
        for attribute in (
            "actual_temperature_c",
            "target_temperature_c"
        ):
            with self.subTest(attribute=attribute):
                machine = self.make_holding_machine()
                setattr(machine, attribute, None)

                with self.assertRaises(ValueError):
                    machine.apply_holding(30)

                self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_off_target_holding_rejected(self):
        machine = self.make_holding_machine()
        machine.actual_temperature_c = 95.0

        with self.assertRaises(ValueError):
            machine.apply_holding(30)

        self.assertEqual(machine.elapsed_hold_seconds, 0.0)

    def test_holding_time_capped_at_requirement(self):
        machine = self.make_holding_machine()

        machine.apply_holding(150)

        self.assertEqual(machine.elapsed_hold_seconds, 120.0)
        self.assertEqual(machine.remaining_hold_seconds(), 0.0)

    def test_multiple_holding_intervals(self):
        machine = self.make_holding_machine()

        machine.apply_holding(30)
        machine.apply_holding(45)

        self.assertEqual(machine.elapsed_hold_seconds, 75.0)
        self.assertEqual(machine.remaining_hold_seconds(), 45.0)

    def make_cooling_machine(self):
        """Create a running furnace with a valid cooling configuration."""
        machine = Equipment(
            "EQ-HT-001",
            "Heat-Treatment Furnace",
            "COOLING"
        )

        machine.operating_state = "RUNNING"
        machine.actual_temperature_c = 100.0
        machine.target_temperature_c = 80.0
        machine.cooling_rate_c_per_min = 10.0

        return machine

    def test_cooling_reduces_temperature(self):
        machine = self.make_cooling_machine()

        machine.apply_cooling(60)

        self.assertEqual(machine.actual_temperature_c, 90.0)

    def test_cooling_stops_at_target(self):
        machine = self.make_cooling_machine()

        machine.apply_cooling(180)

        self.assertEqual(machine.actual_temperature_c, 80.0)

    def test_cooling_preserves_below_target(self):
        """Do not warm an already cool furnace to the cooling setpoint."""
        machine = self.make_cooling_machine()
        machine.actual_temperature_c = 75.0

        machine.apply_cooling(60)

        self.assertEqual(machine.actual_temperature_c, 75.0)

    def test_idle_equipment_cannot_cool(self):
        machine = self.make_cooling_machine()
        machine.operating_state = "IDLE"

        with self.assertRaises(ValueError):
            machine.apply_cooling(60)

        self.assertEqual(machine.actual_temperature_c, 100.0)

    def test_wrong_phase_cannot_cool(self):
        machine = self.make_cooling_machine()
        machine.cycle_phase = "HOLDING"

        with self.assertRaises(ValueError):
            machine.apply_cooling(60)

        self.assertEqual(machine.actual_temperature_c, 100.0)

    def test_active_fault_blocks_cooling(self):
        machine = self.make_cooling_machine()
        machine.activate_fault("EQUIPMENT_MALFUNCTION")

        with self.assertRaises(ValueError):
            machine.apply_cooling(60)

        self.assertEqual(machine.actual_temperature_c, 100.0)

    def test_invalid_cooling_time_rejected(self):
        for seconds in (0, -60):
            with self.subTest(seconds=seconds):
                machine = self.make_cooling_machine()

                with self.assertRaises(ValueError):
                    machine.apply_cooling(seconds)

                self.assertEqual(machine.actual_temperature_c, 100.0)

    def test_invalid_cooling_configuration(self):
        """Reject missing or nonpositive cooling inputs."""
        configurations = (
            ("actual_temperature_c", None),
            ("target_temperature_c", None),
            ("cooling_rate_c_per_min", None),
            ("cooling_rate_c_per_min", 0.0),
            ("cooling_rate_c_per_min", -10.0),
        )

        for attribute, value in configurations:
            with self.subTest(attribute=attribute, value=value):
                machine = self.make_cooling_machine()
                setattr(machine, attribute, value)

                with self.assertRaises(ValueError):
                    machine.apply_cooling(60)

                self.assertEqual(
                    getattr(machine, attribute),
                    value
                )

    def test_multiple_cooling_intervals(self):
        machine = self.make_cooling_machine()

        machine.apply_cooling(30)
        machine.apply_cooling(30)

        self.assertEqual(machine.actual_temperature_c, 90.0)

if __name__ == "__main__":
    unittest.main()
