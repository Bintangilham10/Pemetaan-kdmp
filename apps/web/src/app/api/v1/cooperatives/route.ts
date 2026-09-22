import type { NextRequest } from "next/server";
import { proxyPublicGet } from "@/lib/server/upstream";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams();
  for (const key of ["bbox", "limit"] as const) {
    const value = request.nextUrl.searchParams.get(key);
    if (value !== null) params.set(key, value);
  }
  return proxyPublicGet("/api/v1/cooperatives", `?${params.toString()}`);
}
