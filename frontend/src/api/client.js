const REQUEST_TIMEOUT_MS = 150000;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export class ResearchApiError extends Error {
  constructor(message, kind = "unknown") {
    super(message);
    this.name = "ResearchApiError";
    this.kind = kind;
  }
}

export async function submitResearch(question, maxPapers = 3) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, max_papers: maxPapers }),
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const detail =
        payload && typeof payload.detail === "string"
          ? payload.detail
          : "The research service returned an error.";
      throw new ResearchApiError(
        detail,
        response.status >= 500 ? "server" : "validation",
      );
    }
    if (!payload || typeof payload !== "object") {
      throw new ResearchApiError(
        "The research service returned an invalid response.",
        "invalid-response",
      );
    }
    return payload;
  } catch (error) {
    if (error instanceof ResearchApiError) throw error;
    if (error.name === "AbortError") {
      throw new ResearchApiError(
        "The research request timed out. Check the API and try again.",
        "timeout",
      );
    }
    throw new ResearchApiError(
      "The research service could not be reached. Start the API and try again.",
      "network",
    );
  } finally {
    clearTimeout(timeout);
  }
}
