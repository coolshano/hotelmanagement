import { test, expect } from "@playwright/test";

test("GET /health reports the API is up", async ({ request }) => {
  const response = await request.get("/health");
  console.log(response.url());

  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: "UP" });
});
