import assert from "node:assert/strict";
import test from "node:test";
import { assessHealthStatus } from "../src/trigger/private-ai-health.ts";
import { validateContinuationAction } from "../src/trigger/private-ai-continue.ts";

test("health is ok only when all required project and scratch checks pass", () => {
  const healthy = {
    rootExists: true,
    configExists: true,
    databaseExists: true,
    scratchExists: true,
    requiredDirectoriesExist: true,
  };

  assert.equal(assessHealthStatus(healthy), "ok");
  for (const key of Object.keys(healthy) as (keyof typeof healthy)[]) {
    assert.equal(assessHealthStatus({ ...healthy, [key]: false }), "degraded", `${key} must degrade health`);
  }
});

test("continuation inspection is safe in both local and cloud environments", () => {
  assert.deepEqual(validateContinuationAction("inspect", "DEVELOPMENT", false, false), { allowed: true });
  assert.deepEqual(validateContinuationAction("inspect", "PRODUCTION", false, false), { allowed: true });
});

test("parser continuation is rejected outside development", () => {
  const result = validateContinuationAction("parse-batch", "PRODUCTION", true, true);
  assert.equal(result.allowed, false);
  assert.match(result.reason ?? "", /local-development-only/);
});

test("parser continuation fails closed without parser or writable scratch", () => {
  assert.equal(validateContinuationAction("parse-batch", "DEVELOPMENT", false, true).allowed, false);
  assert.equal(validateContinuationAction("parse-batch", "DEVELOPMENT", true, false).allowed, false);
  assert.deepEqual(validateContinuationAction("parse-batch", "DEVELOPMENT", true, true), { allowed: true });
});

test("unsupported continuation actions are rejected", () => {
  assert.equal(validateContinuationAction("anything-else", "DEVELOPMENT", true, true).allowed, false);
});
