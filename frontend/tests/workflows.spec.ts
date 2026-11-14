import { expect, test, type Page, type Route } from "@playwright/test";

const component = (id: number, name: string) => ({
  component_id: id,
  asset_tag: `ASSET-${id}`,
  name,
  location_id: 1,
  category_id: 1,
  status: "OPERATIONAL",
  installed_on: null,
});
const incident = {
  incident_id: 1,
  incident_number: "INC-TEST",
  reported_at: "2026-11-11T10:30:45.123456Z",
  severity: "HIGH",
  status: "OPEN",
  title: "Pump leak",
  description: "Leaking seal",
  resolved_at: null,
};

async function reply(route: Route, body: unknown) {
  await route.fulfill({
    json: body,
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "*",
      "access-control-allow-methods": "*",
    },
  });
}

async function mockApi(
  page: Page,
  handle?: (route: Route, url: URL) => Promise<boolean>,
) {
  await page.addInitScript(() => sessionStorage.setItem("infraassess-token", "test-admin"));
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === "OPTIONS") {
      await reply(route, {});
      return;
    }
    if (handle && (await handle(route, url))) return;
    if (url.pathname === "/api/dashboard")
      await reply(route, {
        components: 2,
        open_incidents: 1,
        active_work_orders: 0,
        active_alerts: 0,
      });
    else if (url.pathname === "/api/components")
      await reply(route, [
        component(1, "First pump"),
        component(2, "Second pump"),
      ]);
    else if (url.pathname === "/api/locations") await reply(route, [{location_id:1,name:"North"}]);
    else if (url.pathname === "/api/categories") await reply(route, [{category_id:1,name:"Pump"}]);
    else if (url.pathname === "/api/technicians") await reply(route, [{technician_id:2,full_name:"Test technician",active:true}]);
    else if (url.pathname === "/api/incidents") await reply(route, [incident]);
    else await reply(route, []);
  });
}

test("a newer list search cancels the older response", async ({ page }) => {
  let releaseOld!: () => void;
  let signalOld!: () => void;
  const oldStarted = new Promise<void>((resolve) => {
    signalOld = resolve;
  });
  const oldGate = new Promise<void>((resolve) => {
    releaseOld = resolve;
  });
  await mockApi(page, async (route, url) => {
    if (url.pathname !== "/api/components") return false;
    if (url.searchParams.get("search") === "old") {
      signalOld();
      await oldGate;
      await reply(route, [component(3, "Old result")]).catch(() => {});
      return true;
    }
    if (url.searchParams.get("search") === "new") {
      await reply(route, [component(4, "New result")]);
      return true;
    }
    return false;
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Components", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "First pump OPERATIONAL" }),
  ).toBeVisible();
  const search = page.getByPlaceholder("Search components…");
  await search.fill("old");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await oldStarted;
  const cancelled = page.waitForEvent("requestfailed", (request) =>
    request.url().includes("search=old"),
  );
  await search.fill("new");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await cancelled;
  releaseOld();
  await expect(
    page.getByRole("button", { name: "New result OPERATIONAL" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Old result OPERATIONAL" }),
  ).toHaveCount(0);
});

test("selecting another record exits the previous editor", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Components", exact: true }).click();
  await page.getByRole("button", { name: "First pump OPERATIONAL" }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByLabel("Asset tag")).toHaveValue("ASSET-1");
  await page.getByRole("button", { name: "Second pump OPERATIONAL" }).click();
  await expect(
    page.getByRole("heading", { name: "Record detail" }),
  ).toBeVisible();
  await expect(page.getByLabel("Asset tag")).toHaveCount(0);
  await expect(page.locator(".detail")).toContainText("ASSET-2");
});

test("timestamp edits retain seconds, milliseconds and timezone", async ({
  page,
}) => {
  let saved: Record<string, unknown> | undefined;
  await mockApi(page, async (route, url) => {
    if (
      url.pathname === "/api/incidents/1" &&
      route.request().method() === "PATCH"
    ) {
      saved = route.request().postDataJSON();
      await reply(route, { ...incident, ...saved });
      return true;
    }
    return false;
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Incidents", exact: true }).click();
  await page.getByRole("button", { name: "Pump leak OPEN" }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByLabel("Reported at")).toHaveValue(
    "2026-11-11T16:00:45.123",
  );
  await page.getByLabel("Reported at").fill("2026-11-11T16:01:45.123");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Save record", exact: true }),
  ).toHaveCount(0);
  expect(saved?.reported_at).toBe("2026-11-11T10:31:45.123Z");
});

test("editing unrelated fields preserves PostgreSQL timestamp microseconds", async ({
  page,
}) => {
  let saved: Record<string, unknown> | undefined;
  await mockApi(page, async (route, url) => {
    if (
      url.pathname === "/api/incidents/1" &&
      route.request().method() === "PATCH"
    ) {
      saved = route.request().postDataJSON();
      await reply(route, { ...incident, ...saved });
      return true;
    }
    return false;
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Incidents", exact: true }).click();
  await page.getByRole("button", { name: "Pump leak OPEN" }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Title", { exact: true }).fill("Revised title");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Save record", exact: true }),
  ).toHaveCount(0);
  expect(saved?.reported_at).toBe(incident.reported_at);
});

test("deleting the final record on a page returns to the previous page", async ({
  page,
}) => {
  await mockApi(page, async (route, url) => {
    if (url.pathname === "/api/components/26") {
      await route.fulfill({
        status: 204,
        headers: { "access-control-allow-origin": "*" },
      });
      return true;
    }
    if (url.pathname !== "/api/components") return false;
    await reply(
      route,
      url.searchParams.get("offset") === "25"
        ? [component(26, "Last pump")]
        : Array.from({ length: 26 }, (_, i) =>
            component(i + 1, `Pump ${i + 1}`),
          ),
    );
    return true;
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Components", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Last pump OPERATIONAL" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Delete record", exact: true })
    .click();
  await expect(page.getByText("Page 1", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Pump 1 OPERATIONAL", exact: true }),
  ).toBeVisible();
});

test("mobile navigation can open management pages", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Components", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Components", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "First pump OPERATIONAL" }),
  ).toBeVisible();
});

test("editing and refreshing keep list and selected details synchronized", async ({
  page,
}) => {
  // Deliberately return name first: record identity cannot depend on JSON key order.
  let record = Object.assign({ name: "Before edit" }, component(1, "Before edit"));
  await mockApi(page, async (route, url) => {
    if (
      url.pathname === "/api/components/1" &&
      route.request().method() === "PATCH"
    ) {
      record = { ...record, ...route.request().postDataJSON() };
      await reply(route, record);
      return true;
    }
    if (url.pathname === "/api/components") {
      await reply(route, [record]);
      return true;
    }
    return false;
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Components", exact: true }).click();
  await page.getByRole("button", { name: "Before edit OPERATIONAL" }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("After edit");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await page.getByRole("button", { name: "After edit OPERATIONAL" }).click();
  await expect(page.locator(".detail")).toContainText("After edit");
  await expect(page.locator(".detail")).not.toContainText("Before edit");
  record = { ...record, name: "After server refresh" };
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "After server refresh OPERATIONAL" }),
  ).toBeVisible();
  await expect(page.locator(".detail")).toContainText("After server refresh");
  await expect(page.locator(".detail")).not.toContainText("After edit");
});

test("saving blocks duplicate clicks and renders server validation errors", async ({
  page,
}) => {
  let posts = 0;
  let releaseSave!: () => void;
  let signalSave!: () => void;
  const started = new Promise<void>((resolve) => {
    signalSave = resolve;
  });
  const gate = new Promise<void>((resolve) => {
    releaseSave = resolve;
  });
  await mockApi(page, async (route, url) => {
    if (
      url.pathname !== "/api/components" ||
      route.request().method() !== "POST"
    )
      return false;
    posts++;
    signalSave();
    await gate;
    await route.fulfill({
      status: 422,
      json: {
        detail: [{ loc: ["body", "asset_tag"], msg: "Identifier is reserved" }],
      },
      headers: { "access-control-allow-origin": "*" },
    });
    return true;
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Components", exact: true }).click();
  await page.getByRole("button", { name: "＋ Add", exact: true }).click();
  await page.getByLabel("Asset tag").fill("TEST-1");
  await page.getByRole("combobox", {name: /^Location ID/}).selectOption("1");
  await page.getByRole("combobox", {name: /^Category ID/}).selectOption("1");
  await page.getByLabel("Name", { exact: true }).fill("Test pump");
  await page.getByRole("combobox", { name: /^Status/ }).selectOption("OPERATIONAL");
  await page.getByRole("button", { name: "Save record", exact: true }).click();
  await started;
  const saving = page.getByRole("button", { name: "Saving…", exact: true });
  await expect(saving).toBeDisabled();
  await saving.evaluate((button: HTMLButtonElement) => {
    button.click();
    button.click();
  });
  expect(posts).toBe(1);
  releaseSave();
  await expect(
    page.getByText("body.asset_tag: Identifier is reserved", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save record", exact: true }),
  ).toBeEnabled();
});

test("navigation supports keyboard focus and Enter activation", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");
  const overview = page.getByRole("button", { name: "Overview", exact: true });
  await overview.focus();
  await expect(overview).toBeFocused();
  await expect(overview).toHaveCSS("outline-width", "3px");
  await page.getByRole("button", { name: "Components", exact: true }).focus();
  await expect(
    page.getByRole("button", { name: "Components", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Components", exact: true }),
  ).toBeVisible();
});

test("overview refresh cancels an in-flight semantic search", async ({
  page,
}) => {
  let releaseSearch!: () => void;
  let signalSearch!: () => void;
  let recentRequests = 0;
  const searchStarted = new Promise<void>((resolve) => {
    signalSearch = resolve;
  });
  const searchGate = new Promise<void>((resolve) => {
    releaseSearch = resolve;
  });
  await mockApi(page, async (route, url) => {
    if (url.pathname === "/api/search/incidents") {
      signalSearch();
      await searchGate;
      await reply(route, [{ ...incident, title: "Stale search" }]).catch(
        () => {},
      );
      return true;
    }
    if (url.pathname === "/api/incidents") {
      recentRequests++;
      await reply(route, [
        {
          ...incident,
          title:
            recentRequests === 1 ? "Initial incident" : "Refreshed incident",
        },
      ]);
      return true;
    }
    return false;
  });
  await page.goto("/");
  await expect(
    page.getByText("Initial incident", { exact: true }),
  ).toBeVisible();
  await page
    .getByPlaceholder("pump vibrating and leaking")
    .fill("leaking pump");
  await page.getByRole("button", { name: "Search ↗", exact: true }).click();
  await searchStarted;
  const cancelled = page.waitForEvent("requestfailed", (request) =>
    request.url().includes("/api/search/incidents"),
  );
  await page.getByRole("button", { name: "↻ Refresh", exact: true }).click();
  await cancelled;
  releaseSearch();
  await expect(
    page.getByText("Refreshed incident", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recent incidents", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Search ↗", exact: true }),
  ).toBeEnabled();
});


test("sign in rejects invalid credentials and accepts a corrected token", async ({ page }) => {
  await page.route("**/api/**", async route => {
    if (route.request().headers().authorization !== "Bearer valid-token") {
      await route.fulfill({status: 401, json: {detail: "A valid bearer token is required."}});
    } else {
      await reply(route, route.request().url().includes("dashboard") ? {components: 0} : []);
    }
  });
  await page.goto("/");
  await page.getByLabel("Access token").fill("invalid-token");
  await page.getByRole("button", {name: "Connect"}).click();
  await expect(page.locator(".form [role=alert]")).toContainText("valid bearer token");
  await expect(page.getByRole("heading", {name: "InfraAssess sign in"})).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("infraassess-token"))).toBeNull();
  await page.getByLabel("Access token").fill("valid-token");
  await page.getByRole("button", {name: "Connect"}).click();
  await expect(page.getByRole("heading", {name: "Infrastructure overview"})).toBeVisible();
});
