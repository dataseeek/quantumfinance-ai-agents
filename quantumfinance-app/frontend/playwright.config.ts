import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,         // backend tem 1 thread de LLM, evitar interferência
  workers: 1,
  retries: 0,
  timeout: 120_000,             // alguns testes chamam LLM (~30s)
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
