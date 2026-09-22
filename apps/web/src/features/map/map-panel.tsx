"use client";

import dynamic from "next/dynamic";

const CooperativeMap = dynamic(() => import("./cooperative-map"), {
  ssr: false,
  loading: () => (
    <div
      className="flex min-h-112 items-center justify-center bg-slate-100 text-sm text-muted-foreground"
      role="status"
    >
      Menyiapkan peta…
    </div>
  ),
});

export function MapPanel({ styleUrl }: { styleUrl: string }) {
  return <CooperativeMap styleUrl={styleUrl} />;
}
