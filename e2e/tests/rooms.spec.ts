import { test, expect } from "@playwright/test";

test.describe("Rooms API", () => {
  test("GET /rooms/ lists rooms", async ({ request }) => {
    const response = await request.get("/rooms/");

    expect(response.ok()).toBeTruthy();
    expect(Array.isArray(await response.json())).toBeTruthy();
  });

  test("GET /rooms/available lists available rooms", async ({ request }) => {
    const response = await request.get("/rooms/available");

    expect(response.ok()).toBeTruthy();
    expect(Array.isArray(await response.json())).toBeTruthy();
  });

  test("POST /rooms/ creates a room", async ({ request }) => {
    const response = await request.post("/rooms/", {
      data: {
        number: "101",
        room_type_id: 1,
      },
    });

    expect(response.ok()).toBeTruthy();
    expect(await response.json()).toEqual({ message: "Room created" });
  });

  test("PUT /rooms/{id} updates a room", async ({ request }) => {
    const response = await request.put("/rooms/1", { data: {} });

    expect(response.ok()).toBeTruthy();
    expect(await response.json()).toEqual({ message: "Updated" });
  });

  test("DELETE /rooms/{id} deletes a room", async ({ request }) => {
    const response = await request.delete("/rooms/1");

    expect(response.ok()).toBeTruthy();
    expect(await response.json()).toEqual({ message: "Deleted" });
  });
});
