import {
  BrowserCacheLocation,
  InteractionRequiredAuthError,
  PublicClientApplication,
  type AccountInfo,
  type IPublicClientApplication,
} from "@azure/msal-browser";

export class SignInRequiredError extends Error {
  constructor() {
    super("Your sign-in needs to be renewed. Sign in again to continue.");
  }
}

export function readWebConfig(env: Record<string, string | undefined>, origin: string) {
  const tenantId = env.VITE_ENTRA_TENANT_ID?.trim();
  const clientId = env.VITE_ENTRA_CLIENT_ID?.trim();
  const apiId = env.VITE_ENTRA_API_CLIENT_ID?.trim();
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (![tenantId, clientId, apiId].every((value) => value && uuid.test(value))) {
    throw new Error("Entra sign-in is not configured. Set the web app's VITE_ENTRA_TENANT_ID, VITE_ENTRA_CLIENT_ID, and VITE_ENTRA_API_CLIENT_ID.");
  }
  const endpoint = (env.VITE_AGENT_API_URL?.trim() || "/api").replace(/\/$/, "");
  const target = new URL(endpoint, origin);
  if (target.username || target.password || target.search || target.hash ||
      (target.protocol !== "https:" && !(target.protocol === "http:" &&
        ["127.0.0.1", "localhost"].includes(target.hostname)))) {
    throw new Error("The agent API address must use HTTPS or a local development address.");
  }
  return { tenantId: tenantId!, clientId: clientId!, scope: `api://${apiId}/Chat.Access`, endpoint,
    redirectUri: `${origin}/redirect.html` };
}

export type WebConfig = ReturnType<typeof readWebConfig>;

export class EntraAuth {
  private readonly client: IPublicClientApplication;
  private readonly config: WebConfig;

  constructor(config: WebConfig, client?: IPublicClientApplication) {
    this.config = config;
    this.client = client ?? new PublicClientApplication({
      auth: {
        clientId: config.clientId,
        authority: `https://login.microsoftonline.com/${config.tenantId}`,
        redirectUri: config.redirectUri,
      },
      cache: { cacheLocation: BrowserCacheLocation.MemoryStorage },
    });
  }

  async initialize() {
    await this.client.initialize();
  }

  async signIn(): Promise<AccountInfo> {
    const result = await this.client.loginPopup({ scopes: [this.config.scope], prompt: "select_account" });
    if (!result.account || !result.accessToken) throw new SignInRequiredError();
    this.client.setActiveAccount(result.account);
    return result.account;
  }

  async getAccessToken(account: AccountInfo): Promise<string> {
    try {
      const result = await this.client.acquireTokenSilent({ account, scopes: [this.config.scope] });
      if (!result.accessToken) throw new SignInRequiredError();
      return result.accessToken;
    } catch (error) {
      if (error instanceof InteractionRequiredAuthError) throw new SignInRequiredError();
      throw error;
    }
  }

  async signOut(account: AccountInfo) {
    try {
      await this.client.logoutPopup({ account, postLogoutRedirectUri: this.config.redirectUri });
    } finally {
      await this.client.clearCache({ account });
    }
  }
}
