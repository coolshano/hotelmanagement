import { test, expect } from "./fixtures/fixtures";

test("unauthenticatedRequest can reach a public endpoint", async ({ unauthenticatedRequest }) => {
  const response = await unauthenticatedRequest.get("/health");

  expect(response.ok()).toBeTruthy();
});

test("authenticatedRequest logs in and carries a bearer token", async ({ authenticatedRequest }) => {
  const response = await authenticatedRequest.get("/users/");

  expect(response.ok()).toBeTruthy();
});
