import { test, expect, isoAfter } from "./fixtures/fixtures";

test.describe("Rooms API", () => {
  test("GET /rooms/ lists rooms", async ({ request }) => {
    const response = await request.get("/rooms/");

    expect(response.ok()).toBeTruthy();
    const rooms = await response.json();
    expect(rooms.length).toBeGreaterThan(0);
    expect(rooms[0]).toMatchObject({
      room_number: expect.any(String),
      room_type: { name: expect.any(String), amenities: expect.any(Array) },
    });
  });

  test("GET /availability returns calculated, non-overlapping stays", async ({ request }) => {
    const response = await request.get("/availability", {
      params: {
        check_in: isoAfter(70),
        check_out: isoAfter(72),
        guests: 2,
      },
    });

    expect(response.ok()).toBeTruthy();
    const results = await response.json();
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]).toMatchObject({
      nights: 2,
      currency: "GBP",
      nightly_rate: expect.any(Number),
      subtotal: expect.any(Number),
      taxes: expect.any(Number),
      total: expect.any(Number),
    });
  });

  test("administrators can create, update and delete an unused room", async ({ adminRequest }) => {
    const number = `T${Date.now().toString().slice(-7)}`;
    const createResponse = await adminRequest.post("/rooms/", {
      data: {
        room_number: number,
        floor: 5,
        status: "AVAILABLE",
        room_type_id: 1,
        nightly_rate: 149,
        description: "Created by the API integration test.",
      },
    });
    expect(createResponse.status()).toBe(201);
    const created = await createResponse.json();

    const updateResponse = await adminRequest.put(`/rooms/${created.id}`, {
      data: {
        room_number: number,
        floor: 5,
        status: "MAINTENANCE",
        room_type_id: 1,
        nightly_rate: 159,
        description: "Updated by the API integration test.",
      },
    });
    expect(updateResponse.ok()).toBeTruthy();
    expect((await updateResponse.json()).status).toBe("MAINTENANCE");

    const deleteResponse = await adminRequest.delete(`/rooms/${created.id}`);
    expect(deleteResponse.status()).toBe(204);

    const listResponse = await adminRequest.get("/rooms/");
    expect(listResponse.ok()).toBeTruthy();
    const rooms = await listResponse.json();
    expect(rooms.some((room: { id: number }) => room.id === created.id)).toBeFalsy();
  });
});
