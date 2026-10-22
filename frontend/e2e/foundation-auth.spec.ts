import { expect, test } from "@playwright/test";

const frontend = process.env.FOUNDATION_FRONTEND_URL || "http://127.0.0.1:3300";
const api = process.env.FOUNDATION_API_URL || "http://127.0.0.1:8800";

test("register, restore, settings, logout and URL-token boundaries", async ({ page }) => {
  const requested: string[] = [];
  page.on("request", request => requested.push(request.url()));
  const email = `foundation-${Date.now()}@example.com`;

  await page.goto("/register");
  await page.getByLabel("Full name").fill("Foundation Student");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("SyntheticPass1234");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.reload();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByLabel("Email")).toHaveValue(email);

  expect(page.url()).not.toMatch(/access_token|refresh_token/);
  expect(requested.some(url => url.includes("nuvira.agentcraft.info"))).toBeFalsy();
  expect(requested.some(url => url.startsWith(api))).toBeTruthy();

  const rotated = await page.request.post(`${api}/auth/refresh`, {
    headers: { Origin: frontend },
  });
  expect(rotated.status()).toBe(200);
  const logout = await page.request.post(`${api}/auth/logout`, {
    headers: { Origin: frontend },
  });
  expect(logout.status()).toBe(200);
  const rejected = await page.request.post(`${api}/auth/refresh`, {
    headers: { Origin: frontend },
  });
  expect(rejected.status()).toBe(401);
});
