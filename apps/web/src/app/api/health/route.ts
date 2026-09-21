import { proxyPublicGet } from "@/lib/server/upstream";

export const dynamic = "force-dynamic";

export async function GET() {
  return proxyPublicGet("/health/ready");
}
