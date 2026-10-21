import assert from "node:assert/strict";
import { test } from "node:test";
import { ApiError, errorMessage, genericRunError, responseError } from "../src/errors.ts";

test("session and shared budgets offer different recovery instructions", () => {
  assert.match(errorMessage("memory_budget"), /new session/);
  assert.match(errorMessage("memory_budget"), /Clearing chat does not reset/);
  assert.match(errorMessage("shared_daily_budget"), /new session will not reset/);
  assert.match(errorMessage("agent_quarantined"), /will not restore access/);
});

test("unknown errors cannot expose provider text or inherited object properties", () => {
  for (const code of [undefined, null, {}, "secret-token", "constructor", "__proto__", "toString"]) {
    assert.equal(errorMessage(code), genericRunError);
  }
});

test("HTTP errors use reviewed messages and sanitize arbitrary bodies", async () => {
  const budget = await responseError(new Response(JSON.stringify({error: "memory_budget"}), {status:409}));
  assert.ok(budget instanceof ApiError);
  assert.equal(budget.message, errorMessage("memory_budget"));
  for (const body of ['<html>secret-token</html>', '{"error":"secret-token"}', 'null']) {
    const error = await responseError(new Response(body, {status:503}));
    assert.equal(error.message, errorMessage(undefined, 503));
    assert.doesNotMatch(error.message, /secret-token/);
  }
});
