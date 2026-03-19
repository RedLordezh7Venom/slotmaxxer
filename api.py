import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import Candidate, Interviewer, Assignment, TimeSlot
from ai_processor import parse_availability_with_ai, generate_assignment_reasoning, resolve_conflicts_with_ai
from utils import expand_recurring_availability
from scheduler_engine import generate_feasible_assignments, calculate_quality_score, optimal_assign

app = FastAPI(title="SlotMaxxer API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request/Response Models ---

class AvailabilityInput(BaseModel):
    name: str
    availability: str
    email: Optional[str] = "candidate@example.com"
    role: Optional[str] = "Engineer"

class InterviewerInput(BaseModel):
    name: str
    availability: str
    capacity: int = 5

class ScheduleRequest(BaseModel):
    candidates: List[AvailabilityInput]
    interviewers: List[InterviewerInput]
    duration: int = 60

class ScheduledSlot(BaseModel):
    day: str
    date: Optional[str]
    time: str

class AssignmentResponse(BaseModel):
    candidate: str
    interviewer: str
    slot: ScheduledSlot
    score: int
    reasoning: str
    alternatives: List[ScheduledSlot]

class ScheduleResponse(BaseModel):
    success: bool
    assignments: List[AssignmentResponse]
    unassigned: List[str]
    conflict_resolution: Optional[str]


# --- Helpers ---

def format_slot(slot: TimeSlot) -> ScheduledSlot:
    return ScheduledSlot(
        day=slot.day.value,
        date=slot.date.isoformat() if slot.date else None,
        time=f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
    )


# --- Endpoints ---

@app.post("/api/schedule", response_model=ScheduleResponse)
async def schedule_interviews(req: ScheduleRequest):
    try:
        # 1. Parse Inputs (Natural Language -> Structured Models)
        internal_candidates = []
        for c in req.candidates:
            raw_slots = parse_availability_with_ai(c.availability)
            expanded = expand_recurring_availability(raw_slots)
            internal_candidates.append(Candidate(
                id=str(uuid.uuid4())[:8],
                name=c.name,
                email=c.email,
                availability=expanded,
                role=c.role
            ))

        internal_interviewers = []
        for i in req.interviewers:
            raw_slots = parse_availability_with_ai(i.availability)
            expanded = expand_recurring_availability(raw_slots)
            internal_interviewers.append(Interviewer(
                id=str(uuid.uuid4())[:8],
                name=i.name,
                availability=expanded,
                capacity=i.capacity
            ))

        # 2. Generate Feasibility Matrix
        triplets = generate_feasible_assignments(
            internal_candidates, 
            internal_interviewers, 
            required_duration=req.duration
        )

        # 3. Scoring
        scored_triplets = []
        # Pre-calculate interviewer scarcity
        interviewer_total_slots = {i.id: len(i.availability) for i in internal_interviewers}
        
        for c_obj, slot, i_obj in triplets:
            score = calculate_quality_score(c_obj, slot, i_obj, interviewer_total_slots[i_obj.id])
            scored_triplets.append((c_obj, slot, i_obj, score))

        # 4. Optimal Assignment
        assignments, unassigned = optimal_assign(scored_triplets, internal_candidates)

        # 5. Enrich with AI Reasoning
        final_assignments = []
        for a in assignments:
            # Map IDs back to objects for reasoning name lookup
            cand = next(c for c in internal_candidates if c.id == a.candidate_id)
            intv = next(i for i in internal_interviewers if i.id == a.interviewer_id)
            
            ai_reasoning = generate_assignment_reasoning(
                candidate_name=cand.name,
                interviewer_name=intv.name,
                slot=a.slot,
                score=a.quality_score,
                is_preferred=any(p.contains(a.slot) for p in cand.preferred_slots)
            )
            
            final_assignments.append(AssignmentResponse(
                candidate=cand.name,
                interviewer=intv.name,
                slot=format_slot(a.slot),
                score=a.quality_score,
                reasoning=ai_reasoning,
                alternatives=[format_slot(alt) for alt in a.alternatives]
            ))

        # 6. Conflict Resolution for Unassigned
        resolution_strategy = None
        if unassigned:
            resolution_strategy = resolve_conflicts_with_ai(
                unassigned=unassigned,
                assignments=assignments,
                feasible_matrix=scored_triplets
            )

        return ScheduleResponse(
            success=True,
            assignments=final_assignments,
            unassigned=[c.name for c in unassigned],
            conflict_resolution=resolution_strategy
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "engine": "SlotMaxxer-v1"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
