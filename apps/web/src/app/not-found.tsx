import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-4 p-8">
      <p className="text-sm font-semibold text-primary">404</p>
      <h1 className="text-2xl font-semibold">Halaman tidak ditemukan</h1>
      <p className="text-muted-foreground">Kembali ke peta untuk melanjutkan eksplorasi.</p>
      <Button asChild className="self-start">
        <Link href="/">Kembali ke peta</Link>
      </Button>
    </main>
  );
}
