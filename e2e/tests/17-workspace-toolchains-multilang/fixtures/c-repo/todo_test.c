#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct Todo {
    int id;
    const char *title;
    int done;
    const char *completed_at;
} Todo;

static void complete_todo(Todo *item, const char *completed_at) {
    item->done = 1;
    item->completed_at = completed_at;
}

int main(void) {
    Todo item = {1, "task", 0, NULL};
    complete_todo(&item, "2026-02-14T00:00:00Z");
    assert(item.done == 1);
    assert(strcmp(item.completed_at, "2026-02-14T00:00:00Z") == 0);
    printf("c tests passed\n");
    return 0;
}
