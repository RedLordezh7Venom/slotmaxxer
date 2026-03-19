from dataclasses import dataclass, field
from datetime import time, timedelta, date
from enum import Enum
from typing import List, Optional


class DayOfWeek(Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class PreferenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class TimeSlot:
    """
    Represents a discrete window of time on a specific day of the week.
    """
    day: DayOfWeek
    start_time: time
    end_time: time
    date: Optional[date] = None
    is_recurring: bool = False
    preference_level: PreferenceLevel = PreferenceLevel.MEDIUM

    def __post_init__(self):
        # Validation: Ensure logical time sequence
        if self.start_time >= self.end_time:
            raise ValueError(
                f"Invalid TimeSlot: start_time ({self.start_time}) "
                f"must be before end_time ({self.end_time})"
            )

    @property
    def duration_minutes(self) -> int:
        """Calculates the duration of the slot in minutes."""
        start_delta = timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)
        end_delta = timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)
        return int((end_delta - start_delta).total_seconds() // 60)

    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """Checks if this slot overlaps with another slot."""
        if self.day != other.day:
            return False
        # (StartA < EndB) and (EndA > StartB)
        return self.start_time < other.end_time and self.end_time > other.start_time

    def contains(self, other: 'TimeSlot') -> bool:
        """Checks if this slot fully contains another (must be same day)."""
        if self.day != other.day:
            return False
        return self.start_time <= other.start_time and self.end_time >= other.end_time

    def __repr__(self) -> str:
        recurring_suffix = " (R)" if self.is_recurring else ""
        return (
            f"[{self.day.value} {self.start_time.strftime('%H:%M')}-"
            f"{self.end_time.strftime('%H:%M')}{recurring_suffix}]"
        )


@dataclass
class Candidate:
    """
    Represents an interview candidate and their availability preferences.
    """
    id: str
    name: str
    email: str
    availability: List[TimeSlot] = field(default_factory=list)
    preferred_slots: List[TimeSlot] = field(default_factory=list)
    role: Optional[str] = None

    def __repr__(self) -> str:
        return f"Candidate(id={self.id}, name='{self.name}', role='{self.role}')"


@dataclass
class Interviewer:
    """
    Represents an interviewer, their availability, and bandwidth constraints.
    """
    id: str
    name: str
    availability: List[TimeSlot] = field(default_factory=list)
    preferred_slots: List[TimeSlot] = field(default_factory=list)
    capacity: int = 5  # Max interviews per week
    seniority: str = "senior"

    def __repr__(self) -> str:
        return f"Interviewer(id={self.id}, name='{self.name}', capacity={self.capacity})"


@dataclass
class Assignment:
    """
    Represents a finalized interview assignment with quality metrics and reasoning.
    """
    candidate_id: str
    interviewer_id: str
    slot: TimeSlot
    quality_score: int
    reasoning: str
    alternatives: List[TimeSlot] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Assignment: {self.candidate_id} ↔ {self.interviewer_id} "
            f"at {self.slot} (Score: {self.quality_score})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Assignment):
            return NotImplemented
        return (
            self.candidate_id == other.candidate_id and
            self.interviewer_id == other.interviewer_id and
            self.slot == other.slot
        )
