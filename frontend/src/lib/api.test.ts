import { describe, expect, it, vi } from "vitest";
import { apiRequest, ApiError, SESSION_EXPIRED } from "./api";
import { json } from "../test/helpers";

describe("API client", () => {
  it("sends bearer authentication and JSON using the API prefix", async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ id: "1" }));
    vi.stubGlobal("fetch", fetcher);
    await apiRequest("/vehicles", {
      token: "test-token",
      method: "POST",
      body: { price: "10.25" },
    });
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe("/api/vehicles");
    expect(options.headers.get("Authorization")).toBe("Bearer test-token");
    expect(options.headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(options.body)).toEqual({ price: "10.25" });
  });
  it("formats backend field validation errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json(
            { detail: [{ loc: ["body", "price"], msg: "Must be positive" }] },
            422,
          ),
        ),
    );
    await expect(apiRequest("/vehicles")).rejects.toThrow(
      "price: Must be positive",
    );
  });
  it("expires only an authenticated request on 401", async () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED, listener);
    try {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(json({ detail: "Invalid token" }, 401)),
      );
      await expect(
        apiRequest("/auth/me", { token: "invalid" }),
      ).rejects.toBeInstanceOf(ApiError);
      expect(listener).toHaveBeenCalledOnce();
      expect(listener.mock.calls[0][0].detail).toBe("invalid");
      await expect(apiRequest("/auth/login")).rejects.toBeInstanceOf(ApiError);
      expect(listener).toHaveBeenCalledOnce();
    } finally {
      window.removeEventListener(SESSION_EXPIRED, listener);
    }
  });
  it("keeps a session on forbidden requests", async () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED, listener);
    try {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValue(json({ detail: "Admin access required" }, 403)),
      );
      await expect(
        apiRequest("/vehicles/1", { token: "user" }),
      ).rejects.toThrow("Admin access required");
      expect(listener).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener(SESSION_EXPIRED, listener);
    }
  });
  it("handles empty delete responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(null, 204)));
    expect(
      await apiRequest("/vehicles/1", { method: "DELETE" }),
    ).toBeUndefined();
  });
  it("handles network and non-JSON server failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(apiRequest("/vehicles")).rejects.toThrow("Unable to connect");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("Bad gateway", { status: 502 })),
    );
    await expect(apiRequest("/vehicles")).rejects.toThrow(
      "Request failed (502)",
    );
  });
});

it("uses the configured absolute API URL including /api for a separate backend", async () => {
  vi.stubEnv("VITE_API_BASE_URL", "https://api.example/api/");
  vi.resetModules();
  try {
    const hosted = await import("./api");
    const fetcher = vi.fn().mockResolvedValue(json({ id: "1" }));
    vi.stubGlobal("fetch", fetcher);
    await hosted.apiRequest("/vehicles", { token: "test-token" });
    expect(fetcher.mock.calls[0][0]).toBe("https://api.example/api/vehicles");
    expect(fetcher.mock.calls[0][1].headers.get("Authorization")).toBe(
      "Bearer test-token",
    );
  } finally {
    vi.unstubAllEnvs();
    vi.resetModules();
  }
});
