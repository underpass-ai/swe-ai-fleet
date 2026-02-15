import { readFileSync } from "node:fs";

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
    throw new Error(`typecheck marker missing: ${marker}`);
  }
}

console.log("typecheck ok");
