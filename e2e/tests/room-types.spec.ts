import { test, expect } from "./fixtures/fixtures";

test.describe("Room Types API", () => {
  test("GET /room-types/ is public", async ({ request }) => {
    const response = await request.get("/room-types/");

    expect(response.ok()).toBeTruthy();
    const roomTypes = await response.json();
    expect(roomTypes.length).toBeGreaterThan(0);
  });

  test("administrators can create, update and delete an unused room type", async ({ adminRequest }) => {
    const name = `Test Suite ${Date.now()}`;
    const createResponse = await adminRequest.post("/room-types/", {
      data: {
        name,
        description: "Created by the API integration test.",
        max_occupancy: 2,
        base_rate: 199,
        amenities: ["Free Wi-Fi"],
        image_url: "",
      },
    });
    expect(createResponse.status()).toBe(201);
    const created = await createResponse.json();

    const duplicateResponse = await adminRequest.post("/room-types/", {
      data: {
        name,
        description: "Duplicate name.",
        max_occupancy: 2,
        base_rate: 199,
        amenities: [],
        image_url: "",
      },
    });
    expect(duplicateResponse.status()).toBe(409);

    const updateResponse = await adminRequest.put(`/room-types/${created.id}`, {
      data: {
        name,
        description: "Updated by the API integration test.",
        max_occupancy: 3,
        base_rate: 229,
        amenities: ["Free Wi-Fi", "Bathtub"],
        image_url: "",
      },
    });
    expect(updateResponse.ok()).toBeTruthy();
    expect(await updateResponse.json()).toMatchObject({
      base_rate: 229,
      max_occupancy: 3,
    });

    const deleteResponse = await adminRequest.delete(`/room-types/${created.id}`);
    expect(deleteResponse.status()).toBe(204);

    const listResponse = await adminRequest.get("/room-types/");
    const roomTypes = await listResponse.json();
    expect(roomTypes.some((roomType: { id: number }) => roomType.id === created.id)).toBeFalsy();
  });

  test("deleting a room type still assigned to rooms is rejected", async ({ adminRequest }) => {
    const response = await adminRequest.delete("/room-types/1");

    expect(response.status()).toBe(409);
  });
});
