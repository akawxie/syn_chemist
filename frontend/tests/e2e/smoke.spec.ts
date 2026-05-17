import { test, expect } from "@playwright/test";

// Smoke: load the page, enter a SMILES, switch tabs.
// Run on a live backend at :8000 to exercise the full pipeline. Without backend,
// the page should still render and tabs should still switch.
test("loads page and switches tabs", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "AI_chemist" })).toBeVisible();

  await page.getByTestId("main-input").fill("CCO");

  await page.getByTestId("tab-fga").click();
  await expect(page.getByTestId("run-fga")).toBeVisible();

  await page.getByTestId("tab-conditions").click();
  await expect(page.getByTestId("run-conditions")).toBeVisible();

  await page.getByTestId("tab-retro").click();
  await expect(page.getByTestId("run-retro")).toBeVisible();
});
