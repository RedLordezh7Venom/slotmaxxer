from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
from models import Candidate, Interviewer, TimeSlot


def generate_feasible_assignments(
    candidates: List[Candidate], 
    interviewers: List[Interviewer],
    required_duration: int = 60,
    discretization_step: int = 30
) -> List[Tuple[Candidate, TimeSlot, Interviewer]]:
    """
    Generates all valid (Candidate, Slot, Interviewer) triplets.
    This fulfills Step 1 of the scheduling algorithm by identifying all 
    possible intersections that meet the minimum duration requirements.

    Algorithm Complexity: O(C * Sc * I * Si * D)
    - C: Number of Candidates
    - Sc: Average slots per Candidate
    - I: Number of Interviewers
    - Si: Average slots per Interviewer
    - D: Discretization density (how many segments fit in an intersection)
    
    Worst-case (PRD scale): 10 * 10 * 5 * 10 * 4 = 20,000 checks. 
    This remains well within the <2s performance requirement for any CPU.

    Returns:
        List of (Candidate, SpecificSlot, Interviewer) triplets.
    """
    all_triplets = []

    for candidate in candidates:
        # Cross-reference with every interviewer
        for interviewer in interviewers:
            # Check every combination of their available availability
            # Note: We assume availability has been expanded to instances (with dates)
            # if we are scheduling for specific weeks.
            for c_slot in candidate.availability:
                for i_slot in interviewer.availability:
                    # Check for basic day/time overlap
                    common_window = c_slot.intersection(i_slot)
                    
                    if common_window and common_window.duration_minutes >= required_duration:
                        # The window might be large (e.g., 4 hours).
                        # We discretize it into segments (e.g., every 30 mins) 
                        # to give the solver more flexibility in picking the optimal one.
                        segments = get_slots_within_window(
                            common_window, 
                            required_duration, 
                            discretization_step
                        )
                        
                        for segment in segments:
                            all_triplets.append((candidate, segment, interviewer))

    return all_triplets


def get_slots_within_window(
    window: TimeSlot, 
    duration: int, 
    step: int = 30
) -> List[TimeSlot]:
    """
    Slices a continuous time window into multiple discrete TimeSlot options.
    If duration is 60 and step is 30, a 2-hour window yields 3 potential slots:
    Start at 0:00, 0:30, 1:00.
    """
    slots = []
    current_start_time = window.start_time
    
    # We use a dummy date for timedelta math if none exists
    ref_date = window.date if window.date else date.today()
    window_end_dt = datetime.combine(ref_date, window.end_time)

    while True:
        start_dt = datetime.combine(ref_date, current_start_time)
        end_dt = start_dt + timedelta(minutes=duration)

        # Stop if this next slot goes beyond the window's boundary
        if end_dt > window_end_dt:
            break

        slots.append(TimeSlot(
            day=window.day,
            start_time=current_start_time,
            end_time=end_dt.time(),
            date=window.date,
            is_recurring=window.is_recurring,
            preference_level=window.preference_level
        ))

        # Advance by the step
        current_start_time = (start_dt + timedelta(minutes=step)).time()
        
        # Safety break for midnight roll-over (if any)
        if current_start_time < window.start_time:
            break

    return slots


if __name__ == "__main__":
    # Small test
    from datetime import time
    from models import DayOfWeek
    
    print("Testing feasibility matrix generation...")
    c = Candidate("C1", "Jane", "jane@test.com", availability=[
        TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(12, 0))
    ])
    i = Interviewer("I1", "Boss", availability=[
        TimeSlot(DayOfWeek.MONDAY, time(11, 0), time(14, 0))
    ])
    
    triplets = generate_feasible_assignments([c], [i], required_duration=60)
    print(f"Generated {len(triplets)} triplets for 1-hour overlap")
    for _, slot, _ in triplets:
        print(f" - Segment: {slot.start_time.strftime('%H:%M')} to {slot.end_time.strftime('%H:%M')}")
