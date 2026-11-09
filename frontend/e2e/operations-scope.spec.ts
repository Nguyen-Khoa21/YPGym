import { expect, test, type Page } from "@playwright/test";

const PASSWORD = process.env.DEMO_PASSWORD ?? "YPGymDemo123!";

// Client-side navigation keeps the signed-in session; a full reload can drop it in some sandboxes.
async function goClient(page: Page, path: string) {
  await page.evaluate((target) => { window.history.pushState({}, "", target); window.dispatchEvent(new PopStateEvent("popstate")); }, path);
}

async function login(page: Page, email: string, landing: RegExp) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await page.waitForURL(landing);
}

test("staff attendance is locked until clock-in and locks again after clock-out", async ({ page }) => {
  const attendanceRequests: string[] = [];
  page.on("request", (request) => { if (/\/attendance\/(admin|crowdedness)/.test(request.url())) attendanceRequests.push(request.url()); });
  await login(page, "staffdist1@ypgym.dev", /staff\/time-clock/);
  await goClient(page, "/admin/attendance");
  await expect(page.getByRole("heading", { name: "You are clocked out" })).toBeVisible();
  await expect(page.getByText("Gym: YPGym District 1", { exact: true })).toBeVisible();
  expect(attendanceRequests).toEqual([]);

  await page.getByRole("button", { name: "Clock in" }).click();
  await expect(page.getByRole("heading", { name: "Attendance sessions" })).toBeVisible();
  await expect(page.getByTestId("gym-scope")).toContainText("YPGym District 1");
  await expect(page.getByText(/On shift since/)).toBeVisible();
  expect(attendanceRequests.length).toBeGreaterThan(0);

  await page.getByRole("button", { name: "Clock out" }).click();
  await expect(page.getByRole("heading", { name: "You are clocked out" })).toBeVisible();
  const before = attendanceRequests.length;
  await page.waitForTimeout(1_500);
  expect(attendanceRequests.length).toBe(before);
});

test("a manager sees their gym and no branch selector", async ({ page }) => {
  await login(page, "managerdist1@ypgym.dev", /\/admin/);
  await goClient(page, "/admin/attendance");
  await expect(page.getByTestId("gym-scope")).toContainText("Your gym: YPGym District 1");
  await expect(page.getByLabel("Branch")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Branches" })).toHaveCount(0);
  await expect(page.getByText(/Successful payments/)).toHaveCount(0);
});

test("the owner switches branch and sees one card per gym", async ({ page }) => {
  await login(page, "owner@ypgym.dev", /\/admin/);
  await goClient(page, "/admin/attendance");
  const selector = page.getByLabel("Branch");
  await expect(selector).toBeVisible();
  await expect(selector.locator("option:checked")).toContainText("District 1");
  await selector.selectOption({ label: "YPGym District 11 · District 11" });
  await expect(page.getByTestId("gym-scope")).toContainText("District 11");
  await expect(page.getByRole("heading", { name: "Attendance sessions" })).toBeVisible();

  await page.getByRole("link", { name: "Branches" }).click();
  const cards = page.getByRole("region", { name: "Branch overview" }).getByRole("article");
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0)).toContainText("District 1");
  await expect(cards.nth(1)).toContainText("District 11");
});
