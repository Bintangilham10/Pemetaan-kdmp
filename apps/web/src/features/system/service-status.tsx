"use client";

import { useEffect, useState } from "react";
import type { components } from "@kdmp/contracts";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function ServiceStatus() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  useEffect(() => {
    let active = true;
    let current: AbortController | undefined;
    async function check() {
      current?.abort();
      const controller = new AbortController();
      current = controller;
      try {
        const response = await fetch("/api/health", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("unavailable");
        const data: components["schemas"]["ReadyStatus"] = await response.json();
        if (active && !controller.signal.aborted) setStatus(data.status === "ok" ? "ok" : "error");
      } catch {
        if (active && !controller.signal.aborted) setStatus("error");
      }
    }
    void check();
    const interval = setInterval(() => void check(), 30000);
    return () => {
      active = false;
      current?.abort();
      clearInterval(interval);
    };
  }, []);

  return (
    <Badge
      className={cn(
        "border-border bg-card text-muted-foreground",
        status === "ok" && "border-emerald-200 bg-emerald-50 text-emerald-800",
        status === "error" && "border-amber-200 bg-amber-50 text-amber-800",
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full bg-slate-400",
          status === "ok" && "bg-emerald-600",
          status === "error" && "bg-amber-600",
        )}
      />
      <span role="status">
        {status === "loading"
          ? "Memeriksa koneksi"
          : status === "ok"
            ? "Layanan terhubung"
            : "Koneksi terganggu"}
      </span>
    </Badge>
  );
}
