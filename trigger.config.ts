import { defineConfig } from "@trigger.dev/sdk";

export default defineConfig({
  project: "proj_ldxacbqsdsakdqozeqdi",
  runtime: "node-24",
  logLevel: "log",
  // Keep the initial default bounded; increase per-task only after workload review.
  maxDuration: 900,
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 10000,
      factor: 2,
      randomize: true,
    },
  },
  dirs: ["./src/trigger"],
});
