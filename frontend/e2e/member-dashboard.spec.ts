import { expect, test, type Page } from "@playwright/test";

const PASSWORD = process.env.DEMO_PASSWORD ?? "YPGymDemo123!";

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await page.waitForURL(/\/app/);
}

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

for (const [email, gym] of [["memberdist1@ypgym.dev", "District 1"], ["memberdist11@ypgym.dev", "District 11"]] as const) {
  for (const [label, viewport] of [["375px", { width: 375, height: 800 }], ["1280px", { width: 1280, height: 900 }]] as const) {
    test(`dashboard for ${gym} at ${label}`, async ({ page }) => {
      const urls: string[] = [];
      page.on("request", (request) => urls.push(request.url()));
      await page.setViewportSize(viewport);
      await login(page, email);
      await expect(page.getByText(`Your gym: YPGym ${gym}`)).toBeVisible();
      await expect(page.getByRole("heading", { name: /Live occupancy/ })).toContainText(gym);
      await expect(page.getByLabel("Rotating YPGym attendance QR code")).toBeVisible();
      await expect(page.getByText(/Refreshes in/)).toBeVisible();
      await expect(page.getByRole("link", { name: "Open full QR page" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Quick actions" })).toBeVisible();
      await expect(page.getByRole("link", { name: "QR code", exact: true })).toHaveCount(0);
      const other = gym === "District 1" ? "11" : "1";
      expect(urls.filter((url) => url.includes("gym_id"))).toEqual([]);
      void other;
      await noHorizontalScroll(page);
      await page.screenshot({ path: `test-results/dashboard-${gym.replace(" ", "")}-${label}.png`, fullPage: true });

      await page.getByRole("link", { name: "Open full QR page" }).click();
      await expect(page).toHaveURL(/\/app\/qr/);
      await expect(page.getByText(`Your gym: YPGym ${gym}`)).toBeVisible();
      await expect(page.getByRole("heading", { name: "When is it quiet?" })).toBeVisible();
      await noHorizontalScroll(page);
      await page.screenshot({ path: `test-results/qr-${gym.replace(" ", "")}-${label}.png`, fullPage: true });
    });
  }
}

test("the QR code changes when the token rotates", async ({ page }) => {
  let issued = 0;
  await page.route("**/attendance/qr-token/me", async (route) => {
    issued += 1;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ token: `rotating-token-${issued}`, issued_at: new Date().toISOString(), expires_at: new Date(Date.now() + 8_000).toISOString(), ttl_seconds: 8, membership_status: "active" }),
    });
  });
  await login(page, "memberdist1@ypgym.dev");
  const code = page.getByLabel("Rotating YPGym attendance QR code");
  await expect(code).toBeVisible();
  const first = await code.innerHTML();
  await expect.poll(async () => code.innerHTML(), { timeout: 15_000 }).not.toBe(first);
  expect(issued).toBeGreaterThanOrEqual(2);
});
