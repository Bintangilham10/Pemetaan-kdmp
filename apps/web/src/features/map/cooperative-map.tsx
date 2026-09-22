"use client";

import { useEffect, useRef, useState } from "react";
import {
  Map,
  NavigationControl,
  AttributionControl,
  Popup,
  getVersion,
  setWorkerUrl,
  type GeoJSONSource,
} from "maplibre-gl";
import type { components } from "@kdmp/contracts";
import { CircleAlert, Layers2, LoaderCircle, MapPin, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

type Collection = components["schemas"]["CooperativeCollection"];
type DataStatus = { state: "loading" | "ready" | "error"; count: number; truncated: boolean };
const INDONESIA: [[number, number], [number, number]] = [
  [94, -12],
  [142, 7],
];
const EMPTY: Collection = {
  type: "FeatureCollection",
  features: [],
  numberReturned: 0,
  truncated: false,
};

setWorkerUrl(`/vendor/maplibre/${getVersion()}/maplibre-gl-worker.mjs`);

export default function CooperativeMap({ styleUrl }: { styleUrl: string }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const refreshRef = useRef<(() => void) | null>(null);
  const [data, setData] = useState<DataStatus>({ state: "loading", count: 0, truncated: false });
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!container.current) return;
    let active = true;
    let pending: AbortController | undefined;
    let debounce: ReturnType<typeof setTimeout> | undefined;
    let popup: Popup | undefined;
    let map: Map;
    try {
      map = new Map({
        container: container.current,
        style: styleUrl,
        bounds: INDONESIA,
        fitBoundsOptions: { padding: 28 },
        maxBounds: [
          // Leave vertical room so portrait screens can fit the full archipelago.
          [88, -65],
          [151, 65],
        ],
        minZoom: 1,
        maxZoom: 18,
        renderWorldCopies: false,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
      });
    } catch {
      queueMicrotask(() => {
        if (active) setMapError("Peta tidak dapat dimuat. Pastikan browser mendukung WebGL.");
      });
      return () => {
        active = false;
      };
    }
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new AttributionControl({ compact: true }), "bottom-right");
    map.getCanvas().setAttribute("aria-label", "Peta interaktif koperasi Indonesia");
    const styleTimeout = setTimeout(() => {
      if (active && !map.isStyleLoaded())
        setMapError("Peta dasar belum dapat dimuat. Periksa koneksi lalu coba lagi.");
    }, 20000);

    async function loadPoints() {
      pending?.abort();
      const controller = new AbortController();
      pending = controller;
      if (!active) return;
      setData((previous) => ({ ...previous, state: "loading" }));
      const bounds = map.getBounds();
      const bbox = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]
        .map((value) => value.toFixed(6))
        .join(",");
      try {
        const response = await fetch(
          `/api/v1/cooperatives?${new URLSearchParams({ bbox, limit: "500" })}`,
          { signal: controller.signal, cache: "no-store" },
        );
        if (!response.ok) throw new Error("Data unavailable");
        const collection: Collection = await response.json();
        if (!active || controller.signal.aborted) return;
        map.getSource<GeoJSONSource>("cooperatives")?.setData(collection);
        setData({
          state: "ready",
          count: collection.numberReturned,
          truncated: collection.truncated,
        });
      } catch {
        if (active && !controller.signal.aborted) {
          map.getSource<GeoJSONSource>("cooperatives")?.setData(EMPTY);
          setData({ state: "error", count: 0, truncated: false });
        }
      }
    }

    map.on("load", () => {
      if (!active) return;
      clearTimeout(styleTimeout);
      setMapError(null);
      setMapReady(true);
      map.addSource("cooperatives", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "cooperative-points",
        type: "circle",
        source: "cooperatives",
        paint: {
          "circle-radius": 6,
          "circle-color": "#b42335",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
      refreshRef.current = () => void loadPoints();
      void loadPoints();
      map.on("moveend", () => {
        pending?.abort();
        clearTimeout(debounce);
        debounce = setTimeout(() => void loadPoints(), 200);
      });
      map.on("mouseenter", "cooperative-points", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "cooperative-points", () => {
        map.getCanvas().style.cursor = "";
      });
      map.on("click", "cooperative-points", (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        const [longitude, latitude] = feature.geometry.coordinates;
        if (longitude === undefined || latitude === undefined) return;
        const content = document.createElement("p");
        content.textContent = String(feature.properties.name ?? "Koperasi");
        popup?.remove();
        popup = new Popup({ closeButton: false })
          .setLngLat([longitude, latitude])
          .setDOMContent(content)
          .addTo(map);
      });
    });
    map.on("error", () => {
      if (active) setMapError("Sebagian peta dasar gagal dimuat. Periksa koneksi atau coba lagi.");
    });
    return () => {
      active = false;
      clearTimeout(styleTimeout);
      clearTimeout(debounce);
      pending?.abort();
      popup?.remove();
      refreshRef.current = null;
      mapRef.current = null;
      map.remove();
    };
  }, [styleUrl, attempt]);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b bg-card px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Layers2 className="size-4 text-primary" />
          Sebaran koperasi
          <span className="ml-1 rounded-md bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
            Indonesia
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={!mapReady || !!mapError}
          onClick={() =>
            mapRef.current?.fitBounds(INDONESIA, {
              padding: 28,
              duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 600,
            })
          }
        >
          <RotateCcw />
          Atur ulang peta
        </Button>
      </div>
      <div className="relative bg-[#e5eef1]">
        <div
          ref={container}
          className="h-[clamp(390px,56vh,650px)] w-full"
          data-testid="cooperative-map"
          data-ready={mapReady}
        />
        {!mapError && data.state === "ready" && data.count === 0 && (
          <div
            className="pointer-events-none absolute inset-x-4 bottom-11 mx-auto max-w-sm rounded-xl border border-white/80 bg-white/95 px-5 py-4 text-center shadow-lg shadow-slate-900/5"
            role="status"
          >
            <MapPin className="mx-auto mb-2 size-5 text-primary" />
            <p className="text-sm font-semibold">Belum ada data koperasi di area ini</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Lokasi akan tampil setelah data koperasi tervalidasi tersedia.
            </p>
          </div>
        )}
        {(mapError || data.state === "error") && (
          <div
            className="absolute inset-x-4 bottom-11 mx-auto max-w-md rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm"
            role="alert"
          >
            <p className="flex gap-2 text-sm text-amber-950">
              <CircleAlert className="mt-0.5 size-4 shrink-0" />
              {mapError ?? "Data koperasi belum dapat dimuat. Silakan coba lagi."}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3 bg-white"
              onClick={() => {
                if (mapError) {
                  setMapError(null);
                  setMapReady(false);
                  setData({ state: "loading", count: 0, truncated: false });
                  setAttempt((value) => value + 1);
                } else refreshRef.current?.();
              }}
            >
              Coba lagi
            </Button>
          </div>
        )}
        {!mapError && data.state === "loading" && (
          <div
            className="absolute bottom-12 left-4 flex items-center gap-2 rounded-lg bg-white/95 px-3 py-2 text-xs shadow-sm"
            role="status"
          >
            <LoaderCircle className="size-3.5 animate-spin" />
            Memuat peta dan data…
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t bg-card px-5 py-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="size-2 rounded-full bg-primary" />
          Lokasi koperasi<span className="mx-1 text-border">|</span>
          {data.state === "ready"
            ? `${data.count} titik di area peta`
            : data.state === "error"
              ? "Data tidak tersedia"
              : "Memuat data"}
        </span>
        <span>Peta dasar demonstrasi · bukan batas resmi</span>
      </div>
      {data.truncated && (
        <p role="status" className="border-t bg-amber-50 px-5 py-3 text-xs text-amber-900">
          Menampilkan {data.count} titik pertama. Perbesar peta untuk melihat area yang lebih rinci.
        </p>
      )}
    </div>
  );
}
