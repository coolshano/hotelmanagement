import { test as base, request as playwrightRequest, APIRequestContext } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://127.0.0.1:8000";
const TEST_USERNAME = process.env.TEST_USERNAME ?? "test@example.com";
const TEST_PASSWORD = process.env.TEST_PASSWORD ?? "P@ssw0rd123";

type ApiFixtures = {
  unauthenticatedRequest: APIRequestContext;
  authenticatedRequest: APIRequestContext;
  adminRequest: APIRequestContext;
};

async function authenticatedContext(email: string, password: string): Promise<APIRequestContext> {
  const anonymous = await playwrightRequest.newContext({ baseURL: BASE_URL });
  const loginResponse = await anonymous.post("/auth/login", {
    data: { email, password },
  });
  if (!loginResponse.ok()) {
    throw new Error(`Login failed for ${email}: ${loginResponse.status()}`);
  }
  const { access_token } = await loginResponse.json();
  await anonymous.dispose();
  return playwrightRequest.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${access_token}` },
  });
}

export const test = base.extend<ApiFixtures>({
  // A request context with no Authorization header, for testing unauthenticated access.
  unauthenticatedRequest: async ({}, use) => {
    const context = await playwrightRequest.newContext({ baseURL: BASE_URL });
    await use(context);
    await context.dispose();
  },

  // Logs in via /auth/login and returns a request context carrying the resulting bearer token.
  authenticatedRequest: async ({}, use) => {
    const context = await authenticatedContext(TEST_USERNAME, TEST_PASSWORD);
    await use(context);
    await context.dispose();
  },

  adminRequest: async ({}, use) => {
    const context = await authenticatedContext("admin@auroragrand.test", "Admin#2026");
    await use(context);
    await context.dispose();
  },
});

export { expect } from "@playwright/test";
