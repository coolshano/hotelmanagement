import { test, expect } from "./fixtures/fixtures";

test("unauthenticatedRequest can reach a public endpoint", async ({ unauthenticatedRequest }) => {
  const response = await unauthenticatedRequest.get("/health");

  expect(response.ok()).toBeTruthy();
});

test("authenticatedRequest logs in and carries a bearer token", async ({ authenticatedRequest }) => {
  const response = await authenticatedRequest.get("/auth/me");

  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toMatchObject({
    email: "test@example.com",
    role: "REGISTERED_USER",
    status: "ACTIVE",
  });
});

test("protected endpoints reject a missing token", async ({ unauthenticatedRequest }) => {
  const response = await unauthenticatedRequest.get("/bookings/");

  expect(response.status()).toBe(401);
});

test("registered users cannot access administration", async ({ authenticatedRequest }) => {
  const response = await authenticatedRequest.get("/users/");

  expect(response.status()).toBe(403);
});

test("administrators can list users", async ({ adminRequest }) => {
  const response = await adminRequest.get("/users/");

  expect(response.ok()).toBeTruthy();
  expect((await response.json()).length).toBeGreaterThan(1);
});
