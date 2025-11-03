"""Unit tests for PLANNED and READY_FOR_EXECUTION states in FSM."""


from planning.domain.value_objects import StoryState, StoryStateEnum


def test_ready_for_planning_to_planned_is_valid():
    """Test valid transition: READY_FOR_PLANNING → PLANNED."""
    ready = StoryState(StoryStateEnum.READY_FOR_PLANNING)
    planned = StoryState(StoryStateEnum.PLANNED)

    assert ready.can_transition_to(planned) is True


def test_planned_to_ready_for_execution_is_valid():
    """Test valid transition: PLANNED → READY_FOR_EXECUTION."""
    planned = StoryState(StoryStateEnum.PLANNED)
    ready_exec = StoryState(StoryStateEnum.READY_FOR_EXECUTION)

    assert planned.can_transition_to(ready_exec) is True


def test_ready_for_execution_to_in_progress_is_valid():
    """Test valid transition: READY_FOR_EXECUTION → IN_PROGRESS."""
    ready_exec = StoryState(StoryStateEnum.READY_FOR_EXECUTION)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    assert ready_exec.can_transition_to(in_progress) is True


def test_planned_to_in_progress_is_invalid():
    """Test that PLANNED cannot skip READY_FOR_EXECUTION."""
    planned = StoryState(StoryStateEnum.PLANNED)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    # Must go through READY_FOR_EXECUTION first
    assert planned.can_transition_to(in_progress) is False


def test_ready_for_planning_to_in_progress_is_invalid():
    """Test that READY_FOR_PLANNING cannot skip PLANNED state."""
    ready = StoryState(StoryStateEnum.READY_FOR_PLANNING)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    # Must go through PLANNED state first
    assert ready.can_transition_to(in_progress) is False


def test_planned_to_draft_is_valid():
    """Test that PLANNED can reset to DRAFT."""
    planned = StoryState(StoryStateEnum.PLANNED)
    draft = StoryState(StoryStateEnum.DRAFT)

    # Reset to DRAFT is always allowed
    assert planned.can_transition_to(draft) is True


def test_in_progress_to_code_review_is_valid():
    """Test valid transition: IN_PROGRESS → CODE_REVIEW."""
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)
    code_review = StoryState(StoryStateEnum.CODE_REVIEW)

    assert in_progress.can_transition_to(code_review) is True


def test_testing_to_ready_to_review_is_valid():
    """Test valid transition: TESTING → READY_TO_REVIEW."""
    testing = StoryState(StoryStateEnum.TESTING)
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)

    assert testing.can_transition_to(ready_to_review) is True


def test_ready_to_review_to_accepted_is_valid():
    """Test valid transition: READY_TO_REVIEW → ACCEPTED."""
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)
    accepted = StoryState(StoryStateEnum.ACCEPTED)

    assert ready_to_review.can_transition_to(accepted) is True


def test_accepted_to_done_is_valid():
    """Test valid transition: ACCEPTED → DONE."""
    accepted = StoryState(StoryStateEnum.ACCEPTED)
    done = StoryState(StoryStateEnum.DONE)

    assert accepted.can_transition_to(done) is True


def test_ready_to_review_to_done_is_invalid():
    """Test that READY_TO_REVIEW cannot skip ACCEPTED."""
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)
    done = StoryState(StoryStateEnum.DONE)

    # Must go through ACCEPTED first
    assert ready_to_review.can_transition_to(done) is False


def test_ready_to_review_to_in_progress_is_valid():
    """Test valid transition: READY_TO_REVIEW → IN_PROGRESS (PO/QA rejected)."""
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    # PO/QA can reject and send back for rework
    assert ready_to_review.can_transition_to(in_progress) is True


def test_testing_to_done_is_invalid():
    """Test that TESTING cannot skip to DONE."""
    testing = StoryState(StoryStateEnum.TESTING)
    done = StoryState(StoryStateEnum.DONE)

    # Must go through READY_TO_REVIEW → ACCEPTED before DONE
    assert testing.can_transition_to(done) is False


def test_testing_to_accepted_is_invalid():
    """Test that TESTING cannot skip READY_TO_REVIEW."""
    testing = StoryState(StoryStateEnum.TESTING)
    accepted = StoryState(StoryStateEnum.ACCEPTED)

    # Must go through READY_TO_REVIEW first
    assert testing.can_transition_to(accepted) is False


def test_planned_state_predicates():
    """Test state checking for PLANNED."""
    planned = StoryState(StoryStateEnum.PLANNED)

    assert planned.is_draft() is False
    assert planned.is_done() is False
    assert planned.is_in_progress() is False

