import "server-only";

function getApiOrigin(): string {
  const value = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  const url = new URL(value);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error("API_INTERNAL_URL must be an HTTP(S) origin without credentials or a path");
  }
  return url.origin;
}

// A deliberately small allowlist: never forward an arbitrary URL, method or header.
export async function proxyPublicGet(
  path: "/health/ready" | "/api/v1/cooperatives",
  search = "",
): Promise<Response> {
  const requestId = crypto.randomUUID();
  try {
    const response = await fetch(`${getApiOrigin()}${path}${search}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
      headers: { Accept: "application/json", "X-Request-ID": requestId },
      redirect: "error",
    });
    const headers = {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "X-Request-ID": requestId,
    };
    if (response.status >= 500) {
      return Response.json(
        { detail: "Layanan data sementara tidak tersedia." },
        { status: 503, headers },
      );
    }
    if (!response.headers.get("content-type")?.includes("application/json")) {
      return Response.json(
        { detail: "Respons layanan data tidak valid." },
        { status: 502, headers },
      );
    }
    return new Response(await response.text(), { status: response.status, headers });
  } catch {
    return Response.json(
      { detail: "Layanan data belum dapat dihubungi." },
      {
        status: 503,
        headers: { "Cache-Control": "no-store", "X-Request-ID": requestId },
      },
    );
  }
}
