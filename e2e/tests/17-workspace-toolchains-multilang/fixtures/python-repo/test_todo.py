from todo import add_todo, complete_todo, pending_count


def test_add_todo_assigns_id_and_pending():
    items = []
    items = add_todo(items, "write tests")
    items = add_todo(items, "ship feature")

    assert len(items) == 2
    assert items[0].id == 1
    assert items[1].id == 2
    assert pending_count(items) == 2
    assert items[0].completed_at is None


def test_complete_todo_sets_completed_at():
    items = []
    items = add_todo(items, "task")

    assert complete_todo(items, 1, "2026-02-14T00:00:00Z") is True
    assert items[0].done is True
    assert items[0].completed_at == "2026-02-14T00:00:00Z"
    assert pending_count(items) == 0
