# SlotMaxxer: Comprehensive Testing & Hardening Plan

## Executive Summary

This document outlines a production-grade testing strategy for SlotMaxxer covering:
- **Edge Case Testing** (20+ scenarios)
- **Stress Testing** (100+ candidates, API load)
- **AI Failure Scenarios** (Groq downtime, malformed responses)
- **Security Review** (input validation, API abuse)
- **Performance Benchmarks** (sub-2s guarantee)
- **User Acceptance Testing** (real-world scenarios)

**Goal:** Ensure SlotMaxxer handles every scenario gracefully, never crashes, and maintains sub-2s response times.

---

## Test Matrix Overview

| Category | # Tests | Priority | Estimated Time |
|----------|---------|----------|----------------|
| Edge Cases | 22 | P0 | 2 hours |
| Stress Tests | 8 | P0 | 1 hour |
| AI Failures | 6 | P0 | 45 min |
| Security | 10 | P1 | 1 hour |
| Performance | 5 | P0 | 30 min |
| UAT | 4 | P1 | 45 min |
| **TOTAL** | **55** | - | **~6 hours** |

---

# Part 1: Edge Case Testing

## Category 1.1: Input Parsing Edge Cases

### EC-001: Empty Availability
**Scenario:** Candidate provides no availability  
**Input:**
```json
{
  "candidates": [{"name": "Jane", "availability": ""}],
  "interviewers": [{"name": "John", "availability": "Tue 2-5 PM"}]
}
```
**Expected:** Error 422 with message: "Candidate 'Jane' has no valid availability"  
**Test:** `test_empty_candidate_availability()`

---

### EC-002: Malformed Time Strings
**Scenario:** Invalid time format  
**Input:** `"availability": "Tuueesday at noonish"`  
**Expected:** Groq AI parses gracefully OR fallback parser rejects with clear error  
**Test:** `test_malformed_time_strings()`

---

### EC-003: Ambiguous "Afternoon"
**Scenario:** User writes "Tuesday afternoon" without specific times  
**Input:** `"Tue afternoon"`  
**Expected:** Defaults to 12:00-17:00 (document this assumption)  
**Test:** `test_afternoon_keyword_expansion()`

---

### EC-004: Midnight Boundary
**Scenario:** Slot crosses midnight (11 PM - 1 AM)  
**Input:** `"Mon 11 PM - Tue 1 AM"`  
**Expected:** Either reject (business hours only) OR handle as 2-day span  
**Test:** `test_midnight_boundary_handling()`

---

### EC-005: Duplicate Time Slots
**Scenario:** Candidate lists same slot twice  
**Input:** `"Tue 2-5 PM, Tuesday 14:00-17:00"`  
**Expected:** Deduplicate silently  
**Test:** `test_duplicate_slot_deduplication()`

---

### EC-006: Overlapping Availability
**Scenario:** Candidate says "Tue 2-5 PM, Tue 3-6 PM"  
**Expected:** Merge into single window (2-6 PM) or keep both  
**Test:** `test_overlapping_availability_merge()`

---

### EC-007: Past Dates
**Scenario:** User enters "Monday Jan 1, 2024" (past date)  
**Expected:** Reject with error "Cannot schedule interviews in the past"  
**Test:** `test_past_date_rejection()`

---

### EC-008: 24-Hour Format Mix
**Scenario:** Mix of formats: "Tue 14:00-17:00 and Wed 2-5 PM"  
**Expected:** Normalize both to 24-hour internally  
**Test:** `test_mixed_time_format_normalization()`

---

## Category 1.2: Scheduling Algorithm Edge Cases

### EC-009: No Overlap At All
**Scenario:** Candidate free Tue, Interviewers free Wed  
**Expected:** Return empty assignments + AI suggests "nearest miss" alternatives  
**Test:** `test_no_overlap_graceful_failure()`

---

### EC-010: Partial Overlap (<60 min)
**Scenario:** Candidate 2-3 PM, Interviewer 2:30-5 PM (only 30 min overlap)  
**Expected:** Flag as insufficient duration, suggest extension or different slot  
**Test:** `test_partial_overlap_insufficient_duration()`

---

### EC-011: All Interviewers Busy
**Scenario:** 5 candidates, 3 interviewers, all interviewer slots taken by first 3  
**Expected:** Last 2 candidates marked "unassigned" with conflict resolution suggestions  
**Test:** `test_interviewer_capacity_exhaustion()`

---

### EC-012: Single Interviewer Mode
**Scenario:** Only 1 interviewer for 5 candidates  
**Expected:** Sequential assignment, alternatives suggest different times for same interviewer  
**Test:** `test_single_interviewer_sequential_assignment()`

---

### EC-013: Exact Tie in Scores
**Scenario:** Two slots have identical quality scores (e.g., both 1200 pts)  
**Expected:** Deterministic tie-breaker (prefer earlier time)  
**Test:** `test_score_tie_deterministic_ordering()`

---

### EC-014: Preference Conflict
**Scenario:** Candidate prefers 10 AM, Interviewer prefers 2 PM, overlap is 11 AM-1 PM  
**Expected:** Score reflects compromise, reasoning explains tradeoff  
**Test:** `test_preference_conflict_reasoning()`

---

### EC-015: Recurring Availability Expansion
**Scenario:** "Every Tuesday 2-5 PM" for next 4 weeks  
**Expected:** Generates 4 distinct TimeSlot instances with dates  
**Test:** `test_recurring_availability_expansion()`

---

### EC-016: Scarcity Edge Case
**Scenario:** Interviewer with only 1 slot available vs. interviewer with 20 slots  
**Expected:** Scarcity multiplier gives higher priority to rare interviewer  
**Test:** `test_scarcity_multiplier_logic()`

---

### EC-017: All Preferences Ignored
**Scenario:** No candidate/interviewer preferences provided (all slots equal)  
**Expected:** Falls back to time optimality + duration scoring  
**Test:** `test_no_preferences_fallback_scoring()`

---

## Category 1.3: Reassignment Edge Cases

### EC-018: Cascading Cancellations
**Scenario:** Interviewer cancels 3 PM slot, affects 2 candidates, re-assignment causes another conflict  
**Expected:** System re-runs algorithm, minimizes total disruption  
**Test:** `test_cascading_reassignment_stability()`

---

### EC-019: Cancellation With No Alternatives
**Scenario:** Interviewer's only slot cancelled, no other interviewers available  
**Expected:** Candidate marked unassigned with clear message  
**Test:** `test_cancellation_no_alternatives()`

---

### EC-020: Reassignment Preserves Quality
**Scenario:** After cancellation, ensure new assignments don't drastically reduce quality  
**Expected:** Quality degradation < 20% on average  
**Test:** `test_reassignment_quality_preservation()`

---

## Category 1.4: Output Edge Cases

### EC-021: Less Than 3 Alternatives
**Scenario:** Only 1 viable alternative exists for a candidate  
**Expected:** Return 1 alternative (not force 3)  
**Test:** `test_fewer_than_three_alternatives()`

---

### EC-022: Zero Candidates
**Scenario:** Empty candidate list submitted  
**Expected:** Error 422: "At least 1 candidate required"  
**Test:** `test_zero_candidates_error()`

---

# Part 2: Stress Testing

## ST-001: 100 Candidates, 10 Interviewers
**Goal:** Verify algorithm handles scale  
**Setup:**
- 100 candidates with random availability (2-5 slots each)
- 10 interviewers with random availability (10-20 slots each)
**Expected:** 
- Response time < 5 seconds
- All feasible candidates assigned
- No crashes or memory errors
**Test:** `test_large_scale_100_candidates()`

---

## ST-002: 1000 Feasible Assignments
**Goal:** Stress-test sorting algorithm  
**Setup:** Generate 1000 valid triplets (C, S, I)  
**Expected:** 
- Sorting completes in <500ms
- Optimal assignment in <1s
**Test:** `test_thousand_triplet_sorting()`

---

## ST-003: 50 Sequential API Requests
**Goal:** Test API stability under load  
**Setup:** Fire 50 `/api/schedule` requests in parallel  
**Expected:**
- All return 200 OK
- No degradation in response time (avg stays <2s)
- No memory leaks
**Test:** `test_parallel_api_load()`

---

## ST-004: Extreme Discretization
**Goal:** Test `get_slots_within_window()` with large windows  
**Setup:** 8-hour window (9 AM - 5 PM), 15-min step size  
**Expected:** 
- Generates 32 segments
- No infinite loops
- Completes in <100ms
**Test:** `test_extreme_discretization_performance()`

---

## ST-005: Deep Recursion in Conflict Resolution
**Goal:** Test AI reasoner with highly constrained scenarios  
**Setup:** 10 candidates, 2 interviewers, minimal overlap  
**Expected:**
- AI suggests valid solutions (split rounds, add time)
- No API timeout
**Test:** `test_deep_conflict_resolution()`

---

## ST-006: Memory Profiling
**Goal:** Ensure no memory leaks over time  
**Setup:** Run 100 scheduling requests sequentially  
**Expected:** Memory usage stable (<50 MB growth)  
**Test:** `test_memory_stability_over_time()`

---

## ST-007: Unicode & International Names
**Goal:** Test with non-ASCII characters  
**Setup:** Candidates named "José García", "李明", "Müller"  
**Expected:** All processed correctly, no encoding errors  
**Test:** `test_unicode_name_handling()`

---

## ST-008: Extremely Long Availability Strings
**Goal:** Test parser with 1000+ character inputs  
**Setup:** "Mon 9-10 AM, Mon 10-11 AM, Mon 11 AM-12 PM..." (100 slots)  
**Expected:** 
- Groq handles gracefully
- Fallback if token limit exceeded
**Test:** `test_long_availability_string()`

---

# Part 3: AI Failure Scenarios

## AI-001: Groq API Down
**Scenario:** Groq returns 503 Service Unavailable  
**Expected:** Fallback to rule-based parser, warning logged  
**Test:** `test_groq_api_downtime_fallback()`

---

## AI-002: Groq Rate Limit Hit
**Scenario:** 429 Too Many Requests  
**Expected:** Retry with exponential backoff OR immediate fallback  
**Test:** `test_groq_rate_limit_handling()`

---

## AI-003: Malformed JSON from Groq
**Scenario:** AI returns invalid JSON (missing bracket)  
**Expected:** Catch parsing error, fallback to rules  
**Test:** `test_groq_malformed_json_response()`

---

## AI-004: Groq Timeout (>5s)
**Scenario:** API call hangs  
**Expected:** Timeout after 5s, fallback  
**Test:** `test_groq_timeout_handling()`

---

## AI-005: Groq Returns Empty Response
**Scenario:** AI returns `{"slots": []}`  
**Expected:** Treat as parsing failure, use fallback  
**Test:** `test_groq_empty_response()`

---

## AI-006: Nonsensical AI Reasoning
**Scenario:** AI generates reasoning text with hallucinated details  
**Expected:** Validate reasoning doesn't contradict data, sanitize if needed  
**Test:** `test_ai_reasoning_validation()`

---

# Part 4: Security Testing

## SEC-001: SQL Injection Attempt
**Scenario:** Input: `"name": "'; DROP TABLE users; --"`  
**Expected:** Sanitized, no database access (SlotMaxxer has no DB anyway)  
**Test:** `test_sql_injection_prevention()`

---

## SEC-002: XSS in Candidate Names
**Scenario:** `"name": "<script>alert('xss')</script>"`  
**Expected:** Frontend escapes HTML, no script execution  
**Test:** `test_xss_prevention_frontend()`

---

## SEC-003: Oversized Payload
**Scenario:** 10 MB JSON payload  
**Expected:** FastAPI rejects with 413 Payload Too Large  
**Test:** `test_oversized_payload_rejection()`

---

## SEC-004: API Key Exposure
**Scenario:** Check if Groq API key appears in logs/responses  
**Expected:** Never logged or returned to client  
**Test:** `test_api_key_not_exposed()`

---

## SEC-005: CORS Bypass Attempt
**Scenario:** Request from malicious origin  
**Expected:** CORS policy blocks (if enabled) or open (document this)  
**Test:** `test_cors_policy_enforcement()`

---

## SEC-006: Path Traversal
**Scenario:** Input: `"../../etc/passwd"` in a field  
**Expected:** Rejected, no file system access  
**Test:** `test_path_traversal_prevention()`

---

## SEC-007: Denial of Service via Recursion
**Scenario:** Circular availability reference (if possible)  
**Expected:** Algorithm detects, prevents infinite loop  
**Test:** `test_dos_recursion_prevention()`

---

## SEC-008: Email Injection
**Scenario:** `"email": "user@test.com\nBCC: attacker@evil.com"`  
**Expected:** Email validation rejects newlines  
**Test:** `test_email_injection_prevention()`

---

## SEC-009: Integer Overflow
**Scenario:** `"interview_duration_minutes": 999999999`  
**Expected:** Validation caps at reasonable limit (e.g., 480 min)  
**Test:** `test_integer_overflow_validation()`

---

## SEC-010: Environment Variable Leakage
**Scenario:** Error messages shouldn't reveal .env contents  
**Expected:** Generic errors, no stack traces with secrets  
**Test:** `test_no_env_var_leakage_in_errors()`

---

# Part 5: Performance Benchmarks

## PERF-001: Baseline Response Time
**Goal:** Establish performance baseline  
**Setup:** 5 candidates, 5 interviewers, typical scenario  
**Target:** <2 seconds (90th percentile)  
**Test:** `test_baseline_response_time()`

---

## PERF-002: Algorithm Complexity Verification
**Goal:** Verify O(n²) complexity holds  
**Setup:** Test with 10, 50, 100 candidates  
**Expected:** Time grows quadratically, not exponentially  
**Test:** `test_algorithm_complexity_scaling()`

---

## PERF-003: Groq API Latency
**Goal:** Measure AI overhead  
**Setup:** 10 parsing requests  
**Expected:** Avg <1s per request  
**Test:** `test_groq_api_latency_measurement()`

---

## PERF-004: Frontend Load Time
**Goal:** Measure page load speed  
**Setup:** Lighthouse audit  
**Expected:** First Contentful Paint < 1.5s  
**Test:** `test_frontend_load_time()` (manual with Lighthouse)

---

## PERF-005: Memory Footprint
**Goal:** Measure RAM usage  
**Setup:** Typical scenario  
**Expected:** <100 MB total  
**Test:** `test_memory_footprint_measurement()`

---

# Part 6: User Acceptance Testing (UAT)

## UAT-001: Real Recruiter Workflow
**Scenario:** Recruiter schedules 3 candidates across 2 days  
**Steps:**
1. Input messy email copy-paste: "Sarah: Tue/Thu afternoons. Mike: Mon-Wed 9-12. Lisa: flexible"
2. Add 3 interviewers with varying availability
3. Review results
4. Cancel one slot, check reassignment

**Success Criteria:**
- Recruiter understands output without training
- Email templates ready to send
- Reassignment clear and actionable

---

## UAT-002: Edge Case - No Perfect Match
**Scenario:** Impossible constraints (e.g., candidate only free weekends)  
**Success Criteria:**
- System explains why no match exists
- Suggests actionable fixes (add availability, different interviewer)

---

## UAT-003: Mobile Experience
**Scenario:** Access SlotMaxxer on phone  
**Success Criteria:**
- Forms usable (no horizontal scroll)
- Results readable
- Copy-to-clipboard works

---

## UAT-004: Print Output
**Scenario:** Recruiter prints schedule for offline review  
**Success Criteria:**
- Print CSS hides unnecessary elements
- All key info visible
- Formatting preserved

---

# Test Execution Strategy

## Phase 1: Automated Unit Tests (2 hours)
Run all EC-* tests with pytest:
```bash
pytest tests/test_edge_cases.py -v
```

## Phase 2: Stress Tests (1 hour)
Run ST-* tests separately (longer execution):
```bash
pytest tests/test_stress.py -v --timeout=300
```

## Phase 3: AI Failure Simulation (45 min)
Mock Groq API responses:
```bash
pytest tests/test_ai_failures.py -v
```

## Phase 4: Security Audit (1 hour)
Manual + automated checks:
```bash
pytest tests/test_security.py -v
bandit -r . -ll  # Static analysis
```

## Phase 5: Performance Benchmarks (30 min)
```bash
pytest tests/test_performance.py -v --benchmark
```

## Phase 6: UAT (45 min)
Manual testing with real-world scenarios

---

# Success Metrics

| Metric | Target | Critical? |
|--------|--------|-----------|
| Test Pass Rate | 100% | Yes |
| Edge Case Coverage | ≥20 scenarios | Yes |
| Response Time (p90) | <2s | Yes |
| Response Time (p99) | <5s | No |
| AI Fallback Success | 100% | Yes |
| Memory Leak | 0 | Yes |
| Security Vulns | 0 critical | Yes |
| UAT Satisfaction | 4/5+ | No |

---

# Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Groq API down during demo | Medium | High | Implement robust fallback |
| Extreme input crashes system | Low | High | Input validation + limits |
| Slow performance at scale | Low | Medium | Benchmark + optimize |
| Security vulnerability | Low | High | Comprehensive security tests |

---

# Next Steps

1. **Run this full test suite** (estimate: 6 hours)
2. **Document all failures** in GitHub Issues
3. **Fix P0 issues** (edge cases, AI fallback, performance)
4. **Re-run tests** to verify fixes
5. **Generate test coverage report**
6. **Add CI/CD pipeline** (GitHub Actions) to run tests on every commit

---

# Appendix A: Sample Test Data

See `tests/fixtures/` for:
- `edge_case_scenarios.json` - 20+ pre-defined edge cases
- `stress_test_candidates.json` - 100 synthetic candidates
- `malformed_inputs.json` - Invalid data for robustness testing

---

# Appendix B: Performance Baseline

**Target Hardware:** Standard cloud VM (2 vCPU, 4 GB RAM)

| Scenario | Expected Time |
|----------|---------------|
| 5C x 5I | <1s |
| 10C x 10I | <2s |
| 100C x 10I | <5s |

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-20  
**Owner:** SlotMaxxer Team
