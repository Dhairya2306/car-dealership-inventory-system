const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(
  /\/$/,
  "",
);
export const SESSION_EXPIRED = "dealership:session-expired";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(data: unknown, status: number): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(
          (item: { loc?: string[]; msg?: string }) =>
            `${item.loc?.slice(1).join(".") || "Request"}: ${item.msg || "Invalid value"}`,
        )
        .join(". ");
    }
  }
  return `Request failed (${status}). Please try again.`;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  token?: string | null;
  body?: unknown;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { token, body, ...init } = options;
  const headers = new Headers(init.headers);
  if (body !== undefined) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new ApiError(
      0,
      "Unable to connect. Check your connection and try again.",
    );
  }
  const data: unknown =
    response.status === 204
      ? undefined
      : await response.json().catch(() => undefined);
  if (!response.ok) {
    if (response.status === 401 && token) {
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED, { detail: token }));
    }
    throw new ApiError(response.status, errorMessage(data, response.status));
  }
  return data as T;
}

export function messageOf(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
