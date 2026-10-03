const { spawnSync } = require("node:child_process");
const result = spawnSync(
  process.execPath,
  ["--import", "tsx", "--test", "tests/api-live.test.ts", "tests/demo.test.ts"],
  {
    stdio: "inherit",
    cwd: require("node:path").resolve(__dirname, ".."),
    env: { ...process.env, NEXT_PUBLIC_USE_MOCK: "true" },
  },
);
process.exit(result.status ?? 1);
