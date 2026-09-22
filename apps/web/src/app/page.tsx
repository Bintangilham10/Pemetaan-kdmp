import Link from "next/link";
import {
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  CircleHelp,
  Compass,
  Database,
  Map,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MapPanel } from "@/features/map/map-panel";
import { ServiceStatus } from "@/features/system/service-status";

export const dynamic = "force-dynamic";

export default function Home() {
  const styleUrl = process.env.MAP_STYLE_URL ?? "https://demotiles.maplibre.org/style.json";
  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-primary p-3 text-white focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
      >
        Lewati ke konten utama
      </a>
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-400 items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-10">
          <Link href="/" className="flex items-center gap-3" aria-label="Merah Putih beranda">
            <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-white">
              <Building2 className="size-5" strokeWidth={1.7} />
            </span>
            <span>
              <span className="block text-sm font-bold tracking-[0.13em]">MERAH PUTIH</span>
              <span className="mt-0.5 block text-[11px] text-muted-foreground sm:text-xs">
                Koperasi Desa / Kelurahan
              </span>
            </span>
          </Link>
          <div className="flex items-center gap-5">
            <span className="hidden text-xs text-muted-foreground md:block">
              Platform informasi geospasial
            </span>
            <Badge className="border-primary/15 bg-accent text-accent-foreground">
              Fondasi v0.1
            </Badge>
          </div>
        </div>
      </header>
      <div className="mx-auto grid max-w-400 lg:grid-cols-[240px_1fr] xl:grid-cols-[270px_1fr]">
        <aside className="hidden min-h-[calc(100vh-82px)] flex-col border-r bg-card/50 px-5 py-8 lg:flex lg:px-6">
          <p className="mb-4 px-3 text-[10px] font-semibold tracking-[0.18em] text-muted-foreground">
            RUANG EKSPLORASI
          </p>
          <nav aria-label="Navigasi utama">
            <a
              href="#main"
              aria-current="page"
              className="flex items-center gap-3 rounded-xl bg-accent px-3 py-3 text-sm font-semibold text-accent-foreground"
            >
              <Map className="size-4" />
              Peta koperasi
              <ArrowUpRight className="ml-auto size-3.5" />
            </a>
          </nav>
          <div className="mt-8 px-3">
            <span className="text-[10px] font-semibold tracking-[0.18em] text-muted-foreground">
              TENTANG PLATFORM
            </span>
            <p className="mt-3 text-xs leading-6 text-muted-foreground">
              Satu ruang untuk mengenali koperasi dan memahami potensi desa di seluruh Indonesia.
            </p>
          </div>
          <div className="mt-auto pt-16">
            <div className="rounded-xl border bg-card p-4">
              <Compass className="mb-3 size-5 text-primary" />
              <p className="text-xs font-semibold">Berawal dari data yang baik.</p>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                Pemetaan yang akurat menjadi dasar keputusan yang lebih terarah.
              </p>
            </div>
            <p className="mt-5 px-1 text-[10px] text-muted-foreground">
              WebGIS Merah Putih · Tahap fondasi
            </p>
          </div>
        </aside>
        <main id="main" className="min-w-0 px-5 py-7 sm:px-8 lg:px-9 lg:py-8">
          <div className="mb-7 flex items-center gap-2 text-xs text-muted-foreground">
            <span>Eksplorasi</span>
            <span className="text-slate-300">/</span>
            <span className="text-foreground">Peta koperasi</span>
          </div>
          <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold tracking-[0.18em] text-primary">
                <span className="h-px w-5 bg-primary" />
                TERHUBUNG DARI DESA
              </div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Peta Koperasi Merah Putih
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
                Jelajahi sebaran koperasi desa dan kelurahan dalam satu peta Indonesia.
              </p>
            </div>
            <div className="pt-1">
              <ServiceStatus />
            </div>
          </div>
          <section
            aria-label="Peta sebaran koperasi"
            className="overflow-hidden rounded-2xl border bg-card shadow-[0_3px_20px_#17212e04]"
          >
            <MapPanel styleUrl={styleUrl} />
          </section>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="flex gap-3 rounded-xl border bg-card p-4">
              <Database className="mt-0.5 size-4 shrink-0 text-primary" />
              <div>
                <p className="text-xs font-semibold">Data terverifikasi</p>
                <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
                  Belum ada dataset resmi yang dimuat pada tahap ini.
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-xl border bg-card p-4">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
              <div>
                <p className="text-xs font-semibold">Sumber yang jelas</p>
                <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
                  Setiap lokasi disiapkan untuk memiliki sumber data yang dapat ditelusuri.
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-xl border bg-card p-4">
              <CircleHelp className="mt-0.5 size-4 shrink-0 text-primary" />
              <div>
                <p className="text-xs font-semibold">Jelajahi area peta</p>
                <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
                  Geser dan perbesar peta untuk melihat lokasi pada area pilihan.
                </p>
              </div>
            </div>
          </div>
          <footer className="mt-7 flex flex-wrap items-center justify-between gap-3 border-t pt-4 text-[11px] text-muted-foreground">
            <span>Fondasi pemetaan nasional. Dikembangkan secara bertahap.</span>
            <span className="flex items-center gap-1.5">
              Desa berdaya, Indonesia maju
              <ArrowDownRight className="size-3" />
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
