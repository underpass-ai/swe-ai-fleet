"""NATS subject definitions for Task Derivation Service."""


class TaskDerivationRequestSubjects:
    """Constants for task.derivation.requested subscriptions."""

    SUBJECT = "task.derivation.requested"
    DURABLE = "task-derivation-request-consumer"
    STREAM = "task_derivation"

