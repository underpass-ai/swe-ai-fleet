"""Unit tests for CARRY_OVER state (sprint closure handling)."""


from planning.domain.value_objects import StoryState, StoryStateEnum


def test_in_progress_to_carry_over_is_valid():
    """Test valid transition: IN_PROGRESS → CARRY_OVER (sprint ended)."""
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert in_progress.can_transition_to(carry_over) is True


def test_code_review_to_carry_over_is_valid():
    """Test valid transition: CODE_REVIEW → CARRY_OVER (sprint ended)."""
    code_review = StoryState(StoryStateEnum.CODE_REVIEW)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert code_review.can_transition_to(carry_over) is True


def test_testing_to_carry_over_is_valid():
    """Test valid transition: TESTING → CARRY_OVER (sprint ended)."""
    testing = StoryState(StoryStateEnum.TESTING)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert testing.can_transition_to(carry_over) is True


def test_ready_to_review_to_carry_over_is_valid():
    """Test valid transition: READY_TO_REVIEW → CARRY_OVER (sprint ended)."""
    ready_to_review = StoryState(StoryStateEnum.READY_TO_REVIEW)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    assert ready_to_review.can_transition_to(carry_over) is True


def test_carry_over_to_draft_is_valid():
    """Test valid transition: CARRY_OVER → DRAFT (reevaluate)."""
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)
    draft = StoryState(StoryStateEnum.DRAFT)

    assert carry_over.can_transition_to(draft) is True


def test_carry_over_to_ready_for_execution_is_valid():
    """Test valid transition: CARRY_OVER → READY_FOR_EXECUTION (continue)."""
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)
    ready_exec = StoryState(StoryStateEnum.READY_FOR_EXECUTION)

    assert carry_over.can_transition_to(ready_exec) is True


def test_carry_over_to_archived_is_valid():
    """Test valid transition: CARRY_OVER → ARCHIVED (cancel)."""
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)
    archived = StoryState(StoryStateEnum.ARCHIVED)

    assert carry_over.can_transition_to(archived) is True


def test_accepted_to_carry_over_is_invalid():
    """Test that ACCEPTED cannot go to CARRY_OVER."""
    accepted = StoryState(StoryStateEnum.ACCEPTED)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    # ACCEPTED stories are complete, should go to DONE not CARRY_OVER
    assert accepted.can_transition_to(carry_over) is False


def test_draft_to_carry_over_is_invalid():
    """Test that DRAFT cannot go to CARRY_OVER."""
    draft = StoryState(StoryStateEnum.DRAFT)
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)

    # DRAFT stories haven't started, can't be carried over
    assert draft.can_transition_to(carry_over) is False


def test_carry_over_to_in_progress_is_invalid():
    """Test that CARRY_OVER cannot directly go back to IN_PROGRESS."""
    carry_over = StoryState(StoryStateEnum.CARRY_OVER)
    in_progress = StoryState(StoryStateEnum.IN_PROGRESS)

    # Must either reevaluate (DRAFT) or re-queue (READY_FOR_EXECUTION)
    assert carry_over.can_transition_to(in_progress) is False

