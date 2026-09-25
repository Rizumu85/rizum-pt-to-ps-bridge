import { defineConfig } from "vitest/config"

export default defineConfig({
  test: {
    // Native UI tests open real windows; concurrent files compete for GPU and
    // focus, disrupting the user's desktop and invalidating input timings.
    fileParallelism: false,
    maxWorkers: 1,
  },
})
