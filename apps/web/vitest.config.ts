import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": resolve(__dirname, ".")
    }
  },
  esbuild: {
    jsx: "automatic"
  },
  test: {
    globals: true,
    css: true,
    environment: "jsdom",
    include: [
      "test/**/*.spec.ts",
      "test/**/*.spec.tsx",
      "test/**/*.test.ts",
      "test/**/*.test.tsx",
    ],
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
    setupFiles: ["./test/setup.ts"],
      coverage: {
        reporter: ["text", "json", "html"],
      include: ["src/**/*"],
      exclude: ["app/**/*"],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 60,
        statements: 70
      }
    }
  }
});
