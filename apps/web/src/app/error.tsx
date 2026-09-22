"use client";

import { Button } from "@/components/ui/button";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">Halaman belum dapat dimuat</h1>
      <p className="text-muted-foreground">
        Terjadi gangguan sementara. Silakan coba memuat halaman kembali.
      </p>
      <Button className="self-start" onClick={reset}>
        Coba lagi
      </Button>
    </main>
  );
}
