"""Serve simulated heat-treatment furnace data over local OPC UA.

This standalone development application creates an ``EQ-HT-001`` equipment
model, advances a fictional heating/holding/cooling cycle, and publishes the
model's values through a read-only OPC UA address space. It does not modify
``equipment.py`` or the existing command-line demonstration.

The demonstration cycle starts automatically after the server starts, using
illustrative temperatures and rates rather than an industrial process recipe.

Security boundary:
    The endpoint uses OPC UA NoSecurity and listens only on 127.0.0.1. It is
    for same-VM testing, not Ignition integration, remote access, or production
    equipment. Authentication, certificates, and encryption remain future work.

Run from the repository root using the Python environment with ``asyncua``::

    .venv314/bin/python opcua_furnace_server.py

Stop the server with Ctrl+C. All timestamps are intended to be UTC.
"""

import asyncio
import time
from datetime import datetime, timezone

from asyncua import Server, ua

from aero_simulator.equipment import Equipment, HEAT_TREATMENT_PHASES


# Keep the namespace URI and string NodeIds stable across server restarts.
# The numeric namespace index is allocated at runtime and must not be assumed.
NAMESPACE_URI = "urn:perfectopaque:aerospace-manufacturing-simulator:opcua"
ENDPOINT = "opc.tcp://127.0.0.1:4840/aerospace/"
NODE_PREFIX = "Equipment/EQ-HT-001/"

# Nominal loop interval for processing; actual elapsed time drives the model.
UPDATE_SECONDS = 1.0
# Communication heartbeat runs independently from the equipment's phase/state.
HEARTBEAT_SECONDS = 5.0

# Map public OPC UA names to existing Equipment attributes and OPC UA types.
# These names follow the approved communication architecture; HeatBatchID is
# intentionally absent until a genuine batch-data source is implemented.
FURNACE_FIELDS = {
    "EquipmentId": ("equipment_id", ua.VariantType.String),
    "Name": ("name", ua.VariantType.String),
    "OperatingState": ("operating_state", ua.VariantType.String),
    "CyclePhase": ("cycle_phase", ua.VariantType.String),
    "AlarmState": ("alarm_state", ua.VariantType.String),
    "FaultActive": ("fault_active", ua.VariantType.Boolean),
    "FaultCode": ("fault_code", ua.VariantType.String),
    "ActualTemperature": ("actual_temperature_c", ua.VariantType.Double),
    "TargetTemperature": ("target_temperature_c", ua.VariantType.Double),
    "HeatingRate": ("heating_rate_c_per_min", ua.VariantType.Double),
    "CoolingRate": ("cooling_rate_c_per_min", ua.VariantType.Double),
    "RequiredHoldSeconds": ("required_hold_seconds", ua.VariantType.Double),
    "ElapsedHoldSeconds": ("elapsed_hold_seconds", ua.VariantType.Double),
    "DataTimestamp": ("data_timestamp", ua.VariantType.DateTime),
}


def current_values(model, heartbeat):
    """Collect the equipment's current OPC UA values.

    Args:
        model: Authoritative ``Equipment`` instance for the furnace.
        heartbeat: Communication-layer counter, separate from the model.

    Returns:
        Dictionary keyed by public OPC UA node name. An absent fault code is
        represented by an empty string only when there is no active fault.

    Notes:
        This function reads existing equipment properties. It never calculates
        temperatures or advances the manufacturing process.
    """
    result = {node: getattr(model, field) for node, (field, _) in FURNACE_FIELDS.items()}
    if not model.fault_active and result["FaultCode"] is None:
        result["FaultCode"] = ""
    result["HeartbeatCounter"] = heartbeat
    return result


def data_value(value, variant_type, timestamp):
    """Wrap a value with its OPC UA type, quality, and source timestamp.

    Args:
        value: Equipment reading or ``None`` when unavailable.
        variant_type: OPC UA ``VariantType`` for a present reading.
        timestamp: UTC source timestamp associated with the reading.

    Returns:
        An ``ua.DataValue`` with GOOD quality for an available value, or a
        Null variant and ``BadNoData`` for an unavailable value.

    Notes:
        Marking unavailable values BAD avoids interpreting missing
        temperatures as a real zero-degree measurement. Client-side handling
        of this status still requires a dedicated integration test.
    """
    if value is None:
        return ua.DataValue(
            Value=ua.Variant(None, ua.VariantType.Null),
            StatusCode=ua.StatusCode(ua.StatusCodes.BadNoData),
            SourceTimestamp=timestamp,
        )
    return ua.DataValue(
        Value=ua.Variant(value, variant_type),
        StatusCode=ua.StatusCode(ua.StatusCodes.Good),
        SourceTimestamp=timestamp,
    )


async def make_node(parent, namespace, name, variant_type, initial, timestamp):
    """Create one furnace variable with a stable NodeId and read-only access.

    Args:
        parent: Furnace object node in the OPC UA address space.
        namespace: Numeric namespace index registered for ``NAMESPACE_URI``.
        name: Stable variable name, appended to ``NODE_PREFIX``.
        variant_type: OPC UA type declared for a normal, available reading.
        initial: Starting value, possibly ``None``.
        timestamp: Initial UTC source timestamp.

    Returns:
        The newly created ``asyncua`` variable node.

    Raises:
        ValueError: If a missing value has no supported initialization type.

    Notes:
        The server first creates the variable with a typed placeholder if
        necessary, then immediately writes BAD/Null status for missing data.
        The server has not yet started accepting clients at this stage.
        ``set_read_only()`` restricts client writes; the server may still
        publish updates to the variable.
    """
    # An OPC UA variable needs an initial type even when its value is absent.
    # The placeholder is replaced with BadNoData before the server starts.
    if initial is None:
        if variant_type == ua.VariantType.Double:
            initial = 0.0
        elif variant_type == ua.VariantType.String:
            initial = ""
        else:
            raise ValueError(f"No initialization rule for {name}")
        missing = True
    else:
        missing = False

    node = await parent.add_variable(
        ua.NodeId(NODE_PREFIX + name, namespace),
        name,
        ua.Variant(initial, variant_type),
    )
    await node.set_read_only()
    if missing:
        await node.write_value(data_value(None, variant_type, timestamp))
    else:
        await node.write_value(data_value(initial, variant_type, timestamp))
    return node


def advance_furnace(model, elapsed_seconds):
    """Advance the dedicated demo furnace through its manufacturing phases.

    Args:
        model: Furnace ``Equipment`` instance to update in place.
        elapsed_seconds: Actual elapsed wall-clock interval, measured using a
            monotonic timer by the caller.

    Notes:
        This is a scripted, fictional demonstration, not equipment control.
        The scenario intentionally starts itself on the first update tick.
        Thermal calculations and operation validation remain inside the
        existing ``Equipment`` methods.
    """
    if model.cycle_phase == "NOT STARTED":
        model.operating_state = "RUNNING"
        model.data_timestamp = datetime.now(timezone.utc)
        model.advance_phase(HEAT_TREATMENT_PHASES)

    elif model.cycle_phase == "HEATING":
        model.apply_heating(elapsed_seconds)
        if model.actual_temperature_c >= model.target_temperature_c:
            model.advance_phase(HEAT_TREATMENT_PHASES)

    elif model.cycle_phase == "HOLDING":
        model.apply_holding(elapsed_seconds)
        if model.remaining_hold_seconds() == 0:
            # Switch to the fictional cooling setpoint before entering COOLING.
            # The model uses the same target property for both thermal phases.
            model.target_temperature_c = 75.0
            model.data_timestamp = datetime.now(timezone.utc)
            model.advance_phase(HEAT_TREATMENT_PHASES)

    elif model.cycle_phase == "COOLING":
        model.apply_cooling(elapsed_seconds)
        if model.actual_temperature_c <= model.target_temperature_c:
            model.advance_phase(HEAT_TREATMENT_PHASES)


async def main():
    """Create the local server and publish the automatic demonstration cycle.

    The server and simulation share one asyncio event loop. Every nominal
    one-second tick advances the authoritative equipment model using the
    elapsed monotonic-clock interval. Only changed values are republished,
    so an unchanged reading does not get an artificially refreshed source
    timestamp. The heartbeat updates approximately every five seconds.

    The ``async with server`` context manages server startup and cleanup.
    Ctrl+C exits through the module's ``KeyboardInterrupt`` handler.
    """
    # These settings are illustrative demonstration inputs, not a qualified
    # heat-treatment recipe or externally supplied process commands.
    model = Equipment(
        equipment_id="EQ-HT-001",
        name="Heat-Treatment Furnace",
        cycle_phase="NOT STARTED",
        actual_temperature_c=25.0,
        target_temperature_c=125.0,
        heating_rate_c_per_min=50.0,
        cooling_rate_c_per_min=50.0,
        required_hold_seconds=90.0,
    )

    server = Server()
    await server.init()
    # NoSecurity is intentional only for the localhost proof of concept.
    # Do not bind to a LAN interface without a separately reviewed security plan.
    server.set_endpoint(ENDPOINT)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    namespace = await server.register_namespace(NAMESPACE_URI)

    # Build the approved address-space hierarchy: Equipment / EQ-HT-001.
    equipment = await server.nodes.objects.add_object(
        ua.NodeId("Equipment", namespace), "Equipment"
    )
    furnace = await equipment.add_object(
        ua.NodeId("Equipment/EQ-HT-001", namespace), model.equipment_id
    )

    # Snapshot the values used to initialize nodes and compare future updates.
    # HeatBatchID stays absent because no production batch data exists yet.
    heartbeat = 0
    published = current_values(model, heartbeat)
    nodes = {}
    for name, (_, variant_type) in FURNACE_FIELDS.items():
        nodes[name] = await make_node(
            furnace, namespace, name, variant_type,
            published[name], model.data_timestamp,
        )
    nodes["HeartbeatCounter"] = await make_node(
        furnace, namespace, "HeartbeatCounter", ua.VariantType.UInt32,
        heartbeat, datetime.now(timezone.utc),
    )

    async with server:
        print("Local OPC UA furnace server running:", ENDPOINT)
        print("Read-only monitoring; development-only NoSecurity endpoint")
        print("Press Ctrl+C to stop")
        # Monotonic time avoids jumps from system clock adjustments when
        # calculating elapsed process time and heartbeat intervals.
        last_step = time.monotonic()
        last_heartbeat = last_step
        while True:
            await asyncio.sleep(UPDATE_SECONDS)
            now = time.monotonic()
            elapsed = now - last_step
            last_step = now

            advance_furnace(model, elapsed)
            # Heartbeat is independent of process state and wraps as UInt32.
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                heartbeat = (heartbeat + 1) % (2**32)
                last_heartbeat = now

            latest = current_values(model, heartbeat)
            # Publish only changed readings. A heartbeat write does not make
            # unchanged equipment measurements falsely appear newly sampled.
            for name, value in latest.items():
                if value == published[name]:
                    continue
                kind = (
                    ua.VariantType.UInt32 if name == "HeartbeatCounter"
                    else FURNACE_FIELDS[name][1]
                )
                # Equipment changes use the model's source timestamp; the
                # communication heartbeat uses its own current UTC timestamp.
                timestamp = (
                    datetime.now(timezone.utc) if name == "HeartbeatCounter"
                    else model.data_timestamp
                )
                await nodes[name].write_value(data_value(value, kind, timestamp))
                published[name] = value

            print(
                f"{model.cycle_phase:12} "
                f"temperature={model.actual_temperature_c:.1f}°C "
                f"heartbeat={heartbeat}",
                flush=True,
            )


if __name__ == "__main__":
    # Keep Ctrl+C a deliberate, clean stop rather than a traceback in the demo.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("OPC UA server stopped")
