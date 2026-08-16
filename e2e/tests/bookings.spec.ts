import { test, expect, isoAfter } from "./fixtures/fixtures";

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

test("the Redis room lock allows only one of two concurrent bookings for the same room and dates", async ({
  authenticatedRequest,
  adminRequest,
}) => {
  const payload = {
    room_id: 8,
    check_in: isoAfter(150),
    check_out: isoAfter(152),
    guests: 2,
    special_requests: "Concurrency test booking",
  };

  const [responseA, responseB] = await Promise.all([
    authenticatedRequest.post("/bookings/", { data: payload }),
    adminRequest.post("/bookings/", { data: payload }),
  ]);

  const statuses = [responseA.status(), responseB.status()].sort();
  expect(statuses).toEqual([201, 409]);
});
