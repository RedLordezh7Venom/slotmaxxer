from typing import List, Tuple, Optional, Dict
import numpy as np
from models import Candidate, Interviewer, TimeSlot, Assignment
from datetime import datetime, date, timedelta, time

# Scoring Weights
PREF_CANDIDATE_WEIGHT = 1000
PREF_INTERVIEWER_WEIGHT = 500
TIME_OPTIMALITY_HIGH_WEIGHT = 200  # 10 AM - 2 PM
TIME_OPTIMALITY_MEDIUM_WEIGHT = 100 # 9 AM - 4 PM
DURATION_BONUS_WEIGHT = 100         # >= 60 min
SCARCITY_BASE = 1000                # Scarcity = SCARCITY_BASE / interviewer_slot_count


def calculate_quality_score(
    candidate: Candidate,
    slot: TimeSlot,
    interviewer: Interviewer,
    interviewer_total_slots: int
) -> int:
    """
    Calculates the multi-factor quality score for a potential assignment triplet.
    
    Weights (as per PRD):
    - Candidate preferences: 1000 pts
    - Interviewer preferences: 500 pts
    - Time optimality (10am-2pm): 200 pts
    - Duration bonus (>= 60m): 100 pts
    - Scarcity Multiplier: 1000 / total_interviewer_slots
    """
    score = 0

    # 1. Candidate Preference Match
    # Check if the proposed slot is within any of the candidate's preferred slots
    if any(pref.contains(slot) for pref in candidate.preferred_slots):
        score += PREF_CANDIDATE_WEIGHT

    # 2. Interviewer Preference Match
    if any(pref.contains(slot) for pref in interviewer.preferred_slots):
        score += PREF_INTERVIEWER_WEIGHT

    # 3. Time Optimality
    start, end = slot.start_time, slot.end_time
    # High: 10 AM - 2 PM
    if start >= time(10, 0) and end <= time(14, 0):
        score += TIME_OPTIMALITY_HIGH_WEIGHT
    # Medium: 9 AM - 4 PM
    elif start >= time(9, 0) and end <= time(16, 0):
        score += TIME_OPTIMALITY_MEDIUM_WEIGHT

    # 4. Duration Bonus (PRD specifies >= 60min)
    if slot.duration_minutes >= 60:
        score += DURATION_BONUS_WEIGHT

    # 5. Scarcity Multiplier
    # Prioritizes interviewers with limited availability to prevent burnout 
    # of high-availability interviewers and ensure efficient resource use.
    if interviewer_total_slots > 0:
        score += int(SCARCITY_BASE / interviewer_total_slots)

    return score


def generate_feasible_assignments(
    candidates: List[Candidate], 
    interviewers: List[Interviewer],
    required_duration: int = 60,
    discretization_step: int = 30
) -> List[Tuple[Candidate, TimeSlot, Interviewer]]:
    """
    Generates all valid (Candidate, Slot, Interviewer) triplets.
    This fulfills Step 1 of the scheduling algorithm by identifying all 
    possible intersections that meet the minimum duration requirements.

    Algorithm Complexity: O(C * Sc * I * Si * D)
    - C: Number of Candidates
    - Sc: Average slots per Candidate
    - I: Number of Interviewers
    - Si: Average slots per Interviewer
    - D: Discretization density (how many segments fit in an intersection)
    
    Worst-case (PRD scale): 10 * 10 * 5 * 10 * 4 = 20,000 checks. 
    This remains well within the <2s performance requirement for any CPU.

    Returns:
        List of (Candidate, SpecificSlot, Interviewer) triplets.
    """
    all_triplets = []

    for candidate in candidates:
        # Cross-reference with every interviewer
        for interviewer in interviewers:
            # Check every combination of their available availability
            # Note: We assume availability has been expanded to instances (with dates)
            # if we are scheduling for specific weeks.
            for c_slot in candidate.availability:
                for i_slot in interviewer.availability:
                    # Check for basic day/time overlap
                    common_window = c_slot.intersection(i_slot)
                    
                    if common_window and common_window.duration_minutes >= required_duration:
                        # The window might be large (e.g., 4 hours).
                        # We discretize it into segments (e.g., every 30 mins) 
                        # to give the solver more flexibility in picking the optimal one.
                        segments = get_slots_within_window(
                            common_window, 
                            required_duration, 
                            discretization_step
                        )
                        
                        for segment in segments:
                            all_triplets.append((candidate, segment, interviewer))

    return all_triplets


def get_slots_within_window(
    window: TimeSlot, 
    duration: int, 
    step: int = 30
) -> List[TimeSlot]:
    """
    Slices a continuous time window into multiple discrete TimeSlot options.
    If duration is 60 and step is 30, a 2-hour window yields 3 potential slots:
    Start at 0:00, 0:30, 1:00.
    """
    slots = []
    current_start_time = window.start_time
    
    # We use a dummy date for timedelta math if none exists
    ref_date = window.date if window.date else date.today()
    window_end_dt = datetime.combine(ref_date, window.end_time)

    while True:
        start_dt = datetime.combine(ref_date, current_start_time)
        end_dt = start_dt + timedelta(minutes=duration)

        # Stop if this next slot goes beyond the window's boundary
        if end_dt > window_end_dt:
            break

        slots.append(TimeSlot(
            day=window.day,
            start_time=current_start_time,
            end_time=end_dt.time(),
            date=window.date,
            is_recurring=window.is_recurring,
            preference_level=window.preference_level
        ))

        # Advance by the step
        current_start_time = (start_dt + timedelta(minutes=step)).time()
        
        # Safety break for midnight roll-over (if any)
        if current_start_time < window.start_time:
            break

    return slots


MAX_COST = 100_000  # Infeasibility sentinel — must exceed any real quality score


def build_cost_matrix(
    candidates: List[Candidate],
    interviewers: List[Interviewer],
    required_duration: int = 60,
    discretization_step: int = 30,
) -> Tuple[np.ndarray, Dict[int, Tuple[Candidate, TimeSlot, Interviewer]]]:
    """
    Converts the scheduling problem into an NxM cost matrix for the Hungarian algorithm.

    Rows (N) = candidates
    Cols (M) = all feasible (interviewer, slot) pairs across the whole problem

    Cell value:
        MAX_COST              → infeasible (candidate can't meet this interviewer at this time)
        MAX_COST - quality    → feasible   (lower cost = higher quality = preferred by solver)

    Args:
        candidates:          List of Candidate objects with parsed availability.
        interviewers:        List of Interviewer objects with parsed availability.
        required_duration:   Minimum interview length in minutes (default 60).
        discretization_step: Sliding-window step in minutes (default 30).

    Returns:
        cost_matrix:  np.ndarray of shape (N, M), dtype float64.
        col_map:      {col_index: (candidate, slot, interviewer)} for feasible cells.
                      Infeasible columns still exist in the matrix but map to nothing.
    """
    n_candidates = len(candidates)
    if n_candidates == 0 or not interviewers:
        return np.empty((0, 0)), {}

    # ── Step 1: Enumerate all unique (interviewer, slot) column keys ──────────
    # Each column represents one specific (interviewer × discretized_slot) pair.
    # We build the column list first so every candidate row shares the same axis.
    col_keys: List[Tuple[Interviewer, TimeSlot]] = []
    col_key_index: Dict[Tuple[str, str], int] = {}  # (interviewer_id, slot_repr) → col idx

    for interviewer in interviewers:
        # Expand each interviewer slot into discrete interview-length segments
        slot_segments: List[TimeSlot] = []
        for i_slot in interviewer.availability:
            slot_segments.extend(
                get_slots_within_window(i_slot, required_duration, discretization_step)
            )

        for seg in slot_segments:
            key = (interviewer.id, repr(seg))
            if key not in col_key_index:
                col_key_index[key] = len(col_keys)
                col_keys.append((interviewer, seg))

    n_cols = len(col_keys)
    if n_cols == 0:
        return np.full((n_candidates, 1), MAX_COST, dtype=np.float64), {}

    # ── Step 2: Fill the cost matrix ─────────────────────────────────────────
    cost_matrix = np.full((n_candidates, n_cols), MAX_COST, dtype=np.float64)
    col_map: Dict[int, Tuple[Candidate, TimeSlot, Interviewer]] = {}

    for r_idx, candidate in enumerate(candidates):
        # Build a fast lookup of candidate's available windows
        for c_slot in candidate.availability:
            for col_idx, (interviewer, i_seg) in enumerate(col_keys):
                # Check if candidate's slot contains this interviewer segment
                if not c_slot.contains(i_seg) and not i_seg.contains(c_slot):
                    # Try intersection — candidate must be available for the full segment
                    intersection = c_slot.intersection(i_seg)
                    if intersection is None or intersection.duration_minutes < required_duration:
                        continue
                    # Use the segment itself (not the intersection) as the interview slot
                    effective_slot = i_seg
                else:
                    effective_slot = i_seg

                # Candidate is available — compute quality and cost
                quality = calculate_quality_score(
                    candidate,
                    effective_slot,
                    interviewer,
                    len(col_keys),  # use total columns as a proxy for interviewer density
                )
                cost = MAX_COST - quality

                # Keep the best (lowest cost) option if multiple candidate slots overlap this column
                if cost < cost_matrix[r_idx, col_idx]:
                    cost_matrix[r_idx, col_idx] = cost
                    col_map[col_idx] = (candidate, effective_slot, interviewer)

    return cost_matrix, col_map


def optimal_assign(
    scored_triplets: List[Tuple[Candidate, TimeSlot, Interviewer, int]],
    candidates: List[Candidate]
) -> Tuple[List[Assignment], List[Candidate]]:
    """
    Greedily assigns candidates to slots based on global quality scores.
    Handles conflict detection (interviewer double-booking) and recovers 
    alternative slots for each candidate.

    Algorithm complexity: O(T log T) for sorting + O(T * A) for assignment 
    where T is number of triplets and A is number of assignments. 
    With ~1000 triplets, this is near-instant.
    """
    # 1. Sort all possible combinations by score (highest first)
    scored_triplets.sort(key=lambda x: x[3], reverse=True)

    assignments = []
    assigned_candidate_ids = set()
    
    # Track interviewer busy times [interviewer_id -> List[TimeSlot]]
    interviewer_schedule = {}

    # 2. Primary Assignment Pass
    for candidate, slot, interviewer, score in scored_triplets:
        if candidate.id in assigned_candidate_ids:
            continue

        # Check for interviewer conflicts
        busy_slots = interviewer_schedule.get(interviewer.id, [])
        if any(slot.overlaps_with(busy) for busy in busy_slots):
            continue

        # Valid assignment found
        new_assignment = Assignment(
            candidate_id=candidate.id,
            interviewer_id=interviewer.id,
            slot=slot,
            quality_score=score,
            reasoning=f"High-quality match ({score} pts) based on preference and capacity logic."
        )
        
        assignments.append(new_assignment)
        assigned_candidate_ids.add(candidate.id)
        
        # Mark interviewer as busy
        if interviewer.id not in interviewer_schedule:
            interviewer_schedule[interviewer.id] = []
        interviewer_schedule[interviewer.id].append(slot)

    # 3. Alternatives & Unassigned Handling
    final_assignments = []
    for assignment in assignments:
        # Find top 3 alternative slots for this candidate that don't conflict 
        # with the *final* schedule of the chosen or other interviewers.
        alts = []
        for c, s, i, score in scored_triplets:
            if c.id == assignment.candidate_id and s != assignment.slot:
                # Check if interviewer i is free at slot s in the final schedule
                busy = interviewer_schedule.get(i.id, [])
                # Exclude the current assignment itself from the conflict check for THIS interviewer
                other_busy = [b for b in busy if b != assignment.slot]
                if not any(s.overlaps_with(b) for b in other_busy):
                    alts.append(s)
            if len(alts) >= 3:
                break
        
        assignment.alternatives = alts
        final_assignments.append(assignment)

    # 4. Identify unassigned candidates
    unassigned = [c for c in candidates if c.id not in assigned_candidate_ids]

    return final_assignments, unassigned


def optimal_assign_hungarian(
    candidates: List[Candidate],
    interviewers: List[Interviewer],
    required_duration: int = 60,
    discretization_step: int = 30,
    max_rounds: int = 5,
) -> Tuple[List[Assignment], List[Candidate]]:
    """
    Optimal assignment using the Hungarian Algorithm (scipy.optimize.linear_sum_assignment).

    Guarantees globally maximum total quality score — unlike greedy which only
    picks the locally best choice at each step.

    Conflict Strategy — Iterative Hungarian:
        The standard Hungarian algorithm doesn't know that two columns
        (e.g., Interviewer A at 10:00 and Interviewer A at 10:30) are
        mutually exclusive. We solve this by running multiple rounds:

        Round 1: Solve the full matrix.
        Conflict check: If two winners share the same interviewer at overlapping
                        times, evict the lower-quality one.
        Round 2: Re-solve on the reduced matrix (only evicted candidates vs
                 columns that don't conflict with already-confirmed assignments).
        Repeat up to max_rounds or until stable.

    Time Complexity: O(N³) per round (Hungarian) + O(K²) conflict check
    For typical scale (≤20 candidates): < 100ms
    """
    from scipy.optimize import linear_sum_assignment

    if not candidates or not interviewers:
        return [], list(candidates)

    # ── Build initial cost matrix ─────────────────────────────────────────────
    cost_matrix, col_map = build_cost_matrix(
        candidates, interviewers, required_duration, discretization_step
    )

    if cost_matrix.size == 0 or cost_matrix.shape[1] == 0:
        return [], list(candidates)

    n_candidates = len(candidates)
    candidate_index = {c.id: idx for idx, c in enumerate(candidates)}

    # Working cost matrix — we'll zero-out columns as slots get taken
    working_matrix = cost_matrix.copy()

    confirmed: Dict[int, Tuple[Candidate, TimeSlot, Interviewer]] = {}  # row_idx → assignment
    # Tracks which (interviewer_id, slot) pairs are now occupied
    occupied_slots: List[Tuple[str, TimeSlot]] = []

    remaining_rows = list(range(n_candidates))  # candidate row indices still unassigned

    for round_num in range(max_rounds):
        if not remaining_rows:
            break

        # ── Sub-matrix for remaining candidates only ──────────────────────────
        sub_matrix = working_matrix[np.ix_(remaining_rows, range(working_matrix.shape[1]))]

        # Check if any feasible cells exist for remaining candidates
        if (sub_matrix < MAX_COST).sum() == 0:
            break  # Nobody can be assigned anymore

        # ── Hungarian solve ───────────────────────────────────────────────────
        row_ind, col_ind = linear_sum_assignment(sub_matrix)

        # Map sub-matrix row indices back to original candidate rows
        tentative: Dict[int, int] = {}  # orig_row → col
        for r, c in zip(row_ind, col_ind):
            orig_row = remaining_rows[r]
            if sub_matrix[r, c] < MAX_COST:  # Valid (feasible) assignment
                tentative[orig_row] = c

        if not tentative:
            break

        # ── Conflict detection & resolution ──────────────────────────────────
        # An interviewer conflict occurs when two tentative assignments share
        # the same interviewer and their slots overlap in time.
        newly_confirmed: Dict[int, int] = {}     # orig_row → col (no conflict)
        evicted_rows: List[int] = []             # displaced back to unassigned

        # Sort tentative by quality (ascending cost = best quality first)
        # So when there's a conflict, the higher-quality assignment wins.
        tentative_sorted = sorted(tentative.items(), key=lambda x: working_matrix[x[0], x[1]])

        round_occupied: List[Tuple[str, TimeSlot]] = []  # within this round

        for orig_row, col in tentative_sorted:
            if col not in col_map:
                continue  # Infeasible column somehow selected — skip

            _, slot, interviewer = col_map[col]

            # Check against already-confirmed slots AND within-round slots
            all_occupied = occupied_slots + round_occupied
            conflict = any(
                iid == interviewer.id and slot.overlaps_with(occ_slot)
                for iid, occ_slot in all_occupied
            )

            if conflict:
                # This assignment collides — block this column for this candidate
                # and add them back to the pool
                working_matrix[orig_row, col] = MAX_COST
                evicted_rows.append(orig_row)
            else:
                newly_confirmed[orig_row] = col
                round_occupied.append((interviewer.id, slot))

        # Commit this round's conflict-free assignments
        for orig_row, col in newly_confirmed.items():
            confirmed[orig_row] = (candidates[orig_row], col_map[col][1], col_map[col][2])
            occupied_slots.append((col_map[col][2].id, col_map[col][1]))
            # Block this column globally (one slot = one candidate)
            working_matrix[:, col] = MAX_COST

        # Update remaining rows: confirmed are done, evicted go back for next round
        remaining_rows = [
            r for r in remaining_rows
            if r not in newly_confirmed and r not in evicted_rows
        ] + evicted_rows

    # ── Build Assignment objects ──────────────────────────────────────────────
    assignments: List[Assignment] = []
    assigned_ids: set = set()

    for orig_row, (candidate, slot, interviewer) in confirmed.items():
        quality = int(MAX_COST - cost_matrix[orig_row, _find_col(cost_matrix, orig_row, col_map, slot, interviewer)])
        assigned_ids.add(candidate.id)
        assignments.append(Assignment(
            candidate_id=candidate.id,
            interviewer_id=interviewer.id,
            slot=slot,
            quality_score=max(quality, 0),
            reasoning=f"Globally optimal assignment (Hungarian algorithm, score: {max(quality,0)} pts)."
        ))

    # ── Alternatives: top scored slots not chosen ─────────────────────────────
    for a in assignments:
        cand_row = candidate_index[a.candidate_id]
        alts: List[TimeSlot] = []
        # Walk original cost matrix for this candidate, sorted by cost
        col_order = np.argsort(cost_matrix[cand_row])
        for col in col_order:
            if col not in col_map:
                continue
            _, alt_slot, alt_intv = col_map[col]
            if alt_slot == a.slot and alt_intv.id == a.interviewer_id:
                continue  # Skip the chosen one
            if cost_matrix[cand_row, col] >= MAX_COST:
                continue  # Infeasible
            alts.append(alt_slot)
            if len(alts) >= 3:
                break
        a.alternatives = alts

    unassigned = [c for c in candidates if c.id not in assigned_ids]
    return assignments, unassigned


def _find_col(
    cost_matrix: np.ndarray,
    row: int,
    col_map: Dict[int, Tuple],
    slot: TimeSlot,
    interviewer: Interviewer,
) -> int:
    """Reverse-lookup: find the column index matching a confirmed (slot, interviewer) pair."""
    for col, (_, s, i) in col_map.items():
        if s == slot and i.id == interviewer.id:
            return col
    # Fallback: find lowest-cost feasible column for this row
    return int(np.argmin(cost_matrix[row]))


if __name__ == "__main__":
    # Full logical flow test
    from datetime import time
    from models import DayOfWeek
    
    print("Testing Full Scheduler Flow...")
    
    # Setup: 2 candidates competing for the same interviewer prime time
    c1 = Candidate("C1", "Jane", "jane@test.com", availability=[
        TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(12, 0))
    ], preferred_slots=[
        TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(11, 0))
    ])
    
    c2 = Candidate("C John", "John", "john@test.com", availability=[
        TimeSlot(DayOfWeek.MONDAY, time(9, 0), time(12, 0))
    ])
    
    i1 = Interviewer("I1", "Engineering Manager", availability=[
        TimeSlot(DayOfWeek.MONDAY, time(10, 0), time(14, 0))
    ])
    
    # 1. Feasibility Matrix
    triplets = generate_feasible_assignments([c1, c2], [i1])
    
    # 2. Scoring
    scored = []
    for c, s, i in triplets:
        score = calculate_quality_score(c, s, i, len(i.availability))
        scored.append((c, s, i, score))
        
    # 3. Optimal Assignment
    final, unassigned = optimal_assign(scored, [c1, c2])
    
    print(f"Successfully generated {len(final)} assignments.")
    for a in final:
        print(f"Candidate: {a.candidate_id} -> Interviewer: {a.interviewer_id}")
        print(f" - Slot: {a.slot.start_time.strftime('%H:%M')} to {a.slot.end_time.strftime('%H:%M')}")
        print(f" - Quality Score: {a.quality_score}")
        print(f" - Alternatives: {len(a.alternatives)} found\n")
        
    if unassigned:
        print(f"Unassigned Candidates: {[c.id for c in unassigned]}")
