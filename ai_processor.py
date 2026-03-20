import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from typing import List, Optional
from groq import Groq
from models import TimeSlot, DayOfWeek, PreferenceLevel, Candidate, Assignment
from utils import parse_time_string
import re
from datetime import time

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq Client
API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = f"""
You are a precise time-parsing engine for 'SlotMaxxer'. 
Convert natural language into a JSON list of structured availability slots.

Allowed Day values: {[d.name for d in DayOfWeek]}
Allowed Preference values: {[p.value for p in PreferenceLevel]}

JSON Schema for each object:
{{
  "day": "MONDAY", 
  "start": "HH:MM", 
  "end": "HH:MM", 
  "is_recurring": false, 
  "preference": "medium"
}}

Rules:
1. Handle abbreviations (Mon, Tue) and ranges (Mon-Fri).
2. If time is ambiguous (e.g., "2-5"), assume PM for business context unless stated otherwise.
3. If no end time is specified, assume 1 hour duration.
4. If "morning" is mentioned, use 09:00 - 12:00.
5. If "afternoon" is mentioned, use 12:00 - 17:00.
6. Return ONLY a pure JSON list. No preamble or markdown blocks.
"""

# ── Day helpers ────────────────────────────────────────────────────────────────
_DAY_MAP = {
    "mon": DayOfWeek.MONDAY,    "monday":    DayOfWeek.MONDAY,
    "tue": DayOfWeek.TUESDAY,   "tuesday":   DayOfWeek.TUESDAY,
    "wed": DayOfWeek.WEDNESDAY, "wednesday": DayOfWeek.WEDNESDAY,
    "thu": DayOfWeek.THURSDAY,  "thursday":  DayOfWeek.THURSDAY,
    "fri": DayOfWeek.FRIDAY,    "friday":    DayOfWeek.FRIDAY,
    "sat": DayOfWeek.SATURDAY,  "saturday":  DayOfWeek.SATURDAY,
    "sun": DayOfWeek.SUNDAY,    "sunday":    DayOfWeek.SUNDAY,
}

_KEYWORD_DEFAULTS = {
    "morning":    (time(9,  0), time(12, 0)),
    "mornings":   (time(9,  0), time(12, 0)),
    "afternoon":  (time(12, 0), time(17, 0)),
    "afternoons": (time(12, 0), time(17, 0)),
    "evening":    (time(17, 0), time(20, 0)),
    "evenings":   (time(17, 0), time(20, 0)),
}

_DAY_ORDER = [
    DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
    DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY,
]


def _norm_hour(h: int, ampm: str) -> int:
    """Convert 12-hour to 24-hour. Digits 1-7 with no AM/PM → PM (business-hours heuristic)."""
    ampm = ampm.strip().upper()
    if ampm == "AM":
        return 0 if h == 12 else h
    if ampm == "PM":
        return h if h == 12 else h + 12
    # No AM/PM — infer from value
    if 1 <= h <= 7:
        return h + 12
    return h


def _day_range(start_key: str, end_key: str) -> List[DayOfWeek]:
    """Expand 'Mon-Wed' → [MONDAY, TUESDAY, WEDNESDAY]."""
    s = _DAY_MAP.get(start_key.lower())
    e = _DAY_MAP.get(end_key.lower())
    if s is None or e is None:
        return []
    si, ei = _DAY_ORDER.index(s), _DAY_ORDER.index(e)
    return _DAY_ORDER[si:ei + 1] if si <= ei else [s]


def _make_slot(day: DayOfWeek, start: time, end: time, recurring: bool = False) -> Optional[TimeSlot]:
    try:
        return TimeSlot(day=day, start_time=start, end_time=end, is_recurring=recurring)
    except ValueError:
        return None


class DeterministicParser:
    """
    Regex-based availability parser — handles ~90% of common formats without AI.
    Returns [] when no patterns match, so the caller can fall back to Groq.

    Patterns handled (in priority order):
      P4  day-range + keyword   "Mon-Fri mornings"
      P2  day-range + times     "Mon-Wed 9 AM-5 PM"
      P3  single-day + keyword  "Tuesday afternoon"
      P1  single-day + times    "Tue 2-5 PM" | "Every Monday 10-11 AM"
    """

    # P1: optional "Every" + single day + time range
    _P1 = re.compile(
        r"(?:every\s+)?"
        r"(mon|tue|wed|thu|fri|sat|sun)\w*"
        r"\s+"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:\s*(AM|PM))?"
        r"\s*[-–to]+\s*"
        r"(\d{1,2})(?::(\d{2}))?"
        r"\s*(AM|PM)?",
        re.IGNORECASE,
    )

    # P2: day range + time range
    _P2 = re.compile(
        r"(mon|tue|wed|thu|fri|sat|sun)\w*"
        r"\s*[-–]\s*"
        r"(mon|tue|wed|thu|fri|sat|sun)\w*"
        r"\s+"
        r"(\d{1,2})(?::(\d{2}))?"
        r"\s*(AM|PM)?"
        r"\s*[-–to]+\s*"
        r"(\d{1,2})(?::(\d{2}))?"
        r"\s*(AM|PM)?",
        re.IGNORECASE,
    )

    # P3: single day + keyword
    _P3 = re.compile(
        r"(?:every\s+)?"
        r"(mon|tue|wed|thu|fri|sat|sun)\w*"
        r"\s+"
        r"(morning|mornings|afternoon|afternoons|evening|evenings)",
        re.IGNORECASE,
    )

    # P4: day range + keyword
    _P4 = re.compile(
        r"(mon|tue|wed|thu|fri|sat|sun)\w*"
        r"\s*[-–]\s*"
        r"(mon|tue|wed|thu|fri|sat|sun)\w*"
        r"\s+"
        r"(morning|mornings|afternoon|afternoons|evening|evenings)",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, text: str) -> List[TimeSlot]:
        slots: List[TimeSlot] = []
        used: List[tuple] = []  # track matched spans to avoid double-counting

        # ── P4: day-range + keyword ──────────────────────────────────────────
        for m in cls._P4.finditer(text):
            t_s, t_e = _KEYWORD_DEFAULTS.get(m.group(3).lower(), (time(9,0), time(17,0)))
            for day in _day_range(m.group(1), m.group(2)):
                s = _make_slot(day, t_s, t_e)
                if s:
                    slots.append(s)
            used.append(m.span())

        # ── P2: day-range + explicit times ───────────────────────────────────
        for m in cls._P2.finditer(text):
            if any(m.start() >= a and m.end() <= b for a, b in used):
                continue
            sh, sm = int(m.group(3)), int(m.group(4) or 0)
            eh, em = int(m.group(6)), int(m.group(7) or 0)
            sp = (m.group(5) or "").upper()
            ep = (m.group(8) or "").upper()
            if not sp and ep:
                sp = ep
            for day in _day_range(m.group(1), m.group(2)):
                s = _make_slot(day, time(_norm_hour(sh, sp), sm), time(_norm_hour(eh, ep), em))
                if s:
                    slots.append(s)
            used.append(m.span())

        # ── P3: single-day + keyword ─────────────────────────────────────────
        for m in cls._P3.finditer(text):
            if any(m.start() >= a and m.end() <= b for a, b in used):
                continue
            day = _DAY_MAP.get(m.group(1).lower())
            if not day:
                continue
            t_s, t_e = _KEYWORD_DEFAULTS.get(m.group(2).lower(), (time(9,0), time(17,0)))
            recurring = bool(re.search(r"\bevery\b", m.group(0), re.I))
            s = _make_slot(day, t_s, t_e, recurring=recurring)
            if s:
                slots.append(s)
            used.append(m.span())

        # ── P1: single-day + explicit times ──────────────────────────────────
        for m in cls._P1.finditer(text):
            if any(m.start() >= a and m.end() <= b for a, b in used):
                continue
            day = _DAY_MAP.get(m.group(1).lower())
            if not day:
                continue
            sh, sm = int(m.group(2)), int(m.group(3) or 0)
            eh, em = int(m.group(5)), int(m.group(6) or 0)
            ep = (m.group(7) or "").upper()
            recurring = bool(re.search(r"\bevery\b", m.group(0), re.I))
            s = _make_slot(day, time(_norm_hour(sh, ep), sm), time(_norm_hour(eh, ep), em), recurring=recurring)
            if s:
                slots.append(s)
            used.append(m.span())

        return slots


def parse_availability_with_ai(text: str) -> List[TimeSlot]:
    """
    Primary availability parser.
      1. DeterministicParser  — instant, zero-cost regex (covers ~90% of inputs)
      2. Groq AI              — only for ambiguous natural language
      3. parse_time_string    — last-resort rule-based fallback
    """
    # ── Step 1: Deterministic ─────────────────────────────────────────────────
    det_slots = DeterministicParser.parse(text)
    if det_slots:
        logger.info(f"DeterministicParser: '{text[:60]}' → {len(det_slots)} slot(s)")
        return det_slots

    # ── Step 2: Groq AI ───────────────────────────────────────────────────────
    if not client:
        logger.warning("GROQ_API_KEY not found. Falling back to rule-based parser.")
        return parse_time_string(text)

    try:
        # Groq AI Parsing
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse: {text}"}
            ],
            temperature=0,  # Deterministic output
            max_tokens=500
        )

        raw_json = response.choices[0].message.content.strip()
        # Strip potential markdown fences
        if "```" in raw_json:
            raw_json = raw_json.split("```")[1].replace("json", "").strip()

        data = json.loads(raw_json)
        
        parsed_slots = []
        for item in data:
            try:
                start_h, start_m = map(int, item["start"].split(":"))
                end_h, end_m = map(int, item["end"].split(":"))
                
                parsed_slots.append(
                    TimeSlot(
                        day=DayOfWeek[item["day"]],
                        start_time=time(start_h, start_m),
                        end_time=time(end_h, end_m),
                        is_recurring=item.get("is_recurring", False),
                        preference_level=PreferenceLevel(item.get("preference", "medium"))
                    )
                )
            except (ValueError, KeyError) as e:
                logger.error(f"Failed to map AI output fragment: {item} -> {e}")
                continue
                
        return parsed_slots if parsed_slots else parse_time_string(text)

    except Exception as e:
        logger.error(f"Groq API Error: {e}. Falling back to rule-based parser.")
        return parse_time_string(text)


def generate_assignment_reasoning(
    candidate_name: str,
    interviewer_name: str,
    slot: TimeSlot,
    score: int,
    is_preferred: bool = False
) -> str:
    """
    Generates a natural language explanation for why a specific slot was chosen.
    """
    if not client:
        return f"Matched based on overall quality score ({score}) and mutual availability."

    try:
        prompt = f"""
        Explain why {candidate_name} was scheduled with {interviewer_name} 
        at {slot.day.value} {slot.start_time.strftime('%H:%M')}.
        Context:
        - Quality Score: {score}
        - Matches Candidate Preference: {is_preferred}
        - Constraints: { 'High priority' if score > 2000 else 'System-optimized' }
        
        Rules: Max 2-3 sentences. Enthusiastic but professional.
        """
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You provide short, helpful interview scheduling justifications."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Reasoning Gen Error: {e}")
        return f"Optimal assignment considering both preference and resource scarcity (Score: {score})."


def resolve_conflicts_with_ai(
    unassigned: List[Candidate],
    assignments: List[Assignment],
    feasible_matrix: List[tuple]
) -> str:
    """
    Analyzes the scheduling impasse and suggests strategic fixes (swaps, expansions).
    """
    if not unassigned:
        return "No conflicts detected. All candidates successfully assigned."

    # Build a condensed representation of the conflict for the AI
    conflict_report = []
    for c in unassigned:
        # Find all the 'what-could-have-been' slots for this candidate
        potentials = [f"{t[2].name} at {t[1]}" for t in feasible_matrix if t[0].id == c.id]
        conflict_report.append(f"Candidate {c.name} had {len(potentials)} potential slots, but all were blocked by existing assignments.")

    if not client:
        return (
            "Conflict detected: Interviewer capacity reached or slots double-booked. \n"
            "Fallback Recommendation: Add more availability for high-demand interviewers or "
            "request additional time windows from unassigned candidates."
        )

    try:
        prompt = f"""
        Analyze the following scheduling impasse for SlotMaxxer:
        
        Unassigned Status:
        {chr(10).join(conflict_report)}
        
        Successful Assignments:
        {chr(10).join([f"{a.candidate_id} matched with {a.interviewer_id}" for a in assignments])}
        
        Task: Provide 3 prioritized action items (swaps, availability requests, or window expansions).
        Rules: Professional tone. Max 4 sentences. Bullet points.
        """
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a master logistics optimizer for hiring teams."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=250
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Conflict Resolution Error: {e}")
        return "Critical conflict detected. Recommendation: Request additional availability slots from unassigned candidates or substitute interviewers."


if __name__ == "__main__":
    # Test cases
    test_input = "Tue and Thu from 2 to 5 PM, but I prefer Thursday afternoon"
    print(f"Testing with: {test_input}")
    
    # If no API key, you should see the fallback in action
    slots = parse_availability_with_ai(test_input)
    print("Parsed Slots:")
    for s in slots:
        print(f" - {s}")
