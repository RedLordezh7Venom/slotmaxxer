"""
SlotMaxxer Test Dataset Generator
Generates realistic test data for edge cases and stress testing
"""

import json
import random
from datetime import time, date, timedelta
from typing import List, Dict


class TestDatasetGenerator:
    """Generate realistic test datasets for SlotMaxxer"""
    
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry", 
                   "Iris", "Jack", "Kate", "Liam", "Maya", "Noah", "Olivia", "Peter"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson"]
    
    @staticmethod
    def generate_time_string(hour: int, end_hour: int) -> str:
        """Generate time string in format 'HH:MM AM/PM - HH:MM AM/PM'"""
        def format_hour(h):
            if h == 0:
                return "12:00 AM"
            elif h < 12:
                return f"{h}:00 AM"
            elif h == 12:
                return "12:00 PM"
            else:
                return f"{h-12}:00 PM"
        
        return f"{format_hour(hour)} - {format_hour(end_hour)}"
    
    @classmethod
    def generate_candidate(cls, idx: int, complexity: str = "simple") -> Dict:
        """Generate a candidate with varying complexity"""
        name = f"{random.choice(cls.FIRST_NAMES)} {random.choice(cls.LAST_NAMES)}"
        email = f"{name.lower().replace(' ', '.')}@example.com"
        
        if complexity == "simple":
            # Single continuous availability
            day = random.choice(cls.DAYS)
            start_hour = random.randint(9, 12)
            end_hour = start_hour + random.randint(2, 5)
            availability = f"{day} {cls.generate_time_string(start_hour, end_hour)}"
        
        elif complexity == "medium":
            # Multiple days, specific times
            days = random.sample(cls.DAYS, k=random.randint(2, 3))
            availability_parts = []
            for day in days:
                start_hour = random.randint(9, 14)
                end_hour = start_hour + random.randint(1, 3)
                availability_parts.append(f"{day} {cls.generate_time_string(start_hour, end_hour)}")
            availability = ", ".join(availability_parts)
        
        else:  # complex
            # Natural language with preferences
            templates = [
                "Weekday mornings preferred, afternoons also possible",
                "Tue-Thu 2-5 PM, flexible on Mon/Fri",
                "Any day except Wednesday, mornings best",
                "Monday afternoon or Tuesday/Thursday anytime"
            ]
            availability = random.choice(templates)
        
        return {
            "name": name,
            "email": email,
            "availability": availability
        }
    
    @classmethod
    def generate_interviewer(cls, idx: int, availability_level: str = "medium") -> Dict:
        """Generate interviewer with varying availability"""
        name = f"{random.choice(cls.FIRST_NAMES)} {random.choice(cls.LAST_NAMES)} (Interviewer)"
        
        if availability_level == "low":
            # Very limited availability (scarce resource)
            day = random.choice(cls.DAYS)
            start_hour = random.randint(10, 14)
            end_hour = start_hour + 2
            availability = f"{day} {cls.generate_time_string(start_hour, end_hour)}"
        
        elif availability_level == "medium":
            # Moderate availability
            days = random.sample(cls.DAYS, k=random.randint(2, 3))
            availability_parts = []
            for day in days:
                start_hour = random.randint(9, 13)
                end_hour = start_hour + random.randint(2, 4)
                availability_parts.append(f"{day} {cls.generate_time_string(start_hour, end_hour)}")
            availability = ", ".join(availability_parts)
        
        else:  # high
            # Very flexible
            availability = "Monday-Friday 9 AM - 5 PM"
        
        return {
            "name": name,
            "availability": availability
        }
    
    @classmethod
    def generate_edge_case_dataset(cls, case_name: str) -> Dict:
        """Generate specific edge case datasets"""
        
        if case_name == "no_overlap":
            return {
                "candidates": [
                    {"name": "Jane Doe", "availability": "Tuesday 2-5 PM"}
                ],
                "interviewers": [
                    {"name": "Interviewer A", "availability": "Wednesday 2-5 PM"}
                ],
                "expected_outcome": "no_assignments"
            }
        
        elif case_name == "partial_overlap":
            return {
                "candidates": [
                    {"name": "John Smith", "availability": "Monday 2-3 PM"}
                ],
                "interviewers": [
                    {"name": "Interviewer B", "availability": "Monday 2:30-5 PM"}
                ],
                "expected_outcome": "insufficient_duration"
            }
        
        elif case_name == "capacity_exhaustion":
            return {
                "candidates": [
                    cls.generate_candidate(i, "simple") for i in range(5)
                ],
                "interviewers": [
                    {"name": "Interviewer X", "availability": "Monday 10-11 AM"},
                    {"name": "Interviewer Y", "availability": "Monday 2-3 PM"}
                ],
                "expected_outcome": "3_unassigned"
            }
        
        elif case_name == "unicode_names":
            return {
                "candidates": [
                    {"name": "José García", "availability": "Tuesday 2-5 PM"},
                    {"name": "李明", "availability": "Wednesday 10 AM-1 PM"},
                    {"name": "Müller", "availability": "Thursday 9 AM-12 PM"}
                ],
                "interviewers": [
                    {"name": "Владимир Петров", "availability": "Tue-Thu 10 AM-4 PM"}
                ],
                "expected_outcome": "all_assigned"
            }
        
        elif case_name == "recurring_availability":
            return {
                "candidates": [
                    {"name": "Sarah Connor", "availability": "Every Tuesday 2-5 PM"}
                ],
                "interviewers": [
                    {"name": "John Connor", "availability": "Every Tuesday 3-6 PM"}
                ],
                "expected_outcome": "recurring_match"
            }
        
        else:
            raise ValueError(f"Unknown edge case: {case_name}")
    
    @classmethod
    def generate_stress_test_dataset(cls, num_candidates: int, num_interviewers: int) -> Dict:
        """Generate large-scale stress test dataset"""
        
        # Mix of complexity levels
        complexity_distribution = ["simple"] * 50 + ["medium"] * 30 + ["complex"] * 20
        availability_distribution = ["low"] * 20 + ["medium"] * 50 + ["high"] * 30
        
        candidates = [
            cls.generate_candidate(i, random.choice(complexity_distribution))
            for i in range(num_candidates)
        ]
        
        interviewers = [
            cls.generate_interviewer(i, random.choice(availability_distribution))
            for i in range(num_interviewers)
        ]
        
        return {
            "candidates": candidates,
            "interviewers": interviewers,
            "interview_duration_minutes": 60
        }
    
    @classmethod
    def generate_realistic_scenario(cls, scenario_name: str) -> Dict:
        """Generate realistic hiring scenarios"""
        
        if scenario_name == "startup_hiring":
            # 3-4 candidates, 2-3 interviewers, tight schedules
            return {
                "candidates": [
                    {"name": "Alice Chen", "availability": "Tue-Thu afternoons preferred"},
                    {"name": "Bob Miller", "availability": "Mon/Wed mornings, Fri anytime"},
                    {"name": "Carol Davis", "availability": "Flexible weekdays 9-5"}
                ],
                "interviewers": [
                    {"name": "CTO (David)", "availability": "Tue 2-4 PM, Thu 10 AM-12 PM"},
                    {"name": "Lead Engineer (Emma)", "availability": "Mon-Thu 2-5 PM"}
                ],
                "interview_duration_minutes": 60
            }
        
        elif scenario_name == "enterprise_hiring":
            # 10+ candidates, 5+ interviewers, varied schedules
            return cls.generate_stress_test_dataset(12, 6)
        
        elif scenario_name == "interview_day":
            # Single day, back-to-back interviews
            return {
                "candidates": [
                    {"name": f"Candidate {i}", "availability": "Friday 9 AM - 5 PM"}
                    for i in range(1, 6)
                ],
                "interviewers": [
                    {"name": "Panel Member A", "availability": "Friday 9 AM - 12 PM"},
                    {"name": "Panel Member B", "availability": "Friday 1 PM - 5 PM"},
                    {"name": "Panel Member C", "availability": "Friday 10 AM - 4 PM"}
                ],
                "interview_duration_minutes": 60
            }
        
        else:
            raise ValueError(f"Unknown scenario: {scenario_name}")


def generate_all_test_datasets():
    """Generate and save all test datasets"""
    
    gen = TestDatasetGenerator()
    
    # Edge case datasets
    edge_cases = {
        "no_overlap": gen.generate_edge_case_dataset("no_overlap"),
        "partial_overlap": gen.generate_edge_case_dataset("partial_overlap"),
        "capacity_exhaustion": gen.generate_edge_case_dataset("capacity_exhaustion"),
        "unicode_names": gen.generate_edge_case_dataset("unicode_names"),
        "recurring_availability": gen.generate_edge_case_dataset("recurring_availability")
    }
    
    with open("tests/data/edge_cases.json", "w", encoding="utf-8") as f:
        json.dump(edge_cases, f, indent=2, ensure_ascii=False)
    
    # Stress test datasets
    stress_tests = {
        "small_scale": gen.generate_stress_test_dataset(10, 5),
        "medium_scale": gen.generate_stress_test_dataset(50, 10),
        "large_scale": gen.generate_stress_test_dataset(100, 10)
    }
    
    with open("tests/data/stress.json", "w") as f:
        json.dump(stress_tests, f, indent=2)
    
    # Realistic scenarios
    scenarios = {
        "startup_hiring": gen.generate_realistic_scenario("startup_hiring"),
        "enterprise_hiring": gen.generate_realistic_scenario("enterprise_hiring"),
        "interview_day": gen.generate_realistic_scenario("interview_day")
    }
    
    with open("tests/data/scenarios.json", "w") as f:
        json.dump(scenarios, f, indent=2)
    
    print("✓ Generated test datasets in tests/data/:")
    print("  - edge_cases.json (5 edge cases)")
    print("  - stress.json (3 stress tests)")
    print("  - scenarios.json (3 realistic scenarios)")
    
    return edge_cases, stress_tests, scenarios


if __name__ == "__main__":
    generate_all_test_datasets()
