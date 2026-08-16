import { defineConfig } from "@playwright/test";
import dotenv from "dotenv";
import path from "path";

dotenv.config({ path: path.resolve(__dirname, ".env") });

const BASE_URL = process.env.BASE_URL ?? "http://127.0.0.1:8000";
const PORT = new URL(BASE_URL).port || "8000";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["github"]] : "list",

  use: {
    baseURL: BASE_URL,
    extraHTTPHeaders: {
      Accept: "application/json",
    },
    trace: "on-first-retry",
  },

  // Boots the FastAPI app before the test run and tears it down after,
  // so `npx playwright test` works standalone without a manually started server.
  webServer: {
    command:
      "HMS_RESET_DATABASE=true DATABASE_URL=sqlite:////tmp/hotelmanagement-e2e.db " +
      "python -m uvicorn app.main:app --host 127.0.0.1 --port " +
      PORT,
    cwd: "..",
    url: `${BASE_URL}/health`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
