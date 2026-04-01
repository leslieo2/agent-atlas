"use client";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_API_PORT = "8000";

function getDefaultLocalApiBaseUrl() {
  if (typeof window === "undefined") {
    return DEFAULT_API_BASE_URL;
  }

  const hostname = window.location.hostname;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return `${window.location.protocol}//${hostname}:${DEFAULT_API_PORT}`;
  }

  return DEFAULT_API_BASE_URL;
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? getDefaultLocalApiBaseUrl();
}
