"""Regression tests for the local OPC UA heat-treatment demonstration.

These tests verify mapping, value quality, and simulated furnace transitions.
They do not require an OPC UA server to be listening on a network port.
Authenticated/encrypted connectivity and Ignition integration are separate,
future acceptance tests.
"""

import unittest
from datetime import datetime, timezone

from asyncua import ua

from aero_simulator.equipment import Equipment
from opcua_furnace_server import (
    FURNACE_FIELDS,
    HEARTBEAT_SECONDS,
    NAMESPACE_URI,
    NODE_PREFIX,
    UPDATE_SECONDS,
    advance_furnace,
    current_values,
    data_value,
    make_node,
)


def furnace_model(phase="NOT STARTED", state="IDLE"):
    """Build an isolated furnace using the demonstration's example inputs."""
    return Equipment(
        equipment_id="EQ-HT-001",
        name="Heat-Treatment Furnace",
        cycle_phase=phase,
        operating_state=state,
        actual_temperature_c=25.0,
        target_temperature_c=125.0,
        heating_rate_c_per_min=50.0,
        cooling_rate_c_per_min=50.0,
        required_hold_seconds=90.0,
    )


class FurnaceMappingTests(unittest.TestCase):
    """Verify approved node names and values come from Equipment fields."""

    def test_namespace_nodeids_and_timing(self):
        self.assertEqual(
            NAMESPACE_URI,
            "urn:perfectopaque:aerospace-manufacturing-simulator:opcua",
        )
        self.assertEqual(NODE_PREFIX, "Equipment/EQ-HT-001/")
        self.assertEqual(UPDATE_SECONDS, 1.0)
        self.assertEqual(HEARTBEAT_SECONDS, 5.0)

    def test_furnace_values_match_equipment_model(self):
        model = furnace_model()
        values = current_values(model, heartbeat=7)
        for node_name, (attribute, _variant_type) in FURNACE_FIELDS.items():
            expected = getattr(model, attribute)
            if node_name == "FaultCode" and expected is None:
                expected = ""
            with self.subTest(node=node_name):
                self.assertEqual(values[node_name], expected)
        self.assertEqual(values["HeartbeatCounter"], 7)
        self.assertNotIn("HeatBatchID", values)

    def test_unconfigured_readings_remain_missing(self):
        model = Equipment(
            equipment_id="EQ-HT-001",
            name="Heat-Treatment Furnace",
            cycle_phase="NOT STARTED",
        )
        values = current_values(model, heartbeat=0)
        self.assertIsNone(values["ActualTemperature"])
        self.assertIsNone(values["TargetTemperature"])
        self.assertEqual(values["FaultCode"], "")
        self.assertFalse(values["FaultActive"])

    def test_active_fault_preserves_real_code(self):
        model = furnace_model()
        model.activate_fault("SENSOR_FAILURE")
        values = current_values(model, heartbeat=0)
        self.assertTrue(values["FaultActive"])
        self.assertEqual(values["FaultCode"], "SENSOR_FAILURE")
        self.assertEqual(values["AlarmState"], "NORMAL")


class FurnaceDataQualityTests(unittest.TestCase):
    """Verify GOOD and unavailable data retain accurate status and time."""

    def setUp(self):
        self.timestamp = datetime.now(timezone.utc)

    def test_valid_temperature_has_good_quality(self):
        result = data_value(25.0, ua.VariantType.Double, self.timestamp)
        self.assertEqual(result.StatusCode.value, ua.StatusCodes.Good)
        self.assertEqual(result.Value.Value, 25.0)
        self.assertEqual(result.Value.VariantType, ua.VariantType.Double)
        self.assertEqual(result.SourceTimestamp, self.timestamp)

    def test_missing_temperature_is_bad_not_zero(self):
        result = data_value(None, ua.VariantType.Double, self.timestamp)
        self.assertEqual(result.StatusCode.value, ua.StatusCodes.BadNoData)
        self.assertIsNone(result.Value.Value)
        self.assertEqual(result.Value.VariantType, ua.VariantType.Null)
        self.assertEqual(result.SourceTimestamp, self.timestamp)


class FurnaceCycleTests(unittest.TestCase):
    """Exercise transitions without changing the production Equipment model."""

    def test_demo_auto_starts_on_first_tick(self):
        model = furnace_model()
        advance_furnace(model, 1.0)
        self.assertEqual(model.operating_state, "RUNNING")
        self.assertEqual(model.cycle_phase, "HEATING")
        self.assertEqual(model.actual_temperature_c, 25.0)

    def test_heating_reaches_target_and_enters_holding(self):
        model = furnace_model(phase="HEATING", state="RUNNING")
        advance_furnace(model, 120.0)
        self.assertEqual(model.actual_temperature_c, 125.0)
        self.assertEqual(model.cycle_phase, "HOLDING")

    def test_holding_finishes_and_sets_cooling_target(self):
        model = furnace_model(phase="HOLDING", state="RUNNING")
        model.actual_temperature_c = 125.0
        advance_furnace(model, 90.0)
        self.assertEqual(model.elapsed_hold_seconds, 90.0)
        self.assertEqual(model.target_temperature_c, 75.0)
        self.assertEqual(model.cycle_phase, "COOLING")

    def test_cooling_finishes_at_target_without_undershoot(self):
        model = furnace_model(phase="COOLING", state="RUNNING")
        model.actual_temperature_c = 125.0
        model.target_temperature_c = 75.0
        advance_furnace(model, 120.0)
        self.assertEqual(model.actual_temperature_c, 75.0)
        self.assertEqual(model.cycle_phase, "COMPLETE")

    def test_active_fault_blocks_furnace_heating(self):
        model = furnace_model(phase="HEATING", state="RUNNING")
        model.activate_fault("SENSOR_FAILURE")
        with self.assertRaisesRegex(ValueError, "active fault"):
            advance_furnace(model, 1.0)
        self.assertEqual(model.cycle_phase, "HEATING")
        self.assertEqual(model.actual_temperature_c, 25.0)


class FurnaceNodeCreationTests(unittest.IsolatedAsyncioTestCase):
    """Check OPC UA node creation without starting a network server."""

    async def test_missing_node_is_read_only_and_marked_bad(self):
        class FakeNode:
            def __init__(self):
                self.is_read_only = False
                self.data_values = []

            async def set_read_only(self):
                self.is_read_only = True

            async def write_value(self, value):
                self.data_values.append(value)

        class FakeParent:
            def __init__(self):
                self.node_id = None
                self.node_name = None
                self.initial = None
                self.node = FakeNode()

            async def add_variable(self, node_id, node_name, initial):
                self.node_id = node_id
                self.node_name = node_name
                self.initial = initial
                return self.node

        parent = FakeParent()
        timestamp = datetime.now(timezone.utc)
        node = await make_node(
            parent, 2, "ActualTemperature", ua.VariantType.Double,
            None, timestamp,
        )
        self.assertTrue(node.is_read_only)
        self.assertEqual(parent.node_id.Identifier, NODE_PREFIX + "ActualTemperature")
        self.assertEqual(parent.node_name, "ActualTemperature")
        self.assertEqual(parent.initial.Value, 0.0)
        self.assertEqual(len(node.data_values), 1)
        published = node.data_values[0]
        self.assertEqual(published.StatusCode.value, ua.StatusCodes.BadNoData)
        self.assertIsNone(published.Value.Value)


if __name__ == "__main__":
    unittest.main()
