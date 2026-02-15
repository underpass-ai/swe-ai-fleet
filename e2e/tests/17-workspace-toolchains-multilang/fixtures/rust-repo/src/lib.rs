#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Todo {
    pub id: usize,
    pub title: String,
    pub done: bool,
    pub completed_at: Option<String>,
}

pub fn add_todo(list: &mut Vec<Todo>, title: &str) -> usize {
    let next_id = list.len() + 1;
    list.push(Todo {
        id: next_id,
        title: title.to_string(),
        done: false,
        completed_at: None,
    });
    next_id
}

pub fn complete_todo(list: &mut [Todo], id: usize, completed_at: &str) -> bool {
    for item in list {
        if item.id == id {
            item.done = true;
            if item.completed_at.is_none() {
                item.completed_at = Some(completed_at.to_string());
            }
            return true;
        }
    }
    false
}

pub fn pending_count(list: &[Todo]) -> usize {
    list.iter().filter(|item| !item.done).count()
}

#[cfg(test)]
mod tests {
    use super::{add_todo, complete_todo, pending_count, Todo};

    #[test]
    fn add_todo_assigns_id_and_keeps_pending() {
        let mut list: Vec<Todo> = Vec::new();
        assert_eq!(add_todo(&mut list, "write tests"), 1);
        assert_eq!(add_todo(&mut list, "ship feature"), 2);
        assert_eq!(list.len(), 2);
        assert_eq!(pending_count(&list), 2);
        assert_eq!(list[0].completed_at, None);
    }

    #[test]
    fn complete_todo_sets_completed_at() {
        let mut list = vec![Todo {
            id: 1,
            title: String::from("task"),
            done: false,
            completed_at: None,
        }];
        assert!(complete_todo(&mut list, 1, "2026-02-14T00:00:00Z"));
        assert!(list[0].done);
        assert_eq!(
            list[0].completed_at.as_deref(),
            Some("2026-02-14T00:00:00Z")
        );
        assert_eq!(pending_count(&list), 0);
    }
}
