import { test, expect } from "./fixtures/fixtures";

test.describe("Reports API", () => {
  test("dashboard reports expose complete calculated shapes", async ({ adminRequest }) => {
    const response = await adminRequest.get("/reports/dashboard");

    expect(response.ok()).toBeTruthy();
    expect(await response.json()).toMatchObject({
      occupancy: {
        occupied: expect.any(Number),
        available: expect.any(Number),
        maintenance: expect.any(Number),
        total_rooms: expect.any(Number),
        occupancy_rate: expect.any(Number),
      },
      revenue: {
        currency: "GBP",
        monthly_revenue: expect.any(Number),
        previous_month_revenue: expect.any(Number),
        average_daily_rate: expect.any(Number),
        by_month: expect.any(Array),
      },
      recent_bookings: expect.any(Array),
    });
  });

  test("GET /reports/occupancy exposes calculated occupancy figures", async ({ adminRequest }) => {
    const response = await adminRequest.get("/reports/occupancy");

    expect(response.ok()).toBeTruthy();
    expect(await response.json()).toMatchObject({
      occupied: expect.any(Number),
      available: expect.any(Number),
      maintenance: expect.any(Number),
      total_rooms: expect.any(Number),
      occupancy_rate: expect.any(Number),
    });
  });

  test("GET /reports/revenue exposes calculated revenue figures", async ({ adminRequest }) => {
    const response = await adminRequest.get("/reports/revenue");

    expect(response.ok()).toBeTruthy();
    const revenue = await response.json();
    expect(revenue).toMatchObject({
      currency: "GBP",
      monthly_revenue: expect.any(Number),
      previous_month_revenue: expect.any(Number),
      average_daily_rate: expect.any(Number),
      by_month: expect.any(Array),
    });
    const months = revenue.by_month.map((entry: { month: string }) => entry.month);
    expect([...months].sort()).toEqual(months);
  });

  test("GET /reports/bookings returns the full booking list shape", async ({ adminRequest }) => {
    const response = await adminRequest.get("/reports/bookings");

    expect(response.ok()).toBeTruthy();
    const bookings = await response.json();
    expect(bookings.length).toBeGreaterThan(0);
    expect(bookings[0]).toMatchObject({
      reference: expect.any(String),
      status: expect.any(String),
      total_price: expect.any(Number),
    });
  });

  test("GET /reports/* requires an admin", async ({ authenticatedRequest }) => {
    const response = await authenticatedRequest.get("/reports/dashboard");

    expect(response.status()).toBe(403);
  });
});
