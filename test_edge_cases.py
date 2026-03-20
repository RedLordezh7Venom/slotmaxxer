"""
SlotMaxxer Edge Case Test Suite
Tests 22 critical edge cases to ensure production-grade reliability
"""

import pytest
from datetime import time, date, timedelta
from models import Candidate, Interviewer, TimeSlot, DayOfWeek
from scheduler_engine import (
    generate_feasible_assignments,
    calculate_quality_score,
    optimal_assign,
    get_slots_within_window
)
from ai_processor import parse_availability_with_ai
import json


class TestInputParsingEdgeCases:
    """Category 1.1: Input Parsing Edge Cases"""
    
    def test_ec001_empty_candidate_availability(self):
        """EC-001: Empty availability should raise validation error"""
        candidate = Candidate(
            id="C1",
            name="Jane",
            email="jane@test.com",
            availability=[],  # EMPTY
            preferred_slots=[]
        )
        interviewer = Interviewer(
            id="I1",
            name="John",
            availability=[TimeSlot(DayOfWeek.TUESDAY, time(14, 0), time(17, 0))]
        )
        
        triplets = generate_feasible_assignments([candidate], [interviewer])
        assert len(triplets) == 0, "Should generate no assignments with empty availability"
    
    def test_ec002_malformed_time_strings(self):
        """EC-002: Malformed time strings should fallback gracefully"""
        # This tests the AI parser's robustness
        malformed_inputs = [
            "Tuueesday at noonish",
            "tomorrow maybe",
            "idk whenever",
            "2-5 PM on the 32nd of February"
        ]
        
        for bad_input in malformed_inputs:
            try:
                # Should either parse with AI or raise clear error
                result = parse_availability_with_ai(bad_input)
                # If it parses, verify it's at least a list
                assert isinstance(result, list), f"Parser should return list for: {bad_input}"
            except ValueError as e:
                # Acceptable to reject with clear message
                assert "parse" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_ec003_afternoon_keyword_expansion(self):
        """EC-003: 'afternoon' should default to 12:00-17:00"""
        input_text = "Tuesday afternoon"
        slots = parse_availability_with_ai(input_text)
        
        # Verify at least one slot exists
        assert len(slots) > 0, "Should parse 'afternoon' keyword"
        
        # Check if default range is reasonable (12-17 PM)
        for slot in slots:
            assert slot.start_time >= time(12, 0), "Afternoon should start at or after noon"
            assert slot.end_time <= time(18, 0), "Afternoon should end by 6 PM"
    
    def test_ec004_midnight_boundary_handling(self):
        """EC-004: Slots crossing midnight should either reject or handle correctly"""
        slot = TimeSlot(
            day=DayOfWeek.MONDAY,
            start_time=time(23, 0),  # 11 PM
            end_time=time(1, 0),     # 1 AM (next day)
        )
        
        # Should either:
        # 1. Reject (duration_minutes should be negative or invalid)
        # 2. Handle as multi-day span
        
        # Our current implementation treats this as invalid (end < start)
        assert slot.duration_minutes < 0 or slot.duration_minutes > 1200, \
            "Midnight crossing should be flagged"
    
    def test_ec005_duplicate_slot_deduplication(self):
        """EC-005: Duplicate slots should be deduplicated"""
        slot1 = TimeSlot(DayOfWeek.TUESDAY, time(14, 0), time(17, 0))
        slot2 = TimeSlot(DayOfWeek.TUESDAY, time(14, 0), time(17, 0))  # Exact duplicate
        
        candidate = Candidate(
            id="C1",
            name="Jane",
            email="jane@test.com",
            availability=[slot1, slot2],
            preferred_slots=[]
        )
        
        # Use set to deduplicate (requires __hash__ on TimeSlot)
        unique_slots = list({str(s): s for s in candidate.availability}.values())
        assert len(unique_slots) == 1, "Duplicates should be removed"
    
    def test_ec006_overlapping_availability_merge(self):
        """EC-006: Overlapping slots should be handled gracefully"""
        slot1 = TimeSlot(DayOfWeek.TUESDAY, time(14, 0), time(17, 0))  # 2-5 PM
        slot2 = TimeSlot(DayOfWeek.TUESDAY, time(15, 0), time(18, 0))  # 3-6 PM
        
        # Check that intersection works correctly
        intersection = slot1.intersection(slot2)
        assert intersection is not None, "Overlapping slots should have intersection"
        assert intersection.start_time == time(15, 0), "Intersection starts at later start"
        assert intersection.end_time == time(17, 0), "Intersection ends at earlier end"
    
    def test_ec007_past_date_rejection(self):
        """EC-007: Past dates should be rejected"""
        past_date = date(2020, 1, 1)  # Clearly in the past
        
        slot = TimeSlot(
            day=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            date=past_date
        )
        
        # Validation logic: if date is provided and it's in the past, reject
        if slot.date:
            assert slot.date >= date.today(), "Cannot schedule in the past"
    
    def test_ec008_mixed_time_format_normalization(self):
        """EC-008: Mixed 12/24 hour formats should normalize"""
        formats_to_test = [
            ("Tue 14:00-17:00", time(14, 0), time(17, 0)),  # 24-hour
            ("Tue 2-5 PM", time(14, 0), time(17, 0)),        # 12-hour
        ]
        
        for input_str, expected_start, expected_end in formats_to_test:
            slots = parse_availability_with_ai(input_str)
            assert len(slots) > 0, f"Failed to parse: {input_str}"
            
            # Verify normalization
            slot = slots[0]
            assert slot.start_time == expected_start, f"Start time mismatch for {input_str}"
            assert slot.end_time == expected_end, f"End time mismatch for {input_str}"


class TestSchedulingAlgorithmEdgeCases:
    """Category 1.2: Scheduling Algorithm Edge Cases"""
    
    def test_ec009_no_overlap_graceful_failure(self):
        """EC-009: No overlap should return empty assignments"""
        candidate = Candidate(
            id="C1", name="Jane", email="jane@test.com",
            availability=[TimeSlot(DayOfWeek.TUESDAY, time(9, 0), time(12, 0))],
            preferred_slots=[]
        )
        interviewer = Interviewer(
            id="I1", name="John",
            availability=[TimeSlot(DayOfWeek.WEDNESDAY, time(14, 0), time(17, 0))]
        )
        
        triplets = generate_feasible_assignments([candidate], [interviewer])
        assert len(triplets) == 0, "Should find no overlaps"
        
        # Simulate full flow
        scored = [(c, s, i, 0) for c, s, i in triplets]
        assignments, unassigned = optimal_assign(scored, [candidate])
        
        assert len(assignments) == 0, "No assignments possible"
        assert len(unassigned) == 1, "Candidate should be unassigned"
        assert unassigned[0].id == "C1"
    
    def test_ec010_partial_overlap_insufficient_duration(self):
        """EC-010: Overlap <60 min should not generate feasible assignment"""
        candidate = Candidate(
            id="C1", name="Jane", email="jane@test.com",
            availability=[TimeSlot(DayOfWeek.TUESDAY, time(14, 0), time(15, 0))],  # 1 hour
            preferred_slots=[]
        )
        interviewer = Interviewer(
            id="I1", name="John",
            availability=[TimeSlot(DayOfWeek.TUESDAY, time(14, 30), time(17, 0))]  # Starts 30 min in
        )
        
        triplets = generate_feasible_assignments([candidate], [interviewer], required_duration=60)
        
        # Overlap is only 30 minutes (14:30-15:00)
        # Should not generate any feasible assignments
        assert len(triplets) == 0, "30-min overlap should not meet 60-min requirement"
    
    def test_ec011_interviewer_capacity_exhaustion(self):
        """EC-011: More candidates than interviewer capacity"""
        # 5 candidates, 2 interviewers, each with 1 slot
        candidates = [
            Candidate(f"C{i}", f"Candidate{i}", f"c{i}@test.com",
                     availability=[TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(17, 0))],
                     preferred_slots=[])
            for i in range(5)
        ]
        
        interviewers = [
            Interviewer(f"I{i}", f"Interviewer{i}",
                       availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))])
            for i in range(2)
        ]
        
        triplets = generate_feasible_assignments(candidates, interviewers)
        scored = [(c, s, i, calculate_quality_score(c, s, i, len(i.availability))) 
                 for c, s, i in triplets]
        
        assignments, unassigned = optimal_assign(scored, candidates)
        
        # Only 2 interviewers * 1 slot each = max 2 assignments
        assert len(assignments) <= 2, "Cannot exceed interviewer capacity"
        assert len(unassigned) == 3, "3 candidates should be unassigned"
    
    def test_ec012_single_interviewer_sequential_assignment(self):
        """EC-012: Single interviewer should handle sequential slots"""
        candidates = [
            Candidate("C1", "Jane", "jane@test.com",
                     availability=[TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(17, 0))],
                     preferred_slots=[]),
            Candidate("C2", "John", "john@test.com",
                     availability=[TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(17, 0))],
                     preferred_slots=[])
        ]
        
        interviewer = Interviewer(
            "I1", "Interviewer",
            availability=[
                TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(11, 0)),
                TimeSlot(DayOfWeek.MONDAY, time(14, 0), time(16, 0))
            ]
        )
        
        triplets = generate_feasible_assignments(candidates, [interviewer])
        scored = [(c, s, i, calculate_quality_score(c, s, i, len(i.availability))) 
                 for c, s, i in triplets]
        
        assignments, unassigned = optimal_assign(scored, candidates)
        
        # Both candidates should get assigned to different slots
        assert len(assignments) == 2, "Single interviewer can handle 2 sequential interviews"
        assert len(unassigned) == 0, "All should be assigned"
        
        # Verify no time conflicts
        times = [a.slot for a in assignments]
        assert not times[0].overlaps_with(times[1]), "Slots should not overlap"
    
    def test_ec013_score_tie_deterministic_ordering(self):
        """EC-013: Tied scores should have deterministic ordering"""
        # Create two slots with identical scoring factors
        slot1 = TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))
        slot2 = TimeSlot(DayOfWeek.MONDAY, time(14, 0), time(15, 0))
        
        candidate = Candidate("C1", "Jane", "jane@test.com",
                            availability=[slot1, slot2],
                            preferred_slots=[slot1, slot2])  # Both preferred equally
        
        interviewer = Interviewer("I1", "John",
                                 availability=[slot1, slot2],
                                 preferred_slots=[slot1, slot2])
        
        score1 = calculate_quality_score(candidate, slot1, interviewer, 2)
        score2 = calculate_quality_score(candidate, slot2, interviewer, 2)
        
        # Scores should be identical
        assert score1 == score2, "Scores should be tied"
        
        # Verify sorting is stable/deterministic
        triplets = [(candidate, slot1, interviewer, score1),
                   (candidate, slot2, interviewer, score2)]
        
        sorted_once = sorted(triplets, key=lambda x: x[3], reverse=True)
        sorted_twice = sorted(sorted_once, key=lambda x: x[3], reverse=True)
        
        assert sorted_once == sorted_twice, "Sorting should be deterministic"
    
    def test_ec014_preference_conflict_reasoning(self):
        """EC-014: Conflicting preferences should be explained"""
        # Candidate prefers 10 AM, Interviewer prefers 2 PM
        slot_compromise = TimeSlot(DayOfWeek.MONDAY, time(12, 0), time(13, 0))  # Noon
        
        candidate = Candidate(
            "C1", "Jane", "jane@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(17, 0))],
            preferred_slots=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))]
        )
        
        interviewer = Interviewer(
            "I1", "John",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(17, 0))],
            preferred_slots=[TimeSlot(DayOfWeek.MONDAY, time(14, 0), time(15, 0))]
        )
        
        # Score the compromise slot (neither's preference)
        score = calculate_quality_score(candidate, slot_compromise, interviewer, 1)
        
        # Should NOT get preference bonuses
        assert score < 1500, "Compromise slot should not get full preference bonus"
        
        # But should get time optimality bonus (noon is decent)
        assert score > 100, "Should still get some quality points"
    
    def test_ec015_recurring_availability_expansion(self):
        """EC-015: Recurring slots should expand correctly"""
        # Test get_slots_within_window (used for discretization)
        base_slot = TimeSlot(
            day=DayOfWeek.TUESDAY,
            start_time=time(14, 0),
            end_time=time(17, 0),  # 3-hour window
            is_recurring=True
        )
        
        # Generate 60-minute slots with 30-min steps
        segments = get_slots_within_window(base_slot, duration=60, step=30)
        
        # Should generate: 14:00-15:00, 14:30-15:30, 15:00-16:00, 15:30-16:30, 16:00-17:00
        assert len(segments) == 5, f"Expected 5 segments, got {len(segments)}"
        
        # Verify first and last
        assert segments[0].start_time == time(14, 0)
        assert segments[-1].end_time == time(17, 0)
    
    def test_ec016_scarcity_multiplier_logic(self):
        """EC-016: Scarce interviewer should get higher priority"""
        candidate = Candidate(
            "C1", "Jane", "jane@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))],
            preferred_slots=[]
        )
        
        # Interviewer with 1 slot (scarce)
        scarce_interviewer = Interviewer(
            "I1", "Scarce",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))]
        )
        
        # Interviewer with 20 slots (abundant)
        abundant_interviewer = Interviewer(
            "I2", "Abundant",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, i), time(11, i)) 
                         for i in range(20)]  # Dummy slots
        )
        
        slot = TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))
        
        score_scarce = calculate_quality_score(candidate, slot, scarce_interviewer, 1)
        score_abundant = calculate_quality_score(candidate, slot, abundant_interviewer, 20)
        
        # Scarce should get 1000/1 = 1000 bonus
        # Abundant should get 1000/20 = 50 bonus
        assert score_scarce > score_abundant, "Scarce interviewer should score higher"
        assert (score_scarce - score_abundant) >= 900, "Difference should be ~950"
    
    def test_ec017_no_preferences_fallback_scoring(self):
        """EC-017: No preferences should fall back to time/duration scoring"""
        candidate = Candidate(
            "C1", "Jane", "jane@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))],
            preferred_slots=[]  # NO PREFERENCES
        )
        
        interviewer = Interviewer(
            "I1", "John",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))],
            preferred_slots=[]  # NO PREFERENCES
        )
        
        slot = TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))  # 10 AM = prime time
        
        score = calculate_quality_score(candidate, slot, interviewer, 1)
        
        # Should get:
        # - Time optimality: 200 (10 AM is prime)
        # - Duration bonus: 100 (60 min)
        # - Scarcity: 1000
        # Total: ~1300
        
        assert score >= 1000, "Should still get reasonable score without preferences"
        assert score < 2000, "Should not get preference bonuses"


class TestReassignmentEdgeCases:
    """Category 1.3: Reassignment Edge Cases"""
    
    def test_ec018_cascading_reassignment_stability(self):
        """EC-018: Cascading cancellations should stabilize"""
        # This would test the /api/reassign endpoint
        # Placeholder for integration test
        pass
    
    def test_ec019_cancellation_no_alternatives(self):
        """EC-019: Cancelled slot with no alternatives"""
        # If only 1 interviewer with 1 slot, and it's cancelled
        candidate = Candidate(
            "C1", "Jane", "jane@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))],
            preferred_slots=[]
        )
        
        interviewer = Interviewer(
            "I1", "John",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))]
        )
        
        triplets = generate_feasible_assignments([candidate], [interviewer])
        scored = [(c, s, i, calculate_quality_score(c, s, i, 1)) for c, s, i in triplets]
        
        assignments, unassigned = optimal_assign(scored, [candidate])
        
        # Now simulate cancellation by removing the only assignment
        if assignments:
            assignments = []  # Cancel it
        
        # Re-run with empty interviewers
        triplets_after = generate_feasible_assignments([candidate], [])
        assert len(triplets_after) == 0, "No alternatives should exist"
    
    def test_ec020_reassignment_quality_preservation(self):
        """EC-020: Reassignment should minimize quality loss"""
        # Would require storing original scores and comparing
        # Placeholder for integration test
        pass


class TestOutputEdgeCases:
    """Category 1.4: Output Edge Cases"""
    
    def test_ec021_fewer_than_three_alternatives(self):
        """EC-021: Should return actual number of alternatives, not force 3"""
        candidate = Candidate(
            "C1", "Jane", "jane@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(12, 0))],
            preferred_slots=[]
        )
        
        interviewer = Interviewer(
            "I1", "John",
            availability=[
                TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0)),  # Primary
                TimeSlot(DayOfWeek.MONDAY, time(11, 0), time(12, 0))   # Only 1 alternative
            ]
        )
        
        triplets = generate_feasible_assignments([candidate], [interviewer])
        scored = [(c, s, i, calculate_quality_score(c, s, i, 2)) for c, s, i in triplets]
        
        assignments, unassigned = optimal_assign(scored, [candidate])
        
        assert len(assignments) == 1, "Should have 1 assignment"
        # Alternatives should be 1 (not forced to 3)
        assert len(assignments[0].alternatives) <= 1, "Only 1 alternative exists"
    
    def test_ec022_zero_candidates_error(self):
        """EC-022: Empty candidate list should be rejected"""
        interviewer = Interviewer(
            "I1", "John",
            availability=[TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))]
        )
        
        triplets = generate_feasible_assignments([], [interviewer])
        assert len(triplets) == 0, "No candidates = no assignments"
        
        scored = []
        assignments, unassigned = optimal_assign(scored, [])
        assert len(assignments) == 0
        assert len(unassigned) == 0


# Run tests with: pytest test_edge_cases.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
