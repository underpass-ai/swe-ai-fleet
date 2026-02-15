export type Todo = {
  id: number;
  title: string;
  done: boolean;
  completedAt?: string;
};

export function addTodo(list: Todo[], title: string): Todo[] {
  const item: Todo = {
    id: list.length + 1,
    title,
    done: false
  };
  return [...list, item];
}

export function completeTodo(list: Todo[], id: number, completedAt: string): boolean {
  for (const item of list) {
    if (item.id === id) {
      item.done = true;
      item.completedAt = completedAt;
      return true;
    }
  }
  return false;
}

export function pendingCount(list: Todo[]): number {
  return list.filter((item) => !item.done).length;
}
