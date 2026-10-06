import { task } from "@trigger.dev/sdk";

export const privateAiRetryProbe = task({
  id: "private-ai-retry-probe",
  maxDuration: 60,
  retry: { maxAttempts: 3, minTimeoutInMs: 1_000, maxTimeoutInMs: 5_000, factor: 2, randomize: false },
  run: async (payload: { failUntilAttempt?: number; message?: string } = {}, { ctx }) => {
    const failUntilAttempt = payload.failUntilAttempt ?? 0;
    if (!Number.isInteger(failUntilAttempt) || failUntilAttempt < 0 || failUntilAttempt > 2) {
      throw new Error("failUntilAttempt must be an integer from 0 to 2");
    }

    const attempt = ctx.attempt.number;
    console.log("Private AI retry probe", { attempt, failUntilAttempt });
    if (attempt <= failUntilAttempt) {
      throw new Error(`Intentional retry probe failure on attempt ${attempt}`);
    }

    return {
      status: "ok",
      message: payload.message ?? "Private AI retry probe succeeded",
      attempt,
      checkedAt: new Date().toISOString(),
    };
  },
});
