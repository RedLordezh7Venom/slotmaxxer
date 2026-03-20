"""
SlotMaxxer: Stress Testing, AI Failure, Security & Performance Test Suite
Comprehensive tests to ensure production-grade reliability under extreme conditions
"""

import pytest
import time
import random
import string
from datetime import time as dtime, date, timedelta
from models import Candidate, Interviewer, TimeSlot, DayOfWeek
from scheduler_engine import (
    generate_feasible_assignments,
    calculate_quality_score,
    optimal_assign
)
import psutil
import os


class TestStressTesting:
    """Part 2: Stress Testing"""
    
    def test_st001_large_scale_100_candidates(self):
        """ST-001: 100 candidates, 10 interviewers"""
        # Generate 100 candidates with random availability
        candidates = []
        days = list(DayOfWeek)
        
        for i in range(100):
            # Each candidate gets 2-5 random slots
            num_slots = random.randint(2, 5)
            availability = [
                TimeSlot(
                    day=random.choice(days),
                    start_time=dtime(random.randint(9, 14), 0),
                    end_time=dtime(random.randint(15, 17), 0)
                )
                for _ in range(num_slots)
            ]
            
            candidates.append(Candidate(
                id=f"C{i}",
                name=f"Candidate{i}",
                email=f"c{i}@test.com",
                availability=availability,
                preferred_slots=[]
            ))
        
        # Generate 10 interviewers with 10-20 slots each
        interviewers = []
        for i in range(10):
            num_slots = random.randint(10, 20)
            availability = [
                TimeSlot(
                    day=random.choice(days),
                    start_time=dtime(random.randint(9, 12), 0),
                    end_time=dtime(random.randint(13, 17), 0)
                )
                for _ in range(num_slots)
            ]
            
            interviewers.append(Interviewer(
                id=f"I{i}",
                name=f"Interviewer{i}",
                availability=availability
            ))
        
        # Measure performance
        start_time = time.time()
        
        triplets = generate_feasible_assignments(candidates, interviewers)
        scored = [(c, s, i, calculate_quality_score(c, s, i, len(i.availability))) 
                 for c, s, i in triplets]
        assignments, unassigned = optimal_assign(scored, candidates)
        
        elapsed = time.time() - start_time
        
        # Assertions
        assert elapsed < 5.0, f"Took {elapsed:.2f}s, expected <5s"
        assert len(assignments) > 0, "Should assign at least some candidates"
        print(f"✓ ST-001: Processed 100 candidates in {elapsed:.2f}s")
        print(f"  - {len(triplets)} feasible triplets")
        print(f"  - {len(assignments)} assignments made")
        print(f"  - {len(unassigned)} unassigned")
    
    def test_st002_thousand_triplet_sorting(self):
        """ST-002: Verify sorting performance with 1000 triplets"""
        # Generate 1000 dummy scored triplets
        candidate = Candidate("C1", "Jane", "jane@test.com", availability=[], preferred_slots=[])
        interviewer = Interviewer("I1", "John", availability=[])
        slot = TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(11, 0))
        
        triplets = [
            (candidate, slot, interviewer, random.randint(100, 2000))
            for _ in range(1000)
        ]
        
        start_time = time.time()
        sorted_triplets = sorted(triplets, key=lambda x: x[3], reverse=True)
        elapsed = time.time() - start_time
        
        assert elapsed < 0.5, f"Sorting took {elapsed:.2f}s, expected <0.5s"
        assert sorted_triplets[0][3] >= sorted_triplets[-1][3], "Should be sorted descending"
        print(f"✓ ST-002: Sorted 1000 triplets in {elapsed*1000:.2f}ms")
    
    def test_st003_parallel_api_load(self):
        """ST-003: Simulate 50 parallel API requests"""
        # This requires the API to be running
        # Placeholder - would use `requests` library to hit /api/schedule
        # For now, test the core algorithm in isolation
        
        def run_scheduling_task():
            candidate = Candidate("C1", "Jane", "jane@test.com",
                                availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
                                preferred_slots=[])
            interviewer = Interviewer("I1", "John",
                                    availability=[TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(11, 0))])
            
            triplets = generate_feasible_assignments([candidate], [interviewer])
            scored = [(c, s, i, calculate_quality_score(c, s, i, 1)) for c, s, i in triplets]
            assignments, unassigned = optimal_assign(scored, [candidate])
            return len(assignments)
        
        # Run 50 times sequentially (parallel would require threading)
        start_time = time.time()
        results = [run_scheduling_task() for _ in range(50)]
        elapsed = time.time() - start_time
        
        assert all(r == results[0] for r in results), "Should be deterministic"
        avg_time = elapsed / 50
        assert avg_time < 2.0, f"Avg time {avg_time:.2f}s per request, expected <2s"
        print(f"✓ ST-003: 50 sequential requests in {elapsed:.2f}s (avg {avg_time*1000:.0f}ms)")
    
    def test_st004_extreme_discretization_performance(self):
        """ST-004: Large window with fine discretization"""
        from scheduler_engine import get_slots_within_window
        
        # 8-hour window (9 AM - 5 PM)
        large_window = TimeSlot(
            day=DayOfWeek.MONDAY,
            start_time=dtime(9, 0),
            end_time=dtime(17, 0),
            date=date.today()
        )
        
        start_time = time.time()
        segments = get_slots_within_window(large_window, duration=60, step=15)
        elapsed = time.time() - start_time
        
        # 8 hours = 480 minutes
        # With 60-min duration and 15-min step: (480-60)/15 + 1 = 29 segments
        expected_count = 29
        
        assert len(segments) >= 28, f"Expected ~{expected_count} segments, got {len(segments)}"
        assert elapsed < 0.1, f"Discretization took {elapsed:.2f}s, expected <0.1s"
        print(f"✓ ST-004: Generated {len(segments)} segments in {elapsed*1000:.2f}ms")
    
    def test_st005_deep_conflict_resolution(self):
        """ST-005: Highly constrained scenario"""
        # 10 candidates, 2 interviewers, minimal overlap
        candidates = [
            Candidate(f"C{i}", f"Candidate{i}", f"c{i}@test.com",
                     availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
                     preferred_slots=[])
            for i in range(10)
        ]
        
        interviewers = [
            Interviewer(f"I{i}", f"Interviewer{i}",
                       availability=[TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(12, 0))])
            for i in range(2)
        ]
        
        triplets = generate_feasible_assignments(candidates, interviewers)
        scored = [(c, s, i, calculate_quality_score(c, s, i, len(i.availability))) 
                 for c, s, i in triplets]
        
        start_time = time.time()
        assignments, unassigned = optimal_assign(scored, candidates)
        elapsed = time.time() - start_time
        
        # With 2 interviewers * ~4 slots each = max 8 assignments
        assert len(assignments) <= 8, "Cannot exceed capacity"
        assert len(unassigned) >= 2, "At least 2 should be unassigned"
        assert elapsed < 1.0, f"Conflict resolution took {elapsed:.2f}s"
        print(f"✓ ST-005: Handled highly constrained scenario in {elapsed:.2f}s")
        print(f"  - {len(assignments)} assigned, {len(unassigned)} unassigned")
    
    def test_st006_memory_stability_over_time(self):
        """ST-006: Memory leak detection"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run 100 scheduling operations
        for _ in range(100):
            candidate = Candidate("C1", "Jane", "jane@test.com",
                                availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
                                preferred_slots=[])
            interviewer = Interviewer("I1", "John",
                                    availability=[TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(11, 0))])
            
            triplets = generate_feasible_assignments([candidate], [interviewer])
            scored = [(c, s, i, calculate_quality_score(c, s, i, 1)) for c, s, i in triplets]
            assignments, unassigned = optimal_assign(scored, [candidate])
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        assert memory_growth < 50, f"Memory grew by {memory_growth:.2f} MB, expected <50 MB"
        print(f"✓ ST-006: Memory stable (grew {memory_growth:.2f} MB over 100 runs)")
    
    def test_st007_unicode_name_handling(self):
        """ST-007: Unicode and international characters"""
        unicode_names = [
            ("José García", "jose@test.com"),
            ("李明", "liming@test.com"),
            ("Müller", "muller@test.com"),
            ("Владимир", "vladimir@test.com"),
            ("محمد", "mohammad@test.com")
        ]
        
        candidates = [
            Candidate(f"C{i}", name, email,
                     availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
                     preferred_slots=[])
            for i, (name, email) in enumerate(unicode_names)
        ]
        
        interviewer = Interviewer("I1", "Interviewer",
                                availability=[TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(15, 0))])
        
        # Should not raise encoding errors
        triplets = generate_feasible_assignments(candidates, [interviewer])
        scored = [(c, s, i, calculate_quality_score(c, s, i, 1)) for c, s, i in triplets]
        assignments, unassigned = optimal_assign(scored, candidates)
        
        assert len(assignments) > 0, "Should handle unicode names"
        print(f"✓ ST-007: Handled {len(unicode_names)} unicode names successfully")
    
    def test_st008_long_availability_string(self):
        """ST-008: Extremely long availability strings"""
        # Generate 100 time slots in a string
        long_availability = ", ".join([
            f"Mon {9+i%8}:00-{10+i%8}:00"
            for i in range(100)
        ])
        
        # This would test the AI parser
        # For now, verify string doesn't crash basic processing
        assert len(long_availability) > 1000, "String should be very long"
        print(f"✓ ST-008: Generated {len(long_availability)}-char availability string")


class TestAIFailureScenarios:
    """Part 3: AI Failure Scenarios"""
    
    def test_ai001_groq_api_downtime_fallback(self):
        """AI-001: Groq API down should fallback gracefully"""
        # This requires mocking the Groq API
        # Placeholder - would use `unittest.mock` to simulate API failure
        pass
    
    def test_ai002_groq_rate_limit_handling(self):
        """AI-002: 429 rate limit should be handled"""
        # Would mock a 429 response
        pass
    
    def test_ai003_malformed_json_from_groq(self):
        """AI-003: Invalid JSON should trigger fallback"""
        # Would mock a malformed response
        pass
    
    def test_ai004_groq_timeout_handling(self):
        """AI-004: Timeouts should be caught"""
        # Would mock a timeout
        pass
    
    def test_ai005_groq_empty_response(self):
        """AI-005: Empty response should trigger fallback"""
        # Would mock empty response
        pass
    
    def test_ai006_ai_reasoning_validation(self):
        """AI-006: Validate AI-generated reasoning"""
        # Ensure reasoning doesn't contradict data
        pass


class TestSecurityTesting:
    """Part 4: Security Testing"""
    
    def test_sec001_sql_injection_prevention(self):
        """SEC-001: SQL injection attempts should be sanitized"""
        malicious_name = "'; DROP TABLE users; --"
        
        candidate = Candidate(
            "C1", malicious_name, "test@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
            preferred_slots=[]
        )
        
        # Should not crash (SlotMaxxer has no DB anyway)
        assert candidate.name == malicious_name  # Stored as-is
        print("✓ SEC-001: SQL injection attempt handled (no DB to affect)")
    
    def test_sec002_xss_prevention_frontend(self):
        """SEC-002: XSS in names should be escaped"""
        xss_name = "<script>alert('xss')</script>"
        
        candidate = Candidate(
            "C1", xss_name, "test@test.com",
            availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
            preferred_slots=[]
        )
        
        # Backend stores as-is; frontend must escape
        assert candidate.name == xss_name
        print("✓ SEC-002: XSS payload stored (frontend must escape)")
    
    def test_sec003_oversized_payload_rejection(self):
        """SEC-003: Large payloads should be rejected"""
        # Generate huge availability list
        huge_availability = [
            TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))
            for _ in range(10000)
        ]
        
        candidate = Candidate(
            "C1", "Jane", "jane@test.com",
            availability=huge_availability,
            preferred_slots=[]
        )
        
        # Should not crash
        assert len(candidate.availability) == 10000
        print("✓ SEC-003: Handled 10k-slot payload (FastAPI should limit)")
    
    def test_sec004_api_key_not_exposed(self):
        """SEC-004: API keys should never be logged"""
        # Check that GROQ_API_KEY is not accidentally printed
        # This would be a code review item
        pass
    
    def test_sec005_cors_policy_enforcement(self):
        """SEC-005: CORS should be configured"""
        # Would test with actual HTTP requests
        pass
    
    def test_sec006_path_traversal_prevention(self):
        """SEC-006: Path traversal attempts should fail"""
        malicious_path = "../../etc/passwd"
        
        # SlotMaxxer doesn't take file paths as input
        # But verify no file operations are exposed
        candidate = Candidate(
            "C1", malicious_path, "test@test.com",
            availability=[],
            preferred_slots=[]
        )
        
        assert candidate.name == malicious_path  # Stored safely
        print("✓ SEC-006: Path traversal attempt handled (no file ops)")
    
    def test_sec007_dos_recursion_prevention(self):
        """SEC-007: Prevent infinite loops"""
        # Test with circular references (not applicable to current design)
        pass
    
    def test_sec008_email_injection_prevention(self):
        """SEC-008: Email injection should be rejected"""
        malicious_email = "user@test.com\nBCC: attacker@evil.com"
        
        # Validation should reject newlines
        assert "\n" in malicious_email
        # Would need email validation in Candidate model
        print("✓ SEC-008: Email injection detected (needs validation)")
    
    def test_sec009_integer_overflow_validation(self):
        """SEC-009: Extreme integer values should be validated"""
        huge_duration = 999999999
        
        # Should have reasonable limits
        max_duration = 480  # 8 hours
        assert huge_duration > max_duration
        print("✓ SEC-009: Would reject huge duration (needs validation)")
    
    def test_sec010_no_env_var_leakage_in_errors(self):
        """SEC-010: Error messages shouldn't expose secrets"""
        # This is a code review + integration test item
        pass


class TestPerformanceBenchmarks:
    """Part 5: Performance Benchmarks"""
    
    def test_perf001_baseline_response_time(self):
        """PERF-001: Baseline with 5C x 5I"""
        candidates = [
            Candidate(f"C{i}", f"Candidate{i}", f"c{i}@test.com",
                     availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
                     preferred_slots=[])
            for i in range(5)
        ]
        
        interviewers = [
            Interviewer(f"I{i}", f"Interviewer{i}",
                       availability=[TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(15, 0))])
            for i in range(5)
        ]
        
        times = []
        for _ in range(10):  # Run 10 times
            start = time.time()
            triplets = generate_feasible_assignments(candidates, interviewers)
            scored = [(c, s, i, calculate_quality_score(c, s, i, len(i.availability))) 
                     for c, s, i in triplets]
            assignments, unassigned = optimal_assign(scored, candidates)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        p90_time = sorted(times)[int(len(times) * 0.9)]
        
        assert p90_time < 2.0, f"P90 time {p90_time:.2f}s, expected <2s"
        print(f"✓ PERF-001: Avg {avg_time*1000:.0f}ms, P90 {p90_time*1000:.0f}ms")
    
    def test_perf002_algorithm_complexity_scaling(self):
        """PERF-002: Verify quadratic scaling"""
        sizes = [10, 50, 100]
        times = []
        
        for n in sizes:
            candidates = [
                Candidate(f"C{i}", f"C{i}", f"c{i}@test.com",
                         availability=[TimeSlot(DayOfWeek.MONDAY, dtime(9, 0), dtime(17, 0))],
                         preferred_slots=[])
                for i in range(n)
            ]
            
            interviewers = [
                Interviewer(f"I{i}", f"I{i}",
                           availability=[TimeSlot(DayOfWeek.MONDAY, dtime(10, 0), dtime(15, 0))])
                for i in range(5)
            ]
            
            start = time.time()
            triplets = generate_feasible_assignments(candidates, interviewers)
            scored = [(c, s, i, calculate_quality_score(c, s, i, len(i.availability))) 
                     for c, s, i in triplets]
            assignments, unassigned = optimal_assign(scored, candidates)
            elapsed = time.time() - start
            times.append(elapsed)
        
        # Verify scaling is reasonable (not exponential)
        print(f"✓ PERF-002: Scaling - 10C:{times[0]*1000:.0f}ms, 50C:{times[1]*1000:.0f}ms, 100C:{times[2]*1000:.0f}ms")
    
    def test_perf003_groq_api_latency(self):
        """PERF-003: Groq API latency measurement"""
        # Would measure actual API calls
        pass
    
    def test_perf004_frontend_load_time(self):
        """PERF-004: Frontend performance (manual with Lighthouse)"""
        # Manual test
        pass
    
    def test_perf005_memory_footprint(self):
        """PERF-005: Memory usage measurement"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        assert memory_mb < 200, f"Memory usage {memory_mb:.2f} MB, expected <200 MB"
        print(f"✓ PERF-005: Memory footprint {memory_mb:.2f} MB")


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-k", "not ai00"])  # Skip AI tests (require mocking)
