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
from datetime import time

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq Client
# Ensure GROQ_API_KEY is set in your environment
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

def parse_availability_with_ai(text: str) -> List[TimeSlot]:
    """
    Primary tool for parsing candidate/interviewer availability.
    Uses Groq for LLM-based extraction with a deterministic regex fallback.
    """
    # 1. Check for API key and client validity
    if not client:
        logger.warning("GROQ_API_KEY not found. Falling back to rule-based parser.")
        return parse_time_string(text)

    try:
        # 2. AI Parsing Attempt
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
