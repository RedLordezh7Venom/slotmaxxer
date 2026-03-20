# SlotMaxxer: Complete Testing & Hardening Checklist

## Quick Start

```bash
# 1. Install test dependencies
pip install pytest pytest-timeout psutil

# 2. Generate test datasets
python generate_test_data.py

# 3. Run full test suite
python run_tests.py

# 4. Review results
cat test_report.txt
```

---

## Testing Phases Checklist

### ✅ Phase 1: Unit Testing (2 hours)

**Edge Cases (22 tests)**
- [ ] EC-001: Empty availability
- [ ] EC-002: Malformed time strings
- [ ] EC-003: Afternoon keyword expansion
- [ ] EC-004: Midnight boundary
- [ ] EC-005: Duplicate slot deduplication
- [ ] EC-006: Overlapping availability
- [ ] EC-007: Past date rejection
- [ ] EC-008: Mixed time format normalization
- [ ] EC-009: No overlap graceful failure
- [ ] EC-010: Partial overlap (<60 min)
- [ ] EC-011: Interviewer capacity exhaustion
- [ ] EC-012: Single interviewer sequential
- [ ] EC-013: Score tie deterministic ordering
- [ ] EC-014: Preference conflict reasoning
- [ ] EC-015: Recurring availability expansion
- [ ] EC-016: Scarcity multiplier logic
- [ ] EC-017: No preferences fallback
- [ ] EC-018: Cascading reassignment
- [ ] EC-019: Cancellation with no alternatives
- [ ] EC-020: Reassignment quality preservation
- [ ] EC-021: Fewer than 3 alternatives
- [ ] EC-022: Zero candidates error

**Command:**
```bash
pytest test_edge_cases.py -v --tb=short
```

**Expected:** All 22 tests pass

---

### ✅ Phase 2: Stress Testing (1 hour)

**Load Tests (8 tests)**
- [ ] ST-001: 100 candidates x 10 interviewers (<5s)
- [ ] ST-002: 1000 triplet sorting (<0.5s)
- [ ] ST-003: 50 parallel API requests
- [ ] ST-004: Extreme discretization performance
- [ ] ST-005: Deep conflict resolution
- [ ] ST-006: Memory stability (no leaks)
- [ ] ST-007: Unicode name handling
- [ ] ST-008: Long availability strings

**Command:**
```bash
pytest test_comprehensive.py::TestStressTesting -v --timeout=300
```

**Expected:** All pass with documented performance

---

### ✅ Phase 3: AI Failure Scenarios (45 min)

**Groq API Failures (6 tests)**
- [ ] AI-001: API downtime fallback
- [ ] AI-002: Rate limit handling (429)
- [ ] AI-003: Malformed JSON response
- [ ] AI-004: Timeout handling (>5s)
- [ ] AI-005: Empty response fallback
- [ ] AI-006: AI reasoning validation

**Setup:** Mock Groq API responses
```python
from unittest.mock import patch, MagicMock

@patch('ai_processor.groq_client')
def test_ai_failure(mock_groq):
    mock_groq.chat.completions.create.side_effect = Exception("API Down")
    # Test fallback behavior
```

**Expected:** Graceful fallback to rule-based parser

---

### ✅ Phase 4: Security Testing (1 hour)

**Vulnerability Checks (10 tests)**
- [ ] SEC-001: SQL injection prevention
- [ ] SEC-002: XSS prevention (frontend escaping)
- [ ] SEC-003: Oversized payload rejection
- [ ] SEC-004: API key not exposed in logs
- [ ] SEC-005: CORS policy enforcement
- [ ] SEC-006: Path traversal prevention
- [ ] SEC-007: DoS recursion prevention
- [ ] SEC-008: Email injection prevention
- [ ] SEC-009: Integer overflow validation
- [ ] SEC-010: No env var leakage in errors

**Additional Security Checks:**
```bash
# Static analysis
bandit -r . -ll

# Dependency vulnerabilities
pip-audit

# Secret scanning
gitleaks detect
```

**Expected:** 0 critical vulnerabilities

---

### ✅ Phase 5: Performance Benchmarks (30 min)

**Performance Targets (5 tests)**
- [ ] PERF-001: Baseline <2s (90th percentile)
- [ ] PERF-002: Algorithm O(n²) verification
- [ ] PERF-003: Groq API latency <1s avg
- [ ] PERF-004: Frontend load <1.5s (Lighthouse)
- [ ] PERF-005: Memory footprint <100 MB

**Benchmarking:**
```bash
# Backend performance
pytest test_comprehensive.py::TestPerformanceBenchmarks -v --benchmark

# Frontend performance (manual)
# 1. Open Chrome DevTools
# 2. Run Lighthouse audit
# 3. Verify: FCP <1.5s, LCP <2.5s, TTI <3.0s
```

**Expected:** All targets met

---

### ✅ Phase 6: Integration Testing (45 min)

**End-to-End Workflows**
- [ ] Full scheduling flow (input → AI parse → schedule → output)
- [ ] Reassignment workflow (cancel → re-run → new assignments)
- [ ] Email template generation
- [ ] Error handling (bad input → clear error message)

**API Testing:**
```bash
# Start server
uvicorn api:app --reload

# Test endpoints
curl -X POST http://localhost:8000/api/schedule \
  -H "Content-Type: application/json" \
  -d @test_data_scenarios.json

# Verify response time
ab -n 100 -c 10 http://localhost:8000/api/schedule
```

**Expected:** All endpoints return valid responses

---

### ✅ Phase 7: User Acceptance Testing (45 min)

**Real-World Scenarios (4 tests)**
- [ ] UAT-001: Recruiter workflow (copy-paste messy availability)
- [ ] UAT-002: Edge case - no perfect match
- [ ] UAT-003: Mobile experience (responsive)
- [ ] UAT-004: Print output (formatting preserved)

**Testing Protocol:**
1. Act as a recruiter (no technical knowledge)
2. Use the system without documentation
3. Time how long it takes to schedule 3 interviews
4. Rate ease of use (1-5 scale)

**Expected:** 
- Task completion <5 min
- Ease of use ≥4/5
- Zero confusion about output

---

## Defect Tracking

### Critical Issues (Block Production)
| ID | Description | Status | Assignee |
|----|-------------|--------|----------|
| - | - | - | - |

### High Priority (Fix Before Demo)
| ID | Description | Status | Assignee |
|----|-------------|--------|----------|
| - | - | - | - |

### Medium Priority (Nice to Have)
| ID | Description | Status | Assignee |
|----|-------------|--------|----------|
| - | - | - | - |

---

## Test Coverage Report

**Target:** >80% code coverage

```bash
# Generate coverage report
pytest --cov=. --cov-report=html --cov-report=term

# View report
open htmlcov/index.html
```

**Coverage Targets:**
- `scheduler_engine.py`: >90%
- `ai_processor.py`: >80%
- `models.py`: >95%
- `utils.py`: >85%
- `api.py`: >75%

---

## Performance Baselines (Document Actual Results)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| 5C x 5I (p90) | <2s | ___ | ⬜ |
| 10C x 10I (p90) | <2s | ___ | ⬜ |
| 100C x 10I (p90) | <5s | ___ | ⬜ |
| Memory (typical) | <100 MB | ___ | ⬜ |
| Groq API latency | <1s | ___ | ⬜ |

---

## Security Audit Checklist

### Code Security
- [ ] No hardcoded secrets (API keys in .env only)
- [ ] Input validation on all endpoints
- [ ] Error messages don't expose internals
- [ ] No eval() or exec() usage
- [ ] Dependencies up to date (no known CVEs)

### API Security
- [ ] CORS configured appropriately
- [ ] Rate limiting implemented (if needed)
- [ ] Request size limits enforced
- [ ] HTTPS enforced (in production)
- [ ] API key rotation procedure documented

### Data Security
- [ ] No PII logged
- [ ] Email addresses validated
- [ ] HTML escaped in frontend
- [ ] SQL injection not possible (no DB anyway)
- [ ] File upload not exposed

---

## Deployment Readiness Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Security audit complete
- [ ] Documentation complete
- [ ] Demo script prepared
- [ ] Error handling tested
- [ ] Monitoring/logging configured

### Deployment
- [ ] .env.example provided
- [ ] requirements.txt/pyproject.toml up to date
- [ ] README with clear setup instructions
- [ ] Health check endpoint (/health)
- [ ] Deployment instructions (Railway/Heroku/etc.)
- [ ] Environment variables documented

### Post-Deployment
- [ ] Smoke test in production
- [ ] Response time monitoring
- [ ] Error rate monitoring
- [ ] User feedback collection mechanism

---

## Continuous Improvement

### Monitoring Metrics
1. **Response time** (p50, p90, p99)
2. **Error rate** (4xx, 5xx)
3. **Assignment success rate** (% candidates assigned)
4. **AI fallback rate** (how often rule-based parser used)
5. **User satisfaction** (feedback scores)

### A/B Testing Opportunities
- Scoring weight adjustments
- Discretization step size (30 min vs 15 min)
- AI prompt variations
- UI layout changes

---

## Final Sign-Off

### Testing Complete
- [ ] All automated tests passed
- [ ] Manual UAT completed
- [ ] Performance verified
- [ ] Security reviewed
- [ ] Documentation updated
- [ ] Demo rehearsed

### Ready for Submission
- [ ] Code pushed to GitHub
- [ ] README polished
- [ ] Demo video recorded (optional)
- [ ] Test report included
- [ ] Known limitations documented

**Tested By:** _______________  
**Date:** _______________  
**Approval:** _______________

---

## Appendix: Quick Command Reference

```bash
# Full test suite
python run_tests.py

# Individual test suites
pytest test_edge_cases.py -v
pytest test_comprehensive.py::TestStressTesting -v
pytest test_comprehensive.py::TestSecurityTesting -v

# With coverage
pytest --cov=. --cov-report=html

# Generate test data
python generate_test_data.py

# Start server for manual testing
uvicorn api:app --reload --port 8000

# Performance profiling
python -m cProfile -o profile.stats api.py
snakeviz profile.stats

# Memory profiling
python -m memory_profiler api.py
```

---

## Known Limitations (Document These)

1. **Timezone:** Single timezone assumed (specify in docs)
2. **Panel interviews:** Only 1 interviewer per slot (v2 feature)
3. **Calendar integration:** No automatic syncing (manual copy-paste)
4. **Historical data:** No persistence (stateless by design)
5. **Multi-round interviews:** Not automatically scheduled

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-20  
**Status:** Ready for Testing
