import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const edge = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

export default defineConfig({
  testDir: "./tests",
  timeout: 20000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3100",
    timezoneId: "Asia/Kolkata",
    launchOptions: { executablePath: existsSync(edge) ? edge : undefined },
  },
  webServer: {
    command: "npm run start -- --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
