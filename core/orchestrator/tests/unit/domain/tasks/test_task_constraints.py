from core.orchestrator.domain.tasks.task_constraints import TaskConstraints


class TestTaskConstraints:
    def test_get_rubric_returns_rubric(self) -> None:
        rubric = {"criteria": "quality"}
        constraints = TaskConstraints(rubric=rubric, architect_rubric={})

        assert constraints.get_rubric() == rubric

    def test_get_architect_rubric_returns_architect_rubric(self) -> None:
        architect_rubric = {"k": 5}
        constraints = TaskConstraints(rubric={}, architect_rubric=architect_rubric)

        assert constraints.get_architect_rubric() == architect_rubric

    def test_get_cluster_spec_returns_cluster_spec_when_present(self) -> None:
        cluster_spec = {"nodes": 3}
        constraints = TaskConstraints(
            rubric={},
            architect_rubric={},
            cluster_spec=cluster_spec,
        )

        assert constraints.get_cluster_spec() == cluster_spec

    def test_get_cluster_spec_returns_none_when_absent(self) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={})

        assert constraints.get_cluster_spec() is None

    def test_get_k_value_returns_k_from_architect_rubric(self) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={"k": 7})

        assert constraints.get_k_value() == 7

    def test_get_k_value_defaults_to_3_when_k_not_present(self) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={})

        assert constraints.get_k_value() == 3

    def test_to_dict_includes_all_fields_when_present(self) -> None:
        constraints = TaskConstraints(
            rubric={"criteria": "quality"},
            architect_rubric={"k": 5},
            cluster_spec={"nodes": 3},
            additional_constraints={"timeout": 60},
        )

        as_dict = constraints.to_dict()

        assert as_dict["rubric"] == {"criteria": "quality"}
        assert as_dict["architect_rubric"] == {"k": 5}
        assert as_dict["cluster_spec"] == {"nodes": 3}
        assert as_dict["timeout"] == 60

    def test_to_dict_omits_none_fields(self) -> None:
        constraints = TaskConstraints(rubric={}, architect_rubric={})

        as_dict = constraints.to_dict()

        assert "cluster_spec" not in as_dict
        assert "additional_constraints" not in as_dict

    def test_from_dict_creates_constraints_with_all_fields(self) -> None:
        data = {
            "rubric": {"criteria": "quality"},
            "architect_rubric": {"k": 5},
            "cluster_spec": {"nodes": 3},
            "timeout": 60,
        }

        constraints = TaskConstraints.from_dict(data)

        assert constraints.rubric == {"criteria": "quality"}
        assert constraints.architect_rubric == {"k": 5}
        assert constraints.cluster_spec == {"nodes": 3}
        assert constraints.additional_constraints == {"timeout": 60}

    def test_from_dict_handles_missing_fields(self) -> None:
        data: dict[str, object] = {}

        constraints = TaskConstraints.from_dict(data)

        assert constraints.rubric == {}
        assert constraints.architect_rubric == {}
        assert constraints.cluster_spec is None
        assert constraints.additional_constraints is None
