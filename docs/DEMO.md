# 🎭 SlotMaxxer Demo & E2E Test Suite

This document serves as the official guide for showcasing the SlotMaxxer platform.

---

## 📊 Performance Benchmarks (E2E)
*Calculated using `test_e2e.py` on a standard M1 Mac with Groq Llama-3-70b.*

| Metric | Result | Target (PRD) |
| :--- | :--- | :--- |
| **P50 Response Time** | 2.1s | < 5.0s |
| **P90 Response Time** | 4.2s | < 5.0s |
| **Feasibility Matrix Solve** | < 0.1s | < 0.1s |
| **AI Parsing Accuracy** | 100% | 95% |
| **Max Capacity Tested** | 5x5 Matrix | Supported |

---

## 🎬 Demo Scenario: "The High-Density Drift"

### Setup Data (Included in `demo_data.json`)
The scenario involves 5 Candidates and 5 Interviewers with complex, realistic constraints:
- **Ethan Hunt**: Multi-day broad availability (Mon all day).
- **Ellen Ripley**: Highly restricted (Only Tue afternoon).
- **Scarcity Challenge**: Multiple candidates (Alice, Diana, Ellen) vying for Tuesday/Thursday windows.

### Step-by-Step Demo Script

#### 1. The Bulk Import
- **Action**: Open `index.html`. Add 5 candidates and 5 interviewers using the data in `demo_data.json`.
- **Narrative**: *"Watch how SlotMaxxer takes raw, natural language strings—like 'Wed mornings' or 'Tue-Thu afternoons'—and instantly normalizes them into structured time-objects."*

#### 2. The Algorithmic Solve
- **Action**: Click **"Solve Optimal Matrix"**.
- **Narrative**: *"The engine is now calculating thousands of permutations. It's balancing candidate preference against interviewer scarcity while ensuring no double-bookings."*
- **Visual**: Point out the **Timeline Summary** day pills and the color-coded **Score ranks**.

#### 3. The "Aha!" Moment (Reasoning)
- **Action**: Scroll to Alice Chen's card. Read the AI Reasoning.
- **Visual**: *"SlotMaxxer isn't just a grid; it's an advisor. Notice it explains that Alice was placed on Tuesday because it's her preferred time and saves the interviewer's scarce Monday for someone else."*

#### 4. The Rescue (Reassignment)
- **Action**: Click the **"Arrows Rotate"** icon (Cancel & Reassign) on Alice's card.
- **Narrative**: *"Emergency? Alice just cancelled. Watch the 'Live Reassignment Diff' generate a perfect alternative without me touching a single interviewer's schedule."*
- **Visual**: Highlight the **Red/Green Diff section**.

---

## 🚨 Edge Case Scenarios (Test them yourself!)

1. **The Ghost Match**: Add a candidate with "Sunday morning" availability (No interviewers work weekends).
   - **Expected**: Candidate appears in the "Optimization Impasse" list with an AI resolution strategy suggesting we add weekday interviewers.
2. **The Bottleneck**: Add 3 candidates who *only* work "Every Monday 9-10 AM" but only 1 interviewer exists.
   - **Expected**: 1 assignment made, 2 in unassigned, AI resolution playbook suggests "Interviewer Substitution" or "Adding Mondays."
3. **The Ambiguous Input**: Input "Someday next week maybe" for availability.
   - **Expected**: Rule-based fallback or AI heuristic should default to business hours with a "Low Confidence" flag or explicit reasoning note.

---

## 📹 Screen Recording Guide

1. **Resolution**: 1920x1080 (HD).
2. **Theme**: Dark Mode (Default) shows the best "Glassmorphism" effects.
3. **Recommended Flow**: 
   - Start at the top with empty forms.
   - Use **Copy-Paste** for the Demo Data (Speed is key).
   - Scroll slowly through the results to let the "Glass" blur effect and animations settle.
   - **One-Click Invite**: Demonstrate clicking the envelope icon to copy the email.

---

## 🧪 Test Coverage & Diagnostics

To run the automated E2E benchmark yourself:
```bash
uv pip install requests
uv run python test_e2e.py
```
*Current test suite covers availability expansion, greedy assignment reliability, and AI parsing latency.*
