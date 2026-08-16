import { test, expect } from "./fixtures/fixtures";

test.describe("Users API", () => {
  test("administrators can create a user and update their role and status", async ({ adminRequest }) => {
    const email = `user-${Date.now()}@example.test`;
    const createResponse = await adminRequest.post("/users/", {
      data: {
        email,
        full_name: "Test Created User",
        phone: "+44 7700 900999",
        password: "P@ssw0rd123",
        role: "REGISTERED_USER",
      },
    });
    expect(createResponse.status()).toBe(201);
    const created = await createResponse.json();
    expect(created.email).toBe(email);

    const duplicateResponse = await adminRequest.post("/users/", {
      data: {
        email,
        full_name: "Duplicate Email User",
        phone: "+44 7700 900998",
        password: "P@ssw0rd123",
        role: "REGISTERED_USER",
      },
    });
    expect(duplicateResponse.status()).toBe(409);

    const updateResponse = await adminRequest.put(`/users/${created.id}`, {
      data: {
        full_name: "Test Created User",
        phone: "+44 7700 900999",
        role: "ADMIN",
        status: "SUSPENDED",
      },
    });
    expect(updateResponse.ok()).toBeTruthy();
    expect(await updateResponse.json()).toMatchObject({
      role: "ADMIN",
      status: "SUSPENDED",
    });
  });

  test("an administrator cannot remove their own administrator access or suspend themselves", async ({
    adminRequest,
  }) => {
    const me = await (await adminRequest.get("/auth/me")).json();

    const demoteResponse = await adminRequest.put(`/users/${me.id}`, {
      data: {
        full_name: me.full_name,
        phone: me.phone,
        role: "REGISTERED_USER",
        status: "ACTIVE",
      },
    });
    expect(demoteResponse.status()).toBe(409);

    const suspendResponse = await adminRequest.put(`/users/${me.id}`, {
      data: {
        full_name: me.full_name,
        phone: me.phone,
        role: "ADMIN",
        status: "SUSPENDED",
      },
    });
    expect(suspendResponse.status()).toBe(409);
  });

  test("an administrator cannot delete their own account", async ({ adminRequest }) => {
    const me = await (await adminRequest.get("/auth/me")).json();

    const response = await adminRequest.delete(`/users/${me.id}`);

    expect(response.status()).toBe(409);
  });

  test("deleting a user with booking history is rejected", async ({ adminRequest }) => {
    const response = await adminRequest.delete("/users/2");

    expect(response.status()).toBe(409);
  });
});
