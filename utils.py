import re
from datetime import time, date, timedelta, datetime
from typing import List, Optional
from models import DayOfWeek, TimeSlot

# Mapping of search terms to DayOfWeek members
DAYS_MAP = {
    "mon": DayOfWeek.MONDAY, "monday": DayOfWeek.MONDAY,
    "tue": DayOfWeek.TUESDAY, "tuesday": DayOfWeek.TUESDAY,
    "wed": DayOfWeek.WEDNESDAY, "wednesday": DayOfWeek.WEDNESDAY,
    "thu": DayOfWeek.THURSDAY, "thursday": DayOfWeek.THURSDAY,
    "fri": DayOfWeek.FRIDAY, "friday": DayOfWeek.FRIDAY,
    "sat": DayOfWeek.SATURDAY, "saturday": DayOfWeek.SATURDAY,
    "sun": DayOfWeek.SUNDAY, "sunday": DayOfWeek.SUNDAY
}

# Order of days according to Python's weekday() (Monday=0, Sunday=6)
DAY_ORDER = [
    DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
    DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY
]

# Standard keyword time definitions
TIME_KEYWORDS = {
    "morning": (time(9, 0), time(12, 0)),
    "afternoon": (time(12, 0), time(17, 0)),
    "evening": (time(17, 0), time(20, 0))
}

# Regex to match 12-hour or 24-hour time strings
TIME_REGEX = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"


def _parse_hour(h: str, m: Optional[str], meridiem: Optional[str]) -> time:
    """Helper to parse raw regex groups into a datetime.time object."""
    hour = int(h)
    minute = int(m) if m else 0
    if meridiem:
        meridiem = meridiem.lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
    return time(hour, minute)


def parse_time_string(s: str) -> List[TimeSlot]:
    """
    Parses a natural language time string into a list of TimeSlot objects.
    Handles abbreviations, ranges (Mon-Fri), keywords, and 12/24 hour formats.

    Examples:
    >>> slots = parse_time_string("Tue 2-5 PM")
    >>> slots[0]
    [TUESDAY 14:00-17:00]
    >>> slots = parse_time_string("Mon/Wed morning")
    >>> [s.day.value for s in slots]
    ['MONDAY', 'WEDNESDAY']
    >>> slots = parse_time_string("Mon-Wed 9 AM - 4 PM")
    >>> len(slots)
    3
    """
    s = s.lower().strip()
    is_recurring = "every" in s or "weekly" in s
    s = s.replace("every", "").replace("weekly", "").strip()

    # Detect keyword-based times (morning/afternoon/evening)
    keyword_found = None
    for k in TIME_KEYWORDS:
        if k in s:
            keyword_found = k
            break

    # Determine split point between days and time
    match_time = re.search(r"\d", s)
    separator_index = -1
    if keyword_found and match_time:
        separator_index = min(s.find(keyword_found), match_time.start())
    elif keyword_found:
        separator_index = s.find(keyword_found)
    elif match_time:
        separator_index = match_time.start()

    if separator_index == -1:
        return []

    days_part = s[:separator_index].strip().rstrip(",/")
    time_part = s[separator_index:].strip()

    # 1. Parse Days
    target_days = []
    # Check for range: "Mon-Fri"
    range_match = re.search(r"(\w+)\s*-\s*(\w+)", days_part)
    if range_match:
        start_day_str, end_day_str = range_match.groups()
        if start_day_str in DAYS_MAP and end_day_str in DAYS_MAP:
            start_idx = DAY_ORDER.index(DAYS_MAP[start_day_str])
            end_idx = DAY_ORDER.index(DAYS_MAP[end_day_str])
            if start_idx <= end_idx:
                target_days = DAY_ORDER[start_idx : end_idx + 1]
            else:
                # Wrap-around support (e.g., Fri-Mon)
                target_days = DAY_ORDER[start_idx:] + DAY_ORDER[: end_idx + 1]

    if not target_days:
        # Check for list/single: "Mon, Wed" or "Mon/Wed" or "Monday"
        for word in re.split(r"[,/ ]+", days_part):
            if word in DAYS_MAP:
                target_days.append(DAYS_MAP[word])

    # 2. Parse Time
    start_t, end_t = None, None
    if keyword_found:
        start_t, end_t = TIME_KEYWORDS[keyword_found]
    else:
        times = re.findall(TIME_REGEX, time_part)
        if len(times) >= 2:
            t1_h, t1_m, t1_mer = times[0]
            t2_h, t2_m, t2_mer = times[1]

            # Meridiem inference (e.g., "2-5 PM")
            if not t1_mer and t2_mer:
                h1, h2 = int(t1_h), int(t2_h)
                if t2_mer == "pm" and h1 < h2 and h1 != 12:
                    t1_mer = "pm"
                elif t2_mer == "pm" and h1 > h2:
                    # e.g., "11-1 PM"
                    t1_mer = "am"
                else:
                    t1_mer = t2_mer

            start_t = _parse_hour(t1_h, t1_m, t1_mer)
            end_t = _parse_hour(t2_h, t2_m, t2_mer)
        elif len(times) == 1:
            t1_h, t1_m, t1_mer = times[0]
            start_t = _parse_hour(t1_h, t1_m, t1_mer)
            # Default to 60-minute duration as per PRD
            dummy_dt = datetime.combine(date.today(), start_t) + timedelta(minutes=60)
            end_t = dummy_dt.time()

    if not start_t or not end_t or not target_days:
        return []

    return [
        TimeSlot(day=d, start_time=start_t, end_time=end_t, is_recurring=is_recurring)
        for d in target_days
    ]


def expand_recurring_availability(slots: List[TimeSlot], weeks: int = 4) -> List[TimeSlot]:
    """
    Expands recurring slots into specific instances for the next N weeks.
    Includes:
    - Deduplication: Prevents duplicate identical slots on the same date.
    - Validation: Skips slots that occurred in the past (including earlier today).
    """
    expanded_slots = []
    base_date = date.today()
    now_time = datetime.now().time()
    
    # Tracking to prevent duplicate entries
    seen = set()

    for slot in slots:
        # Determine the first occurrence date based on the day of the week
        day_idx = DAY_ORDER.index(slot.day)
        days_ahead = (day_idx - base_date.weekday()) % 7
        
        # If the day was today but the time has passed, jump to next week
        # for non-recurring or just skip the first instance for recurring
        first_occurrence = base_date + timedelta(days=days_ahead)
        
        # Determine how many instances to generate
        iterations = weeks if slot.is_recurring else 1
        
        for i in range(iterations):
            occurrence_date = first_occurrence + timedelta(weeks=i)
            
            # Validation: Skip if date/time is in the past
            if occurrence_date < base_date:
                continue
            if occurrence_date == base_date and slot.end_time <= now_time:
                continue
                
            # Deduplication check
            identity = (occurrence_date, slot.start_time, slot.end_time)
            if identity in seen:
                continue
            
            expanded_slots.append(
                TimeSlot(
                    day=slot.day,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    date=occurrence_date,
                    is_recurring=slot.is_recurring,
                    preference_level=slot.preference_level
                )
            )
            seen.add(identity)

    return expanded_slots



def generate_email_template(candidate_name: str, interviewer_name: str, slot_text: str, reasoning: str, alternatives: list = None) -> str:
    """
    Generates a professional, recruiter-ready email invitation for the candidate.
    """
    alt_text = ""
    if alternatives:
        alt_text = "\n\nIf this time doesn't work, we have these backup options:\n" + \
                   "\n".join([f"- {a}" for a in alternatives])

    template = f"""
Subject: Interview Invitation: [SlotMaxxer] {candidate_name} x {interviewer_name}

Hi {candidate_name},

Great news! We've optimized our panel's availability and would like to invite you for an interview with {interviewer_name}.

📅 Confirmed Time: {slot_text}

---
💡 Why this slot was chosen:
"{reasoning}"
---
{alt_text}

📍 Calendar Invite Details:
Summary: Interview with {interviewer_name}
Time: {slot_text}
Platform: Video Link to follow

Please confirm if this works for you!

Best regards,
SlotMaxxer Scheduling Team
    """
    return template.strip()


if __name__ == "__main__":
    # Small test loop for manual verification
    tests = [
        "Tue 2-5 PM",
        "Mon-Fri 9 AM-4 PM",
        "Wed morning",
        "Every Tuesday afternoon"
    ]
    for t in tests:
        print(f"Input: {t}")
        parsed = parse_time_string(t)
        print(f"Parsed: {parsed}\n")
