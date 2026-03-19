import os
import json
import logging
from typing import List, Optional
from groq import Groq
from models import TimeSlot, DayOfWeek, PreferenceLevel
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
            model="llama3-70b-8192",
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


if __name__ == "__main__":
    # Test cases
    test_input = "Tue and Thu from 2 to 5 PM, but I prefer Thursday afternoon"
    print(f"Testing with: {test_input}")
    
    # If no API key, you should see the fallback in action
    slots = parse_availability_with_ai(test_input)
    print("Parsed Slots:")
    for s in slots:
        print(f" - {s}")
