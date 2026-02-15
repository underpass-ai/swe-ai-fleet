#include <stdio.h>

typedef struct Todo {
    int id;
    const char *title;
    int done;
    const char *completed_at;
} Todo;

int main(void) {
    Todo item = {1, "write tests", 0, NULL};
    printf("todo:%d:%s:%d\n", item.id, item.title, item.done);
    return 0;
}
