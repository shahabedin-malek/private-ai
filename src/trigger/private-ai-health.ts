import { execFile } from "node:child_process";
import { access, constants, statfs } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { schedules, task } from "@trigger.dev/sdk";

const execFileAsync = promisify(execFile);
const configuredRoot = process.env.PRIVATE_AI_PROJECT_ROOT ?? process.cwd();
const projectRoot = path.resolve(configuredRoot);
const expectedDirectories = [".progress", "data", "data/database", "data/manifests", "scripts"];

async function pathExists(target: string): Promise<boolean> {
  try {
    await access(target, constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

async function gitStatus(): Promise<{ available: boolean; changedTrackedFiles?: number } | null> {
  try {
    const { stdout } = await execFileAsync("git", ["status", "--porcelain", "--untracked-files=no"], {
      cwd: projectRoot,
      timeout: 3_000,
      maxBuffer: 4_096,
    });
    return { available: true, changedTrackedFiles: stdout.trim() ? stdout.trim().split("\n").length : 0 };
  } catch {
    return null;
  }
}

async function filesystemSpace(target: string): Promise<{ availableBytes: number; freeBytes: number } | null> {
  try {
    const usage = await statfs(target);
    return {
      availableBytes: Number(usage.bavail) * Number(usage.bsize),
      freeBytes: Number(usage.bfree) * Number(usage.bsize),
    };
  } catch {
    return null;
  }
}

export function assessHealthStatus(input: {
  rootExists: boolean;
  configExists: boolean;
  databaseExists: boolean;
  scratchExists: boolean;
  requiredDirectoriesExist: boolean;
}): "ok" | "degraded" {
  return input.rootExists && input.configExists && input.databaseExists && input.scratchExists && input.requiredDirectoriesExist
    ? "ok"
    : "degraded";
}

export async function inspectHealth(environment: string) {
  const databasePath = path.join(projectRoot, "data/database/private_ai_corpus.sqlite");
  const scratchPath = process.env.PRIVATE_AI_SCRATCH_ROOT ?? "/home/chris/data-processing";
  const [rootExists, directories, databaseExists, configExists, git, scratchExists, projectSpace, scratchSpace] = await Promise.all([
    pathExists(projectRoot),
    Promise.all(expectedDirectories.map(async (directory) => ({
      path: directory,
      exists: await pathExists(path.join(projectRoot, directory)),
    }))),
    pathExists(databasePath),
    pathExists(path.join(projectRoot, "trigger.config.ts")),
    gitStatus(),
    pathExists(scratchPath),
    filesystemSpace(projectRoot),
    filesystemSpace(scratchPath),
  ]);

  return {
    status: assessHealthStatus({
      rootExists,
      configExists,
      databaseExists,
      scratchExists,
      requiredDirectoriesExist: directories.every(({ exists }) => exists),
    }),
    project: "private-ai",
    environment,
    checkedAt: new Date().toISOString(),
    runtime: { node: process.version, platform: process.platform, architecture: process.arch },
    host: { cpuCount: os.cpus().length, totalMemoryBytes: os.totalmem() },
    paths: {
      rootExists,
      directories,
      databaseExists,
      triggerConfigExists: configExists,
      gitStatus: git,
      project: { exists: rootExists, ...projectSpace },
      scratch: { configured: true, exists: scratchExists, ...scratchSpace },
    },
    execution: {
      triggerSecretConfigured: Boolean(process.env.TRIGGER_SECRET_KEY),
      mode: "read-only health check; no corpus mutation",
    },
  };
}

export const privateAiHealth = task({
  id: "private-ai-health",
  maxDuration: 60,
  run: async (_payload, { ctx }) => inspectHealth(ctx.environment.type),
});

// Declarative schedule is deliberately low-frequency; attach/sync only via Trigger.dev.
export const privateAiScheduledHealth = schedules.task({
  id: "private-ai-scheduled-health",
  cron: "0 */6 * * *",
  maxDuration: 60,
  run: async (payload, { ctx }) => ({
    schedule: { timestamp: payload.timestamp.toISOString(), lastTimestamp: payload.lastTimestamp?.toISOString() ?? null },
    health: await inspectHealth(ctx.environment.type),
  }),
});
