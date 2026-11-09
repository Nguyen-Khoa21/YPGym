import { expect, test, type Page } from "@playwright/test";

const PASSWORD = process.env.DEMO_PASSWORD ?? "YPGymDemo123!";

async function goClient(page: Page, path: string) {
  await page.evaluate((target) => { window.history.pushState({}, "", target); window.dispatchEvent(new PopStateEvent("popstate")); }, path);
}

async function openBroadcasts(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("owner@ypgym.dev");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await page.waitForURL(/admin/);
  await goClient(page, "/admin/broadcasts");
  await expect(page.getByRole("heading", { name: "Publish announcement" })).toBeVisible();
}

test("broadcast fields are labelled, typeable and multi-line", async ({ page }) => {
  await openBroadcasts(page);
  const title = page.getByLabel("Title", { exact: true });
  const message = page.getByLabel("Message", { exact: true });
  await title.fill("Holiday hours");
  await expect(title).toHaveValue("Holiday hours");
  await message.click();
  await page.keyboard.type("Line one");
  await page.keyboard.press("Enter");
  await page.keyboard.type("Line two");
  await expect(message).toHaveValue("Line one\nLine two");
  await expect(page.getByRole("button", { name: /publish broadcast/i })).toBeEnabled();
  expect(await message.evaluate((el) => el.tagName)).toBe("TEXTAREA");
});

test("an empty submit marks fields invalid and links the error text", async ({ page }) => {
  await openBroadcasts(page);
  await page.getByRole("button", { name: /publish broadcast/i }).click();
  const title = page.getByLabel("Title", { exact: true });
  await expect(title).toHaveAttribute("aria-invalid", "true");
  const describedBy = await title.getAttribute("aria-describedby");
  expect(describedBy).toBeTruthy();
  await expect(page.locator(`[id="${describedBy}"]`)).toHaveAttribute("role", "alert");
  await title.fill("Holiday hours");
  await expect(title).not.toHaveAttribute("aria-invalid", "true");
});

test("title and message controls share width and look on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await openBroadcasts(page);
  const a = await page.getByLabel("Title", { exact: true }).boundingBox();
  const b = await page.getByLabel("Message", { exact: true }).boundingBox();
  expect(Math.abs((a?.width ?? 0) - (b?.width ?? 1))).toBeLessThan(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
});
