import { getApiBaseUrl } from "@/src/shared/config/env";

const API_BASE = getApiBaseUrl();

type ApiErrorDetail =
  | string
  | {
      code?: string;
      message?: string;
      detail?: string;
    }
  | Array<{
      msg?: string;
    }>;

function formatApiError(detail: ApiErrorDetail): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item.msg).filter((value): value is string => Boolean(value));
    return messages.join("; ");
  }

  if (detail?.message) {
    return detail.message;
  }

  if (detail?.detail) {
    return detail.detail;
  }

  return "";
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      cache: "no-store"
    });
  } catch {
    throw new Error("Unable to reach the API server.");
  }

  if (!response.ok) {
    const text = await response.text();

    try {
      const payload = JSON.parse(text) as { detail?: ApiErrorDetail };
      const message = formatApiError(payload.detail ?? "");
      throw new Error(message || `Request failed: ${response.status}`);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(text || `Request failed: ${response.status}`);
    }
  }

  return response.json() as Promise<T>;
}
