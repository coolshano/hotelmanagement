import { test, expect } from "./fixtures/fixtures";

test.describe("Payments API", () => {
  test("GET /payments/ requires an admin", async ({ authenticatedRequest }) => {
    const response = await authenticatedRequest.get("/payments/");

    expect(response.status()).toBe(403);
  });

  test("administrators can record a payment against an existing booking", async ({ adminRequest }) => {
    const createResponse = await adminRequest.post("/payments/", {
      data: {
        booking_id: 2,
        amount: 259,
        currency: "GBP",
        method: "CARD",
      },
    });
    expect(createResponse.status()).toBe(201);
    const created = await createResponse.json();
    expect(created).toMatchObject({
      booking_id: 2,
      amount: 259,
      currency: "GBP",
      method: "CARD",
    });

    const getResponse = await adminRequest.get(`/payments/${created.id}`);
    expect(getResponse.ok()).toBeTruthy();
    expect((await getResponse.json()).id).toBe(created.id);
  });

  test("creating a payment against a nonexistent booking returns 404", async ({ adminRequest }) => {
    const response = await adminRequest.post("/payments/", {
      data: {
        booking_id: 999999,
        amount: 100,
        currency: "GBP",
        method: "CARD",
      },
    });

    expect(response.status()).toBe(404);
  });

  test("GET /payments/{id} returns 404 for a nonexistent payment", async ({ adminRequest }) => {
    const response = await adminRequest.get("/payments/999999");

    expect(response.status()).toBe(404);
  });
});
