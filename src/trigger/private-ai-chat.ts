import { chat } from "@trigger.dev/sdk/ai";
import { stepCountIs } from "ai";
import { anthropic } from "@ai-sdk/anthropic";

export const privateAiChat = chat.agent({
  id: "private-ai-chat",
  uiMessageStreamOptions: {
    onError: () => "The chat request could not be completed.",
  },
  run: async ({ messages, signal, streamText }) => {
    if (!process.env.ANTHROPIC_API_KEY) {
      throw new Error("ANTHROPIC_API_KEY is required to run this optional Anthropic chat task");
    }

    return streamText({
      model: anthropic("claude-sonnet-4-5"),
      messages,
      abortSignal: signal,
      stopWhen: stepCountIs(15),
    });
  },
});
