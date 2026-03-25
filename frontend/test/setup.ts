import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup, render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactElement } from "react";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

class IntersectionObserverMock {
  observe() {
    return null;
  }

  unobserve() {
    return null;
  }

  disconnect() {
    return null;
  }

  takeRecords() {
    return [];
  }
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false
  })
});

Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  value: ResizeObserverMock
});

Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  value: IntersectionObserverMock
});

afterEach(() => {
  cleanup();
});

export function renderWithQueryClient(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
        refetchOnWindowFocus: false
      },
      mutations: {
        retry: 0
      }
    }
  });

  return render(ui, {
    wrapper: ({ children }) => createElement(QueryClientProvider, { client: queryClient }, children),
    ...options
  });
}
