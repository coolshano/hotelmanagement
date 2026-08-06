import { test, expect } from "./fixtures/fixtures";

function isoAfter(days: number): string {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

test("booking creation persists pricing and rejects an overlapping booking", async ({
  authenticatedRequest,
}) => {
  const payload = {
    room_id: 2,
    check_in: isoAfter(80),
    check_out: isoAfter(82),
    guests: 2,
    special_requests: "API test booking",
  };

  const createdResponse = await authenticatedRequest.post("/bookings/", { data: payload });
  expect(createdResponse.status()).toBe(201);
  const created = await createdResponse.json();
  expect(created).toMatchObject({
    user_id: 7,
    room_id: 2,
    nights: 2,
    status: "CONFIRMED",
    currency: "GBP",
  });
  expect(created.reference).toMatch(/^AG-\d{5}$/);
  expect(created.total_price).toBeGreaterThan(created.subtotal);

  const duplicateResponse = await authenticatedRequest.post("/bookings/", { data: payload });
  expect(duplicateResponse.status()).toBe(409);

  const listResponse = await authenticatedRequest.get("/bookings/");
  expect(listResponse.ok()).toBeTruthy();
  const ownBookings = await listResponse.json();
  expect(ownBookings.every((booking: { user_id: number }) => booking.user_id === 7)).toBeTruthy();
});

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
