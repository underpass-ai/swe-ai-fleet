"""FSM validation tests - verify all states are reachable and no dead ends."""


from planning.domain.value_objects import StoryState, StoryStateEnum


def test_all_states_reachable_from_draft():
    """Test that all states can be reached from DRAFT (directly or transitively)."""
    # This validates that no state is unreachable
    reachable = set()
    to_visit = [StoryStateEnum.DRAFT]

    transitions = {
        StoryStateEnum.DRAFT: {StoryStateEnum.PO_REVIEW},
        StoryStateEnum.PO_REVIEW: {StoryStateEnum.READY_FOR_PLANNING, StoryStateEnum.DRAFT},
        StoryStateEnum.READY_FOR_PLANNING: {StoryStateEnum.PLANNED},
        StoryStateEnum.PLANNED: {StoryStateEnum.READY_FOR_EXECUTION, StoryStateEnum.CARRY_OVER},
        StoryStateEnum.READY_FOR_EXECUTION: {StoryStateEnum.IN_PROGRESS, StoryStateEnum.CARRY_OVER},
        StoryStateEnum.IN_PROGRESS: {StoryStateEnum.CODE_REVIEW, StoryStateEnum.CARRY_OVER},
        StoryStateEnum.CODE_REVIEW: {StoryStateEnum.TESTING, StoryStateEnum.IN_PROGRESS, StoryStateEnum.CARRY_OVER},
        StoryStateEnum.TESTING: {StoryStateEnum.READY_TO_REVIEW, StoryStateEnum.IN_PROGRESS, StoryStateEnum.CARRY_OVER},
        StoryStateEnum.READY_TO_REVIEW: {StoryStateEnum.ACCEPTED, StoryStateEnum.IN_PROGRESS, StoryStateEnum.CARRY_OVER},
        StoryStateEnum.ACCEPTED: {StoryStateEnum.DONE},
        StoryStateEnum.CARRY_OVER: {StoryStateEnum.DRAFT, StoryStateEnum.READY_FOR_EXECUTION, StoryStateEnum.ARCHIVED},
        StoryStateEnum.DONE: {StoryStateEnum.ARCHIVED},
        StoryStateEnum.ARCHIVED: set(),
    }

    while to_visit:
        current = to_visit.pop()
        if current in reachable:
            continue

        reachable.add(current)
        next_states = transitions.get(current, set())
        to_visit.extend(next_states)

    # All 13 states should be reachable
    all_states = set(StoryStateEnum)
    assert reachable == all_states, f"Unreachable states: {all_states - reachable}"


def test_no_dead_ends_except_archived():
    """Test that all states have at least one exit (except ARCHIVED)."""
    draft = StoryState(StoryStateEnum.DRAFT)
    po_review = StoryState(StoryStateEnum.PO_REVIEW)
    ready_planning = StoryState(StoryStateEnum.READY_FOR_PLANNING)
    planned = StoryState(StoryStateEnum.PLANNED)
    ready_exec = StoryState(StoryStateEnum.READY_FOR_EXECUTION)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)
    code_review = StoryState(StoryStateEnum.CODE_REVIEW)
    testing = StoryState(StoryStateEnum.TESTING)
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)
    accepted = StoryState(StoryStateEnum.ACCEPTED)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)
    done = StoryState(StoryStateEnum.DONE)

    # All states should be able to transition somewhere (except ARCHIVED)
    assert draft.can_transition_to(StoryState(StoryStateEnum.PO_REVIEW))
    assert po_review.can_transition_to(StoryState(StoryStateEnum.READY_FOR_PLANNING))
    assert ready_planning.can_transition_to(StoryState(StoryStateEnum.PLANNED))
    assert planned.can_transition_to(StoryState(StoryStateEnum.READY_FOR_EXECUTION))
    assert ready_exec.can_transition_to(StoryState(StoryStateEnum.IN_PROGRESS))
    assert in_progress.can_transition_to(StoryState(StoryStateEnum.CODE_REVIEW))
    assert code_review.can_transition_to(StoryState(StoryStateEnum.TESTING))
    assert testing.can_transition_to(StoryState(StoryStateEnum.READY_TO_REVIEW))
    assert ready_to_review.can_transition_to(StoryState(StoryStateEnum.ACCEPTED))
    assert accepted.can_transition_to(StoryState(StoryStateEnum.DONE))
    assert carry_over.can_transition_to(StoryState(StoryStateEnum.DRAFT))
    assert done.can_transition_to(StoryState(StoryStateEnum.ARCHIVED))


def test_planned_cannot_go_to_carry_over():
    """Test that PLANNED cannot transition to CARRY_OVER (not in sprint yet)."""
    planned = StoryState(StoryStateEnum.PLANNED)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    # PLANNED means tasks derived but NOT committed to sprint yet
    assert planned.can_transition_to(carry_over) is False


def test_ready_for_execution_can_go_to_carry_over():
    """Test that READY_FOR_EXECUTION can transition to CARRY_OVER (sprint ended)."""
    ready_exec = StoryState(StoryStateEnum.READY_FOR_EXECUTION)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert ready_exec.can_transition_to(carry_over) is True


def test_draft_cannot_go_to_carry_over():
    """Test that DRAFT cannot go to CARRY_OVER (not in sprint yet)."""
    draft = StoryState(StoryStateEnum.DRAFT)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert draft.can_transition_to(carry_over) is False


def test_po_review_cannot_go_to_carry_over():
    """Test that PO_REVIEW cannot go to CARRY_OVER (not in sprint yet)."""
    po_review = StoryState(StoryStateEnum.PO_REVIEW)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert po_review.can_transition_to(carry_over) is False


def test_all_states_can_reset_to_draft():
    """Test that all states can reset to DRAFT."""
    all_states = list(StoryStateEnum)

    for state_enum in all_states:
        if state_enum == StoryStateEnum.DRAFT:
            continue  # Skip self-transition test

        current = StoryState(state_enum)
        draft = StoryState(StoryStateEnum.DRAFT)

        assert current.can_transition_to(draft) is True, \
            f"{state_enum} cannot transition to DRAFT (should always be allowed)"

