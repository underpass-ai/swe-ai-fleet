import { readFileSync } from "node:fs";

const source = readFileSync("src/todo.ts", "utf8");
if (source.includes("\t")) {
  throw new Error("tabs are not allowed");
}
if (source.includes(": any")) {
  throw new Error("any type is not allowed");
}

console.log("lint ok");
