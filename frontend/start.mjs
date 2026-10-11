// `npm start`: builds the website, then starts the Python backend (which serves it).
import { spawn, spawnSync } from "node:child_process";

const candidates = process.platform === "win32" ? ["python", "py", "python3"] : ["python3", "python"];
const python = candidates.find((c) => spawnSync(c, ["--version"], { stdio: "ignore" }).status === 0);
if (!python) {
  console.error("Python was not found. Install Python 3.10+ and try again.");
  process.exit(1);
}
const child = spawn(python, ["main.py"], { cwd: new URL("..", import.meta.url), stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
process.on("SIGINT", () => child.kill("SIGINT"));
