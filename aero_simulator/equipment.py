"""Model manufacturing equipment states, process phases, and thermal behavior.

The equipment model tracks faults and thermal process steps without external
SCADA, communications, or data-storage integrations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Phases are ordered to define the next valid step in each process cycle.
CASTING_PHASES = (
    "MOLD READY",
    "MELT READY",
    "POURING",
    "SOLIDIFYING",
    "COMPLETE",
)

HEAT_TREATMENT_PHASES = (
    "NOT STARTED",
    "HEATING",
    "HOLDING",
    "COOLING",
    "COMPLETE",
)

def next_phase(current_phase, phases):
    """Return the next phase in an ordered manufacturing cycle.

    Args:
        current_phase: Current phase name to locate within ``phases``.
        phases: Ordered sequence of permitted phase names.

    Returns:
        The phase immediately following ``current_phase``.

    Raises:
        ValueError: If the phase is unknown or the cycle is complete.
    """
    if current_phase not in phases:
        raise ValueError("Unknown manufacturing phase")

    current_index = phases.index(current_phase)

    if current_index == len(phases) - 1:
        raise ValueError("Manufacturing cycle already complete")

    return phases[current_index + 1]

@dataclass
class Equipment:
    """Represent an individual machine and its manufacturing process state.

    Attributes:
        equipment_id: Unique identifier for the simulated machine.
        name: Human-readable equipment description.
        cycle_phase: Current casting or heat-treatment process phase.
        operating_state: Equipment state, initially ``IDLE``.
        alarm_state: Recorded alarm status, initially ``NORMAL``.
        fault_active: Whether a fault currently blocks process operations.
        fault_code: Code identifying the active fault, if any.
        actual_temperature_c: Current temperature in degrees Celsius.
        target_temperature_c: Process target in degrees Celsius.
        heating_rate_c_per_min: Temperature increase rate in Celsius/minute.
        cooling_rate_c_per_min: Temperature decrease rate in Celsius/minute.
        required_hold_seconds: Configured duration of the holding phase.
        elapsed_hold_seconds: Completed holding duration in seconds.
        fault_history: Separate per-machine records of activated faults.
        data_timestamp: UTC time of initialization or last method update.

    Notes:
        Configuration attributes can be assigned directly. Direct assignment
        does not automatically update ``data_timestamp`` or ``alarm_state``.
    """
    equipment_id: str
    name: str
    cycle_phase: str
    operating_state: str = "IDLE"
    alarm_state: str = "NORMAL"
    fault_active: bool = False
    fault_code: str | None = None
    actual_temperature_c: float | None = None
    target_temperature_c: float | None = None
    heating_rate_c_per_min: float | None = None
    cooling_rate_c_per_min: float | None = None
    required_hold_seconds: float | None = None
    elapsed_hold_seconds: float = 0.0
    fault_history: list[dict] = field(default_factory=list)

    data_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def advance_phase(self, phases):
        """Move running, fault-free equipment to the next process phase.

        Args:
            phases: Ordered process phases for this machine.

        Raises:
            ValueError: If the machine is not running, a fault is active,
                the current phase is invalid, or the cycle is complete.
        """
        if self.operating_state != "RUNNING":
            raise ValueError("Equipment must be RUNNING")

        if self.fault_active:
            raise ValueError("Cannot advance with active fault")

        self.cycle_phase = next_phase(
            self.cycle_phase, phases
        )

        self.data_timestamp = datetime.now(timezone.utc)

    def activate_fault(self, fault_code):
        """Activate a fault and append a UTC-stamped history record.

        Args:
            fault_code: Nonempty identifier for the equipment fault.

        Raises:
            ValueError: If the fault code is empty or only whitespace.

        Notes:
            This method updates fault fields, but does not change
            ``alarm_state`` or clear a previously active fault.
        """
        if not fault_code or not fault_code.strip():
            raise ValueError("Fault code cannot be empty")

        self.fault_active = True
        self.fault_code = fault_code
        self.data_timestamp = datetime.now(timezone.utc)

        # Preserve each activation as a separate event for later inspection.
        self.fault_history.append({
            "equipment_id": self.equipment_id,
            "fault_code": fault_code,
            "timestamp": self.data_timestamp
        })

    def temperature_deviation_c(self):
        """Calculate actual minus target temperature in degrees Celsius.

        Returns:
            Signed deviation, or ``None`` when either reading is missing.
            A positive value means the actual temperature is above target.
        """
        if (
            self.actual_temperature_c is None
            or self.target_temperature_c is None
        ):
            return None

        return (
            self.actual_temperature_c
            - self.target_temperature_c
        )

    def calculate_heating_increase(self, elapsed_seconds):
        """Convert the configured heating rate into a temperature increase.

        Args:
            elapsed_seconds: Time interval in seconds; not validated here.

        Returns:
            Calculated increase in degrees Celsius, or ``None`` when no
            heating rate has been configured.
        """
        if self.heating_rate_c_per_min is None:
            return None

        return (
            self.heating_rate_c_per_min
            * elapsed_seconds / 60
        )

    def apply_heating(self, elapsed_seconds):
        """Raise temperature toward the configured target while heating.

        Args:
            elapsed_seconds: Nonnegative heating interval in seconds.

        Raises:
            ValueError: If the state or phase is invalid, a fault is active,
                time is negative, or temperature/rate inputs are invalid.

        Notes:
            Temperature is capped at the target. If already at or above
            target, the method leaves the reading and timestamp unchanged.
        """
        if self.operating_state != "RUNNING":
            raise ValueError("Equipment must be RUNNING")

        if self.cycle_phase != "HEATING":
            raise ValueError("Equipment must be HEATING")

        if self.fault_active:
            raise ValueError("Cannot heat with an active fault")

        if elapsed_seconds < 0:
            raise ValueError("Elapsed time cannot be negative")

        if self.actual_temperature_c is None:
            raise ValueError("Actual temperature is required")

        if self.target_temperature_c is None:
            raise ValueError("Target temperature is required")

        if (
            self.heating_rate_c_per_min is None
            or self.heating_rate_c_per_min <= 0
        ):
            raise ValueError("Positive heating rate is required")

        if self.actual_temperature_c >= self.target_temperature_c:
            return        

        increase = self.calculate_heating_increase(elapsed_seconds)

        # A process interval must not heat the model beyond its setpoint.
        self.actual_temperature_c = min(
            self.actual_temperature_c + increase,
            self.target_temperature_c
        )

        self.data_timestamp = datetime.now(timezone.utc)

    def remaining_hold_seconds(self):
        """Return uncompleted holding time, never less than zero.

        Returns:
            Remaining seconds, or ``None`` if no hold time is configured.
        """
        if self.required_hold_seconds is None:
            return None

        return max(
            0.0,
            self.required_hold_seconds - self.elapsed_hold_seconds
        )

    def apply_holding(self, elapsed_seconds):
        """Accumulate holding time while the furnace is exactly at target.

        Args:
            elapsed_seconds: Strictly positive time interval in seconds.

        Raises:
            ValueError: If the equipment cannot hold, an input is invalid,
                or actual and target temperatures are not equal.

        Notes:
            The accumulated duration is capped at the required hold time.
        """
        if self.operating_state != "RUNNING":
            raise ValueError("Equipment must be RUNNING")

        if self.cycle_phase != "HOLDING":
            raise ValueError("Equipment must be HOLDING")

        if self.fault_active:
            raise ValueError("Cannot hold with an active fault")

        if elapsed_seconds <= 0:
            raise ValueError("Elapsed time must be positive")

        if (
            self.required_hold_seconds is None
            or self.required_hold_seconds <= 0
        ):
            raise ValueError("Valid holding duration required")

        if (
            self.actual_temperature_c is None
            or self.target_temperature_c is None
        ):
            raise ValueError("Temperature readings required")

        if self.actual_temperature_c != self.target_temperature_c:
            raise ValueError("Furnace is not at target temperature")

        # Cap elapsed time rather than carrying overshoot into later phases.
        self.elapsed_hold_seconds = min(
            self.elapsed_hold_seconds + elapsed_seconds,
            self.required_hold_seconds
        )

        self.data_timestamp = datetime.now(timezone.utc)

    def apply_cooling(self, elapsed_seconds):
        """Lower temperature toward the configured cooling target.

        Args:
            elapsed_seconds: Strictly positive cooling interval in seconds.

        Raises:
            ValueError: If the equipment is not running and cooling, a fault
                is active, or time, temperature, or cooling rate is invalid.

        Notes:
            Cooling never lowers the temperature below the target. If the
            reading is already at or below target, no state is changed.
        """
        if self.operating_state != "RUNNING":
            raise ValueError("Equipment must be RUNNING")

        if self.cycle_phase != "COOLING":
            raise ValueError("Equipment must be COOLING")

        if self.fault_active:
            raise ValueError("Cannot cool with an active fault")

        if elapsed_seconds <= 0:
            raise ValueError("Elapsed time must be positive")

        if self.actual_temperature_c is None:
            raise ValueError("Actual temperature is required")

        if self.target_temperature_c is None:
            raise ValueError("Cooling target is required")

        if (
            self.cooling_rate_c_per_min is None
            or self.cooling_rate_c_per_min <= 0
        ):
            raise ValueError("Positive cooling rate required")

        if self.actual_temperature_c <= self.target_temperature_c:
            return

        decrease = (
            self.cooling_rate_c_per_min
            * elapsed_seconds / 60
        )

        # Prevent an oversized time interval from cooling below the setpoint.
        self.actual_temperature_c = max(
            self.actual_temperature_c - decrease,
            self.target_temperature_c
        )

        self.data_timestamp = datetime.now(timezone.utc)
