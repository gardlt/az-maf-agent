// Only reviewed messages reach the UI; server/provider text may contain sensitive data.
const messages: Record<string, string> = {
  memory_budget: "This session has reached its memory-operation limit. Disconnect and connect to start a new session. Clearing chat does not reset usage limits.",
  tool_budget: "This session has reached its tool-use limit. Disconnect and connect to start a new session. Clearing chat does not reset usage limits.",
  shared_daily_budget: "The agent has reached its daily usage limit. Try again after the budget window resets. Starting a new session will not reset this limit.",
  shared_run_budget: "This request exceeds the run budget. Try a shorter or simpler request.",
  shared_tool_budget: "This request reached its tool-use limit. Try a narrower request.",
  shared_memory_budget: "This request reached its memory-operation limit. Try a simpler request.",
  context_limit: "This conversation is too long for the model. Clear the chat or shorten your message. Clearing chat does not reset usage limits.",
  busy: "A request is already running in this session. Wait for it to finish before trying again.",
  shared_concurrency: "The agent is handling too many requests. Wait a moment and try again.",
  session_not_found: "This session is unavailable or has expired. Disconnect and connect to start a new session.",
  stale_revision: "This session changed in another request. Disconnect and resume it using its session ID before retrying.",
  session_changed: "This session changed while the request was running. Disconnect and resume it before retrying.",
  global_stop: "The agent has been paused by an operator. Contact the administrator before retrying.",
  agent_quarantined: "The agent has been quarantined by a security control. Contact the administrator. Starting a new session will not restore access.",
  tool_not_allowed: "This action is not allowed by the agent's tool policy. Ask for a supported movie lookup instead.",
  action_forbidden: "This action is not permitted. Ask for a supported movie lookup instead.",
  capability_disabled: "This capability is disabled by policy. Contact the administrator if you need access.",
  approval_required: "This action requires operator approval. Contact the administrator.",
  provider_rejected: "The model service could not complete this request. Try again later or contact the administrator if it continues.",
  tool_service_unavailable: "The movie lookup service is unavailable. Try again later.",
  agent_token_unavailable: "The agent could not authenticate to a required service. Contact the administrator.",
  agent_token_invalid: "The agent could not authenticate to a required service. Contact the administrator.",
};

export const genericRunError = "The agent could not complete this request. Try again later. If it continues, contact the administrator.";

export function errorMessage(code: unknown, status?: number): string {
  if (typeof code === "string" && Object.hasOwn(messages, code)) return messages[code];
  if (status === 401) return "Your sign-in is no longer valid. Sign out and sign in again.";
  if (status === 403) return "Your account is not permitted to perform this action. Contact the administrator.";
  if (status === 429) return "A usage or capacity limit has been reached. Wait before retrying; contact the administrator if it continues.";
  if (status === 502 || status === 503 || status === 504) return "The agent service is temporarily unavailable. Try again later.";
  return genericRunError;
}

export class ApiError extends Error {}

export async function responseError(response: Response): Promise<ApiError> {
  let code: unknown;
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "error" in body) code = body.error;
  } catch {
    // Proxy errors can be HTML; never render their bodies.
  }
  return new ApiError(errorMessage(code, response.status));
}
