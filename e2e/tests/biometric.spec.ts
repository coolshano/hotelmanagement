import { request as playwrightRequest, type APIRequestContext } from "@playwright/test";

import { test as base, expect } from "./fixtures/fixtures";

/**
 * Biometric sign-in for administrator accounts.
 *
 * The phone never sends a password: it holds a server-issued secret behind the
 * OS keystore and exchanges it for a normal session. The test that matters most
 * is the last one — an administrator resetting the enrolment from the web app
 * really does lock the device out.
 */

const BASE_URL = process.env.BASE_URL ?? "http://127.0.0.1:8000";

/**
 * Several of these tests are destructive at account level: resetting biometrics
 * clears *every* device on the account. Sharing the seeded admin across workers
 * would make them stomp on each other under `fullyParallel`, so each worker
 * gets its own throwaway administrator.
 *
 * Worker scope rather than test scope is deliberate. Playwright runs a worker's
 * tests serially, so this is still collision-free, and it costs one account
 * creation per worker instead of one per test - which matters because every
 * login runs a 390,000-iteration PBKDF2 and the dev server is single-process.
 */
interface ThrowawayAdmin {
  id: number;
  email: string;
  /** Mutable: the password-change test updates this after rotating it. */
  password: string;
  request: APIRequestContext;
}

const test = base.extend<Record<string, never>, { workerAdmin: ThrowawayAdmin }>({
  workerAdmin: [
    async ({}, use, workerInfo) => {
      const anonymous = await playwrightRequest.newContext({ baseURL: BASE_URL });

      const seeded = await anonymous.post("/auth/login", {
        data: { email: "admin@auroragrand.test", password: "Admin#2026" },
      });
      expect(seeded.ok()).toBeTruthy();
      const seededToken = (await seeded.json()).access_token;

      const asSeededAdmin = await playwrightRequest.newContext({
        baseURL: BASE_URL,
        extraHTTPHeaders: { Authorization: `Bearer ${seededToken}` },
      });

      const email = `biometric-w${workerInfo.workerIndex}-${Date.now()}@e2e.test`;
      const password = "Biometric#2026x";

      const created = await asSeededAdmin.post("/users/", {
        data: {
          full_name: "Biometric Test Admin",
          email,
          password,
          role: "ADMIN",
        },
      });
      expect(created.status()).toBe(201);
      const { id } = await created.json();

      const session = await anonymous.post("/auth/login", {
        data: { email, password },
      });
      expect(session.ok()).toBeTruthy();
      const { access_token } = await session.json();

      const request = await playwrightRequest.newContext({
        baseURL: BASE_URL,
        extraHTTPHeaders: { Authorization: `Bearer ${access_token}` },
      });

      const admin: ThrowawayAdmin = { id, email, password, request };

      await use(admin);

      await request.dispose();
      await asSeededAdmin.delete(`/users/${id}`);
      await asSeededAdmin.dispose();
      await anonymous.dispose();
    },
    { scope: "worker" },
  ],
});

test.afterEach(async ({ workerAdmin }) => {
  await workerAdmin.request.delete("/auth/biometric");
});

/** Unique per test so the (user, device) key can never collide. */
function deviceId(): string {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

async function enrol(request: APIRequestContext, device: string) {
  const response = await request.post("/auth/biometric/enroll", {
    data: { device_id: device, device_label: "Playwright device" },
  });
  expect(response.status()).toBe(201);
  return response.json();
}

test("an administrator can enrol a device and sign in with it", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  const enrolment = await enrol(workerAdmin.request, device);

  expect(enrolment.biometric_token).toBeTruthy();
  expect(enrolment.device_label).toBe("Playwright device");

  const response = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: enrolment.biometric_token,
    },
  });

  expect(response.ok()).toBeTruthy();

  const session = await response.json();
  expect(session).toMatchObject({ token_type: "bearer" });
  expect(session.access_token).toBeTruthy();
  expect(session.refresh_token).toBeTruthy();
  expect(session.user).toMatchObject({ email: workerAdmin.email, role: "ADMIN" });
});

test("the session from a biometric sign-in has full administrator access", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  const enrolment = await enrol(workerAdmin.request, device);

  const session = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: enrolment.biometric_token,
    },
  });

  const { access_token } = await session.json();

  const authed = await playwrightRequest.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${access_token}` },
  });

  expect((await authed.get("/reports/dashboard")).ok()).toBeTruthy();
  await authed.dispose();
});

test("a registered user cannot enrol a biometric device", async ({
  authenticatedRequest,
}) => {
  const response = await authenticatedRequest.post("/auth/biometric/enroll", {
    data: { device_id: deviceId(), device_label: "Guest phone" },
  });

  expect(response.status()).toBe(403);
});

test("the device list never returns the secret", async ({ workerAdmin }) => {
  const device = deviceId();
  await enrol(workerAdmin.request, device);

  const response = await workerAdmin.request.get("/auth/biometric/devices");
  expect(response.ok()).toBeTruthy();

  const devices = await response.json();
  expect(devices).toHaveLength(1);
  expect(devices[0].device_id).toBe(device);
  expect(devices[0]).not.toHaveProperty("biometric_token");
  expect(devices[0]).not.toHaveProperty("secret_hash");
});

test("a wrong secret is rejected", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  await enrol(workerAdmin.request, device);

  const response = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: "x".repeat(43),
    },
  });

  expect(response.status()).toBe(401);
});

test("an unknown device is rejected", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const response = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: deviceId(),
      biometric_token: "x".repeat(43),
    },
  });

  expect(response.status()).toBe(401);
});

test("an administrator reset from the web app locks the device out", async ({
  workerAdmin,
  adminRequest,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  const enrolment = await enrol(workerAdmin.request, device);
  const credentials = {
    email: workerAdmin.email,
    device_id: device,
    biometric_token: enrolment.biometric_token,
  };

  // The device works to begin with.
  const before = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: credentials,
  });
  expect(before.ok()).toBeTruthy();

  // This is what the web app's "Reset biometric" button calls.
  const listed = await adminRequest.get(`/users/${workerAdmin.id}/biometric`);
  expect(listed.ok()).toBeTruthy();
  expect(await listed.json()).toHaveLength(1);

  const reset = await adminRequest.delete(`/users/${workerAdmin.id}/biometric`);
  expect(reset.status()).toBe(204);

  const after = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: credentials,
  });
  expect(after.status()).toBe(401);

  // The message has to tell the phone's owner what to do next.
  const body = await after.json();
  expect(body.detail.message.toLowerCase()).toContain("password");

  // And the account itself is untouched.
  const withPassword = await unauthenticatedRequest.post("/auth/login", {
    data: { email: workerAdmin.email, password: workerAdmin.password },
  });
  expect(withPassword.ok()).toBeTruthy();
});

test("a registered user cannot read or reset another account's devices", async ({
  authenticatedRequest,
  workerAdmin,
}) => {
  expect(
    (await authenticatedRequest.get(`/users/${workerAdmin.id}/biometric`)).status(),
  ).toBe(403);
  expect(
    (await authenticatedRequest.delete(`/users/${workerAdmin.id}/biometric`)).status(),
  ).toBe(403);
});

test("a user can remove their own enrolled device", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  const enrolment = await enrol(workerAdmin.request, device);

  const removed = await workerAdmin.request.delete(
    `/auth/biometric/devices/${enrolment.id}`,
  );
  expect(removed.status()).toBe(204);

  const response = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: enrolment.biometric_token,
    },
  });

  expect(response.status()).toBe(401);
});

test("re-enrolling the same device issues a new secret and retires the old one", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  const first = await enrol(workerAdmin.request, device);
  const second = await enrol(workerAdmin.request, device);

  // The same row is recycled rather than piling up duplicates.
  expect(second.id).toBe(first.id);
  expect(second.biometric_token).not.toBe(first.biometric_token);

  const withOld = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: first.biometric_token,
    },
  });
  expect(withOld.status()).toBe(401);

  const withNew = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: second.biometric_token,
    },
  });
  expect(withNew.ok()).toBeTruthy();
});

test("changing the password revokes every enrolled device", async ({
  workerAdmin,
  unauthenticatedRequest,
}) => {
  const device = deviceId();
  const enrolment = await enrol(workerAdmin.request, device);

  const rotated = "Biometric#2027y";

  const changed = await workerAdmin.request.post("/auth/change-password", {
    data: {
      current_password: workerAdmin.password,
      new_password: rotated,
    },
  });
  expect(changed.ok()).toBeTruthy();

  // The fixture is shared with the rest of this worker's tests, so keep the
  // record it hands them accurate.
  workerAdmin.password = rotated;

  const response = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: workerAdmin.email,
      device_id: device,
      biometric_token: enrolment.biometric_token,
    },
  });

  expect(response.status()).toBe(401);
});

test("biometric login rejects unknown fields", async ({
  unauthenticatedRequest,
}) => {
  const response = await unauthenticatedRequest.post("/auth/biometric/login", {
    data: {
      email: "admin@auroragrand.test",
      device_id: deviceId(),
      biometric_token: "x".repeat(43),
      role: "ADMIN",
    },
  });

  expect(response.status()).toBe(422);
});

test("enrolment requires a session", async ({ unauthenticatedRequest }) => {
  const response = await unauthenticatedRequest.post("/auth/biometric/enroll", {
    data: { device_id: deviceId(), device_label: "Anonymous" },
  });

  expect(response.status()).toBe(401);
});

export { expect };
