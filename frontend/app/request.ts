import { formatApiError } from "./error-format";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export async function request(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const token = sessionStorage.getItem("infraassess-token");
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, { ...init, headers });
  const text = await response.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) throw Error(formatApiError(body));
  return body as any;
}

/** Abort superseded reads and ignore late responses even if cancellation races. */
export class RequestScope {
  private active?: AbortController;
  start(): AbortController {
    this.cancel();
    return (this.active = new AbortController());
  }
  isCurrent(controller: AbortController): boolean {
    return this.active === controller && !controller.signal.aborted;
  }
  cancel() {
    this.active?.abort();
    this.active = undefined;
  }
}
