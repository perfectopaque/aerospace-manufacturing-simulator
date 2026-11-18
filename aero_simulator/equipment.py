from dataclasses import dataclass, field
from datetime import datetime, timezone

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
    if current_phase not in phases:
        raise ValueError("Unknown manufacturing phase")

    current_index = phases.index(current_phase)

    if current_index == len(phases) - 1:
        raise ValueError("Manufacturing cycle already complete")

    return phases[current_index + 1]

@dataclass
class Equipment:
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
    required_hold_seconds: float | None = None
    elapsed_hold_seconds: float = 0.0
    fault_history: list[dict] = field(default_factory=list)

    data_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def advance_phase(self, phases):
        if self.operating_state != "RUNNING":
            raise ValueError("Equipment must be RUNNING")

        if self.fault_active:
            raise ValueError("Cannot advance with active fault")

        self.cycle_phase = next_phase(
            self.cycle_phase, phases
        )

        self.data_timestamp = datetime.now(timezone.utc)

    def activate_fault(self, fault_code):
        if not fault_code or not fault_code.strip():
            raise ValueError("Fault code cannot be empty")

        self.fault_active = True
        self.fault_code = fault_code
        self.data_timestamp = datetime.now(timezone.utc)

        self.fault_history.append({
            "equipment_id": self.equipment_id,
            "fault_code": fault_code,
            "timestamp": self.data_timestamp
        })

    def temperature_deviation_c(self):
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
        if self.heating_rate_c_per_min is None:
            return None

        return (
            self.heating_rate_c_per_min
            * elapsed_seconds / 60
        )

    def apply_heating(self, elapsed_seconds):
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

        self.actual_temperature_c = min(
            self.actual_temperature_c + increase,
            self.target_temperature_c
        )

        self.data_timestamp = datetime.now(timezone.utc)

    def remaining_hold_seconds(self):
        if self.required_hold_seconds is None:
            return None

        return max(
            0.0,
            self.required_hold_seconds - self.elapsed_hold_seconds
        )

    def apply_holding(self, elapsed_seconds):
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

        self.elapsed_hold_seconds = min(
            self.elapsed_hold_seconds + elapsed_seconds,
            self.required_hold_seconds
        )

        self.data_timestamp = datetime.now(timezone.utc)

