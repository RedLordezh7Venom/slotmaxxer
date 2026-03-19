# ⚡ SlotMaxxer: AI-Powered Interview Slot Optimizer

SlotMaxxer is a high-performance, recruiter-grade scheduling optimization engine. It utilizes a **Greedy Constraint-Satisfaction Algorithm** combined with **LLM-driven analysis** (via Groq/Llama-3) to transform natural language availability into perfectly optimized interview grids.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (Recommended: [uv](https://github.com/astral-sh/uv))
- **Groq API Key** (Get it at [console.groq.com](https://console.groq.com/))

### 2. Installation
```bash
git clone https://github.com/your-username/slotmaxxer.git
cd slotmaxxer
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_api_key_here
```

### 4. Run the Platform
```bash
uv run uvicorn api:app --port 8000 --reload
```
Visit **`http://localhost:8000`** to access the dashboard.

---

## 🏗️ Architecture Matrix

SlotMaxxer follows a decoupled, AI-augmented architecture for maximum reliability and speed.

```text
[ RECRUITER UI ]  <-- (REST / JSON) -->  [ FASTAPI GATEWAY ]
      |                                       |
      | (JS / Tailwind / Glassmorphism)       | (Logging & Validation)
      v                                       v
[ NATURAL LANG PARSER ]  <-- (Groq) -->  [ SCHEDULER ENGINE ]
      |                                       |
      | (LLama-3 JSON Mode)                   | (Greedy Optimization)
      v                                       v
[ STRUCTURED SLOTS ]    ------------->   [ OPTIMAL MATRIX ]
                                              |
                                              v
                                       [ REASONING ENGINE ]
                                       (Human-readable UX)
```

### Core Components:
- **`api.py`**: FastAPI endpoints (`/api/schedule`, `/api/reassign`).
- **`ai_processor.py`**: Integration with Groq for availability parsing and strategic reasoning.
- **`scheduler_engine.py`**: The "brain" that solves the N-to-N assignment problem using quality scorings.
- **`models.py`**: Pydantic data schemas (Timeslots, Assignments, Requests).
- **`utils.py`**: Time expansion (recurring slots) and recruiter email template generation.

---

## 🛠️ API Documentation

### `POST /api/schedule`
Generates a full schedule from a list of candidates and interviewers.
- **Payload**: `ScheduleRequest`
- **Output**: `ScheduleResponse` containing assignments, AI reasoning, and backup slots.

### `POST /api/reassign`
Handles a single cancellation and re-optimizes the remaining grid.
- **Payload**: `ReassignRequest`
- **Output**: `ReassignResponse` with visual diff data and impact analysis.

---

## 🌟 Example Use Cases

### Case 1: High-Density Recruiting
Input: *"Alice is free Tue-Thu afternoon. Dr. Bob is free Wed 9 AM-4 PM."*
**SlotMaxxer** identifies the overlapping Wed afternoon slot, assigns Alice to Dr. Bob, and benchmarks it as a "High-Quality Match" due to low density.

### Case 2: Emergency Cancellation
A candidate cancels their Wednesday slot.
**SlotMaxxer** instantly identifies the next best window across all panelists, generates a new email invitation, and provides a "Visual Diff" for the recruiter.

---

## 🔧 Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **API Error 422** | Check that input strings aren't empty. Use valid names. |
| **Groq Connection Failed** | Ensure your `GROQ_API_KEY` is set correctly in `.env`. |
| **Infinite Loading** | Check the terminal for uvicorn logs. The AI might be timing out. |
| **Zero Assignments** | Ensure at least one candidate time overlaps with one interviewer time. |

---

## 🤝 Contributing

We welcome optimizations to the constraint-satisfaction algorithm!
1. Fork the Repo.
2. Create your Feature Branch (`git checkout -b feature/AmazingAlgorithm`).
3. Commit your Changes (`git commit -m 'Add smarter weighting'`).
4. Push to the Branch (`git push origin feature/AmazingAlgorithm`).
5. Open a Pull Request.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

*Built with ⚡ by the SlotMaxxer Team.*
