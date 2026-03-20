"""
SlotMaxxer Manual Test Suite
Runs 10 test cases against the API and writes results to output file
Author: Assessment Testing
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any


class SlotMaxxerTester:
    """Test runner for SlotMaxxer API"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results = []
        
    def run_test(self, test_name: str, test_data: Dict, expected: str) -> Dict:
        """Run a single test case"""
        print(f"\n{'='*80}")
        print(f"Running: {test_name}")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.api_url}/api/schedule",
                json=test_data,
                timeout=10
            )
            elapsed = time.time() - start_time
            
            result = {
                "test_name": test_name,
                "status": "PASS" if response.status_code == 200 else "FAIL",
                "status_code": response.status_code,
                "response_time_ms": int(elapsed * 1000),
                "expected": expected,
                "response_data": response.json() if response.status_code == 200 else None,
                "error": None if response.status_code == 200 else response.text,
                "timestamp": datetime.now().isoformat()
            }
            
            # Pretty print for console
            if response.status_code == 200:
                data = response.json()
                print(f"✓ SUCCESS - {elapsed*1000:.0f}ms")
                if data.get("assignments"):
                    for assignment in data["assignments"]:
                        print(f"  → {assignment.get('candidate', 'N/A')}: {assignment.get('scheduled_slot', {}).get('time', 'N/A')}")
                        print(f"    Score: {assignment.get('quality_score', 0)}")
                        print(f"    Reasoning: {assignment.get('reasoning', 'N/A')[:100]}...")
                else:
                    print(f"  → No assignments (expected for edge cases)")
            else:
                print(f"✗ FAILED - HTTP {response.status_code}")
                print(f"  Error: {response.text[:200]}")
                
        except Exception as e:
            elapsed = time.time() - start_time
            result = {
                "test_name": test_name,
                "status": "ERROR",
                "status_code": None,
                "response_time_ms": int(elapsed * 1000),
                "expected": expected,
                "response_data": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"✗ ERROR: {str(e)}")
        
        self.results.append(result)
        return result
    
    def generate_report(self, output_file: str = "test_results.json"):
        """Generate detailed test report"""
        
        # Summary stats
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        avg_time = sum(r["response_time_ms"] for r in self.results) / total if total > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
                "avg_response_time_ms": int(avg_time),
                "generated_at": datetime.now().isoformat()
            },
            "tests": self.results
        }
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Also create human-readable version
        readable_file = output_file.replace('.json', '_readable.txt')
        with open(readable_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("SLOTMAXXER TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            
            f.write("SUMMARY\n")
            f.write("-"*80 + "\n")
            f.write(f"Total Tests:        {total}\n")
            f.write(f"Passed:             {passed} ✓\n")
            f.write(f"Failed:             {failed} ✗\n")
            f.write(f"Errors:             {errors} ⚠\n")
            f.write(f"Pass Rate:          {report['summary']['pass_rate']}\n")
            f.write(f"Avg Response Time:  {int(avg_time)}ms\n")
            f.write(f"\n")
            
            f.write("DETAILED RESULTS\n")
            f.write("="*80 + "\n\n")
            
            for i, result in enumerate(self.results, 1):
                f.write(f"Test #{i}: {result['test_name']}\n")
                f.write("-"*80 + "\n")
                f.write(f"Status:          {result['status']}\n")
                f.write(f"Response Time:   {result['response_time_ms']}ms\n")
                f.write(f"Expected:        {result['expected']}\n")
                
                if result['status'] == 'PASS' and result['response_data']:
                    data = result['response_data']
                    f.write(f"\nResults:\n")
                    
                    if data.get('assignments'):
                        for j, assignment in enumerate(data['assignments'], 1):
                            f.write(f"  Assignment {j}:\n")
                            f.write(f"    Candidate:  {assignment.get('candidate', 'N/A')}\n")
                            f.write(f"    Interviewer: {assignment.get('interviewer', 'N/A')}\n")
                            f.write(f"    Time:       {assignment.get('scheduled_slot', {}).get('time', 'N/A')}\n")
                            f.write(f"    Day:        {assignment.get('scheduled_slot', {}).get('day', 'N/A')}\n")
                            f.write(f"    Score:      {assignment.get('quality_score', 0)}\n")
                            f.write(f"    Reasoning:  {assignment.get('reasoning', 'N/A')[:150]}...\n")
                            
                            if assignment.get('alternatives'):
                                f.write(f"    Alternatives: {len(assignment['alternatives'])} backup slots\n")
                    else:
                        f.write(f"  No assignments made\n")
                    
                    if data.get('unassigned_candidates'):
                        f.write(f"\nUnassigned: {len(data['unassigned_candidates'])} candidates\n")
                    
                    if data.get('conflicts'):
                        f.write(f"\nConflicts: {data.get('conflicts')}\n")
                
                elif result['error']:
                    f.write(f"\nError: {result['error']}\n")
                
                f.write("\n" + "="*80 + "\n\n")
        
        print(f"\n{'='*80}")
        print(f"TEST REPORT GENERATED")
        print(f"{'='*80}")
        print(f"JSON Report:     {output_file}")
        print(f"Readable Report: {readable_file}")
        print(f"\nSummary: {passed}/{total} passed ({report['summary']['pass_rate']})")
        print(f"Avg Response Time: {int(avg_time)}ms")
        

def get_test_cases() -> List[Dict]:
    """Define all test cases"""
    
    return [
        # NOMINAL CASE 1: Exact Example from Instructions
        {
            "name": "NOMINAL-1: Exact Example (Tue 3-4 PM)",
            "data": {
                "candidates": [
                    {
                        "name": "Sarah Johnson",
                        "availability": "Tue 2-5 PM"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Interviewer A",
                        "availability": "Tue 3-6 PM"
                    },
                    {
                        "name": "Interviewer B",
                        "availability": "Tue 1-4 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "Assigns Tue 3-4 PM (matches instructions example)"
        },
        
        # NOMINAL CASE 2: Multi-Day Multiple Interviewers
        {
            "name": "NOMINAL-2: Multi-Day (Wed 3-4 PM preferred)",
            "data": {
                "candidates": [
                    {
                        "name": "Mike Chen",
                        "availability": "Tue-Thu 2-5 PM, Fri 9 AM-12 PM"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. A",
                        "availability": "Wed 3-5 PM"
                    },
                    {
                        "name": "Dr. B",
                        "availability": "Thu 2-4 PM"
                    },
                    {
                        "name": "Dr. C",
                        "availability": "Fri 10 AM-12 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "Multiple valid slots, Wed 15:00 ranked highest"
        },
        
        # NOMINAL CASE 3: Natural Language Parsing
        {
            "name": "NOMINAL-3: Natural Language (AI Parse)",
            "data": {
                "candidates": [
                    {
                        "name": "Emily Davis",
                        "availability": "Tuesday and Thursday afternoons"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. Smith",
                        "availability": "Tue-Thu 2-5 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "AI parses 'afternoons' correctly, assigns Tue or Thu 2-3 PM"
        },
        
        # NOMINAL CASE 4: Scarcity Priority
        {
            "name": "NOMINAL-4: Scarcity Priority (Rare Interviewer)",
            "data": {
                "candidates": [
                    {
                        "name": "Alex Rodriguez",
                        "availability": "Mon-Fri 9 AM-5 PM"
                    }
                ],
                "interviewers": [
                    {
                        "name": "CEO (Limited)",
                        "availability": "Mon 10-11 AM only"
                    },
                    {
                        "name": "Engineer (Flexible)",
                        "availability": "Mon-Fri 9 AM-5 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "Assigns to CEO (scarce resource), high priority score"
        },
        
        # NOMINAL CASE 5: Multiple Candidates Sequential
        {
            "name": "NOMINAL-5: Three Candidates Sequential",
            "data": {
                "candidates": [
                    {
                        "name": "Jane Doe",
                        "availability": "Monday 9 AM-5 PM"
                    },
                    {
                        "name": "John Smith",
                        "availability": "Monday 9 AM-5 PM"
                    },
                    {
                        "name": "Lisa Wang",
                        "availability": "Monday 9 AM-5 PM"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. Johnson",
                        "availability": "Monday 10 AM-4 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "All 3 assigned different 1-hour slots, no conflicts"
        },
        
        # EDGE CASE 1: No Overlap
        {
            "name": "EDGE-1: Zero Overlap",
            "data": {
                "candidates": [
                    {
                        "name": "Grace Thompson",
                        "availability": "Monday mornings only"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. Martinez",
                        "availability": "Tuesday afternoons only"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "No overlap detected, clear error message with suggestions"
        },
        
        # EDGE CASE 2: Partial Overlap
        {
            "name": "EDGE-2: Partial Overlap (30 min)",
            "data": {
                "candidates": [
                    {
                        "name": "Tom Wilson",
                        "availability": "Wed 2:00-2:45 PM"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. Lee",
                        "availability": "Wed 2:30-5:00 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "Warning about insufficient duration or extends slot"
        },
        
        # EDGE CASE 3: Capacity Exhaustion
        {
            "name": "EDGE-3: Capacity Exhaustion (5 candidates, 1 slot)",
            "data": {
                "candidates": [
                    {"name": f"Candidate {i}", "availability": "Monday 9 AM-5 PM"}
                    for i in range(1, 6)
                ],
                "interviewers": [
                    {
                        "name": "Solo Interviewer",
                        "availability": "Monday 10-11 AM only"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "1 assigned, 4 unassigned with clear message"
        },
        
        # EDGE CASE 4: Empty Availability
        {
            "name": "EDGE-4: Empty Candidate Availability",
            "data": {
                "candidates": [
                    {
                        "name": "Invalid Candidate",
                        "availability": ""
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. Brown",
                        "availability": "Tuesday 2-5 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "Validation error with clear message"
        },
        
        # EDGE CASE 5: Peak Time Optimization
        {
            "name": "EDGE-5: Peak Time Preference (10 AM-2 PM)",
            "data": {
                "candidates": [
                    {
                        "name": "Noah Brown",
                        "availability": "Monday 9 AM-5 PM"
                    }
                ],
                "interviewers": [
                    {
                        "name": "Dr. Garcia",
                        "availability": "Monday 9 AM-5 PM"
                    }
                ],
                "interview_duration_minutes": 60
            },
            "expected": "Top 3 slots in peak time range (10 AM-2 PM preferred)"
        }
    ]


def main():
    """Run all tests and generate report"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         SlotMaxxer Manual Test Suite                     ║
    ║                                                           ║
    ║  Running 10 test cases (5 nominal + 5 edge cases)        ║
    ║  Results will be written to test_results.json            ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Configuration
    API_URL = "http://localhost:8000"  # Change if needed
    
    # Initialize tester
    tester = SlotMaxxerTester(api_url=API_URL)
    
    # Get test cases
    test_cases = get_test_cases()
    
    print(f"\nConnecting to API at: {API_URL}")
    print(f"Total tests to run: {len(test_cases)}\n")
    
    # Run all tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] ", end="")
        tester.run_test(
            test_name=test_case["name"],
            test_data=test_case["data"],
            expected=test_case["expected"]
        )
        time.sleep(0.5)  # Small delay between tests
    
    # Generate report
    print("\n\nGenerating test report...")
    tester.generate_report("test_results.json")
    
    # Final summary
    passed = sum(1 for r in tester.results if r["status"] == "PASS")
    total = len(tester.results)
    
    print(f"\n{'='*80}")
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print(f"{'='*80}")
        print("\nSlotMaxxer is ready for submission!")
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print(f"{'='*80}")
        print("\nReview test_results_readable.txt for details")
    
    print("\nNext steps:")
    print("1. Review test_results_readable.txt")
    print("2. Check any failed tests")
    print("3. Take screenshots of successful cases")
    print("4. Include results in submission")


if __name__ == "__main__":
    main()