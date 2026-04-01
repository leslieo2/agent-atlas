import { getApiBaseUrl } from "@/src/shared/config/env";
import { afterEach, describe, expect, it } from "vitest";

describe("getApiBaseUrl", () => {
  const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalLocation = window.location;

  afterEach(() => {
    if (originalApiBaseUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;
    } else {
      process.env.NEXT_PUBLIC_API_BASE_URL = originalApiBaseUrl;
    }

    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("prefers an explicit NEXT_PUBLIC_API_BASE_URL", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.example:9000";

    expect(getApiBaseUrl()).toBe("http://api.example:9000");
  });

  it("defaults to localhost when the app is opened on localhost", () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: new URL("http://localhost:3000/"),
    });

    expect(getApiBaseUrl()).toBe("http://localhost:8000");
  });

  it("defaults to 127.0.0.1 when the app is opened on 127.0.0.1", () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: new URL("http://127.0.0.1:3000/"),
    });

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });
});
