import { test, expect } from "./fixtures/fixtures";

test.describe("Guests API", () => {
  test("GET /guests/ requires an admin", async ({ authenticatedRequest }) => {
    const response = await authenticatedRequest.get("/guests/");

    expect(response.status()).toBe(403);
  });

  test("administrators can create, fetch, update and delete a guest", async ({ adminRequest }) => {
    const email = `guest-${Date.now()}@example.test`;
    const createResponse = await adminRequest.post("/guests/", {
      data: {
        first_name: "Priya",
        last_name: "Chandra",
        phone: "+44 7700 900000",
        email,
        address: "1 Test Street",
      },
    });
    expect(createResponse.status()).toBe(201);
    const created = await createResponse.json();

    const duplicateResponse = await adminRequest.post("/guests/", {
      data: {
        first_name: "Priya",
        last_name: "Chandra",
        phone: "+44 7700 900000",
        email,
        address: "1 Test Street",
      },
    });
    expect(duplicateResponse.status()).toBe(409);

    const getResponse = await adminRequest.get(`/guests/${created.id}`);
    expect(getResponse.ok()).toBeTruthy();
    expect((await getResponse.json()).email).toBe(email);

    const updateResponse = await adminRequest.put(`/guests/${created.id}`, {
      data: {
        first_name: "Priya",
        last_name: "Chandra-Osei",
        phone: "+44 7700 900000",
        email,
        address: "2 Test Street",
      },
    });
    expect(updateResponse.ok()).toBeTruthy();
    expect((await updateResponse.json()).last_name).toBe("Chandra-Osei");

    const deleteResponse = await adminRequest.delete(`/guests/${created.id}`);
    expect(deleteResponse.status()).toBe(204);

    const listResponse = await adminRequest.get("/guests/");
    expect(listResponse.ok()).toBeTruthy();
    const guests = await listResponse.json();
    expect(guests.some((guest: { id: number }) => guest.id === created.id)).toBeFalsy();
  });

  test("GET /guests/{id} returns 404 for a nonexistent guest", async ({ adminRequest }) => {
    const response = await adminRequest.get("/guests/999999");

    expect(response.status()).toBe(404);
  });
});
