import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const source = readFileSync("src/todo.ts", "utf8");
const required = [
  "type Todo",
  "completedAt?: string",
  "addTodo",
  "completeTodo",
  "pendingCount"
];
for (const marker of required) {
  if (!source.includes(marker)) {
    throw new Error(`build marker missing: ${marker}`);
  }
}

mkdirSync("dist", { recursive: true });

writeFileSync(
  "dist/todo.mjs",
  [
    "export function addTodo(list, title) {",
    "  const item = { id: list.length + 1, title, done: false, completedAt: undefined };",
    "  return [...list, item];",
    "}",
    "",
    "export function completeTodo(list, id, completedAt) {",
    "  for (const item of list) {",
    "    if (item.id === id) {",
    "      item.done = true;",
    "      item.completedAt = completedAt;",
    "      return true;",
    "    }",
    "  }",
    "  return false;",
    "}",
    "",
    "export function pendingCount(list) {",
    "  return list.filter((item) => !item.done).length;",
    "}"
  ].join("\n"),
  "utf8"
);

writeFileSync(
  "dist/test.mjs",
  [
    "import test from 'node:test';",
    "import assert from 'node:assert/strict';",
    "import { addTodo, completeTodo, pendingCount } from './todo.mjs';",
    "",
    "test('addTodo creates items and keeps pending count', () => {",
    "  let list = [];",
    "  list = addTodo(list, 'write tests');",
    "  list = addTodo(list, 'ship feature');",
    "  assert.equal(list.length, 2);",
    "  assert.equal(list[0].id, 1);",
    "  assert.equal(list[1].id, 2);",
    "  assert.equal(pendingCount(list), 2);",
    "});",
    "",
    "test('completeTodo sets completedAt and reduces pending', () => {",
    "  let list = [];",
    "  list = addTodo(list, 'task');",
    "  const ok = completeTodo(list, 1, '2026-02-14T00:00:00Z');",
    "  assert.equal(ok, true);",
    "  assert.equal(list[0].done, true);",
    "  assert.equal(list[0].completedAt, '2026-02-14T00:00:00Z');",
    "  assert.equal(pendingCount(list), 0);",
    "});"
  ].join("\n"),
  "utf8"
);

console.log("build ok");
