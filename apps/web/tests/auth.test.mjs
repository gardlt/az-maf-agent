import assert from "node:assert/strict";
import { test } from "node:test";
import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { EntraAuth, readWebConfig, SignInRequiredError } from "../src/auth.ts";

const env = {
  VITE_ENTRA_TENANT_ID: "c57afb80-6b3d-4bae-a466-e4d217bcb4a2",
  VITE_ENTRA_CLIENT_ID: "a5d930a1-3d30-4d14-83d6-6992cb1bf626",
  VITE_ENTRA_API_CLIENT_ID: "67b8f4b9-71e4-4815-b8b5-a0a4fd7bc0d7",
};
const config = readWebConfig(env, "http://127.0.0.1:5173");
const account = { homeAccountId: "user-a", username: "a@example.test" };

test("missing configuration and unsafe API endpoints fail before sign-in", () => {
  assert.throws(() => readWebConfig({}, "http://localhost:5173"));
  for (const endpoint of ["http://external.example/api", "javascript:alert(1)", "https://user:pass@example.test", "https://example.test/?token=secret"]) {
    assert.throws(() => readWebConfig({ ...env, VITE_AGENT_API_URL: endpoint }, "http://localhost:5173"));
  }
});

test("sign-in requests the API delegated scope and binds the returned account", async () => {
  let active;
  const auth = new EntraAuth(config, {
    async loginPopup(request) {
      assert.deepEqual(request.scopes, [config.scope]);
      return { account, accessToken: "fixture-only" };
    },
    setActiveAccount(value) { active = value; },
  });
  assert.equal(await auth.signIn(), account);
  assert.equal(active, account);
});

test("every token request uses the selected user and can receive a renewed token", async () => {
  let calls = 0;
  const auth = new EntraAuth(config, {
    async acquireTokenSilent(request) {
      assert.equal(request.account, account);
      assert.deepEqual(request.scopes, [config.scope]);
      return { accessToken: `fixture-token-${++calls}` };
    },
  });
  assert.equal(await auth.getAccessToken(account), "fixture-token-1");
  assert.equal(await auth.getAccessToken(account), "fixture-token-2");
});

test("expired consent requires explicit sign-in instead of dispatching an API call", async () => {
  const auth = new EntraAuth(config, {
    async acquireTokenSilent() { throw new InteractionRequiredAuthError("login_required"); },
  });
  await assert.rejects(auth.getAccessToken(account), SignInRequiredError);
});

test("an empty access token is never returned for an Authorization header", async () => {
  const auth = new EntraAuth(config, {
    async acquireTokenSilent() { return { accessToken: "" }; },
  });
  await assert.rejects(auth.getAccessToken(account), SignInRequiredError);
});

test("local credentials are cleared even when the sign-out popup fails", async () => {
  let cleared;
  const auth = new EntraAuth(config, {
    async logoutPopup() { throw new Error("popup_closed"); },
    async clearCache(request) { cleared = request.account; },
  });
  await assert.rejects(auth.signOut(account));
  assert.equal(cleared, account);
});
