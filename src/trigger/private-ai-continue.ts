import { execFile } from "node:child_process";
import { access, constants, readFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { task } from "@trigger.dev/sdk";

const execFileAsync = promisify(execFile);
const projectRoot = path.resolve(process.env.PRIVATE_AI_PROJECT_ROOT ?? process.cwd());
const scratchRoot = path.resolve(process.env.PRIVATE_AI_SCRATCH_ROOT ?? "/home/chris/data-processing");
const progressFiles = [
  ".progress/MASTER_PROGRESS.md",
  ".progress/CONTINUATION_PROMPT.md",
  ".progress/TASK_QUEUE.md",
  ".progress/TASK_STATUS.md",
  ".progress/CURRENT_TASK.md",
  ".progress/SESSION_LOG.md",
  ".progress/ERRORS.md",
];

export function validateContinuationAction(
  action: string,
  environment: string,
  parserAvailable: boolean,
  scratchWritable: boolean,
): { allowed: boolean; reason?: string } {
  if (action !== "inspect" && action !== "parse-batch") {
    return { allowed: false, reason: "Unsupported continuation action" };
  }
  if (action === "inspect") return { allowed: true };
  if (environment !== "DEVELOPMENT") {
    return { allowed: false, reason: "parse-batch is local-development-only; cloud Trigger.dev cannot access the private corpus/SSD" };
  }
  if (!parserAvailable) {
    return { allowed: false, reason: "Local Private AI parser is not available under PRIVATE_AI_PROJECT_ROOT" };
  }
  if (!scratchWritable) {
    return { allowed: false, reason: "The configured local SSD scratch root is unavailable or not writable" };
  }
  return { allowed: true };
}

async function readableFile(relativePath: string): Promise<boolean> {
  try {
    await access(path.join(projectRoot, relativePath), constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

export const privateAiContinue = task({
  id: "private-ai-continue",
  maxDuration: 180,
  retry: { maxAttempts: 2, minTimeoutInMs: 1_000, maxTimeoutInMs: 10_000, factor: 2, randomize: true },
  run: async (payload: { action?: "inspect" | "parse-batch" } = {}, { ctx }) => {
    const action = payload.action ?? "inspect";
    const progress = await Promise.all(progressFiles.map(async (file) => ({
      file,
      exists: await readableFile(file),
    })));
    const continuationPath = path.join(projectRoot, ".progress/CONTINUATION_PROMPT.md");
    const continuation = (await readableFile(".progress/CONTINUATION_PROMPT.md"))
      ? await readFile(continuationPath, "utf8")
      : "";
    const nextAction = continuation.match(/\*\*NEXT EXACT ACTION:\*\*\s*([^\n]+)/)?.[1]?.trim()
      ?? continuation.match(/\*\*NEXT EXACT COMMAND:\*\*\s*`([^`]+)`/)?.[1]?.trim()
      ?? null;

    const result: Record<string, unknown> = {
      status: "inspected",
      action,
      project: "private-ai",
      checkedAt: new Date().toISOString(),
      progress,
      persistedNextAction: nextAction ? "available" : null,
      executionBackend: "trigger.dev",
      host: { node: process.version, platform: process.platform, architecture: process.arch, cpuCount: os.cpus().length },
    };

    const parserAvailable = await readableFile("scripts/corpus_parse.py");
    let scratchWritable = false;
    try {
      await access(scratchRoot, constants.R_OK | constants.W_OK);
      scratchWritable = true;
    } catch {
      // Fail closed; the path itself is never included in the error or output.
    }
    const actionCheck = validateContinuationAction(
      action,
      ctx.environment.type,
      parserAvailable,
      scratchWritable,
    );
    if (!actionCheck.allowed) throw new Error(actionCheck.reason);
    if (action === "inspect") return result;

    const { stdout, stderr } = await execFileAsync("python3", [
      "scripts/corpus_parse.py",
      "--project", projectRoot,
      "--scratch-root", scratchRoot,
      "--limit", "100",
      "--max-mb", "2",
      "--max-wall-seconds", "60",
    ], {
      cwd: projectRoot,
      timeout: 120_000,
      maxBuffer: 64 * 1024,
      env: {
        ...process.env,
        TMPDIR: path.join(scratchRoot, "private-ai-tmp", "tmp"),
        TEMP: path.join(scratchRoot, "private-ai-tmp", "tmp"),
        TMP: path.join(scratchRoot, "private-ai-tmp", "tmp"),
      },
    });

    result.status = "processed";
    // Parser output can include local paths and source identifiers; keep only safe execution facts.
    result.parser = {
      completed: true,
      summaryAvailable: stdout.trim().length > 0,
      diagnosticAvailable: stderr.trim().length > 0,
    };
    return result;
  },
});
