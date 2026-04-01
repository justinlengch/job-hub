import { useEffect, useMemo, useRef, useState } from "react";
import { sankey as createSankey, sankeyLinkHorizontal } from "d3-sankey";
import { toast } from "sonner";
import { apiService } from "@/services/api";
import {
  SankeyLink,
  SankeyNode,
  SankeyResponse,
  SankeySnapshotCache,
  SankeySnapshotFilters,
} from "@/types/application";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ArrowRight,
  CalendarRange,
  Download,
  Loader2,
  RefreshCw,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";

const STAGE_FALLBACK_COLUMNS: Record<string, number> = {
  APPLIED: 0,
  GHOSTED: 1,
  ASSESSMENT: 1,
  REJECTED: 1,
  INTERVIEW: 2,
  FINAL_ROUND: 3,
  OFFERED: 4,
  ACCEPTED: 5,
  WITHDRAWN: 5,
};

const STAGE_FALLBACK_KINDS: Record<string, string> = {
  APPLIED: "root",
  GHOSTED: "ghosted",
  ASSESSMENT: "progress",
  INTERVIEW: "progress",
  FINAL_ROUND: "progress",
  OFFERED: "progress",
  ACCEPTED: "terminal",
  REJECTED: "rejected",
  WITHDRAWN: "terminal",
};

const STAGE_FALLBACK_ORDER: Record<string, number> = {
  APPLIED: 0,
  GHOSTED: 1,
  REJECTED: 2,
  ASSESSMENT: 3,
  INTERVIEW: 4,
  FINAL_ROUND: 5,
  OFFERED: 6,
  ACCEPTED: 7,
  WITHDRAWN: 8,
};

const PRESET_OPTIONS: Array<{
  id: SankeySnapshotFilters["preset"];
  label: string;
}> = [
  { id: "all", label: "All time" },
  { id: "last30", label: "Last 30 days" },
  { id: "last90", label: "Last 90 days" },
];

const SANKEY_CACHE_SCHEMA_VERSION = 2;

const NODE_PALETTE: Record<
  string,
  {
    fill: string;
    stroke: string;
    accent: string;
    text: string;
    muted: string;
  }
> = {
  root: {
    fill: "#ecfdf5",
    stroke: "#16a34a",
    accent: "#22c55e",
    text: "#064e3b",
    muted: "#047857",
  },
  ghosted: {
    fill: "#f8fafc",
    stroke: "#cbd5e1",
    accent: "#94a3b8",
    text: "#334155",
    muted: "#64748b",
  },
  rejected: {
    fill: "#fff1f2",
    stroke: "#fb7185",
    accent: "#ef4444",
    text: "#881337",
    muted: "#be123c",
  },
  progress: {
    fill: "#eff6ff",
    stroke: "#60a5fa",
    accent: "#2563eb",
    text: "#1e3a8a",
    muted: "#475569",
  },
  terminal: {
    fill: "#f0fdf4",
    stroke: "#34d399",
    accent: "#10b981",
    text: "#064e3b",
    muted: "#065f46",
  },
  fallback: {
    fill: "#f8fafc",
    stroke: "#cbd5e1",
    accent: "#64748b",
    text: "#0f172a",
    muted: "#475569",
  },
};

const FILTERABLE_STAGES = new Set([
  "APPLIED",
  "ASSESSMENT",
  "INTERVIEW",
  "FINAL_ROUND",
  "OFFERED",
  "ACCEPTED",
  "REJECTED",
  "WITHDRAWN",
]);

type LayoutNodeDatum = SankeyNode & {
  stageKey: string;
  kindKey: string;
  columnIndex: number;
  palette: (typeof NODE_PALETTE)["fallback"];
  labelLines: string[];
  sortIndex: number;
};

type LayoutLinkDatum = SankeyLink & {
  key: string;
  kindKey: string;
};

type LayoutNode = LayoutNodeDatum & {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  value: number;
};

type LayoutLink = LayoutLinkDatum & {
  width: number;
  y0: number;
  y1: number;
  source: LayoutNode;
  target: LayoutNode;
};

interface SankeyDiagramProps {
  userId: string;
  onStageSelect?: (stage: string) => void;
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const normalizeStageKey = (value: string) => value.trim().toUpperCase();

const formatStageLabel = (value: string) =>
  value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(" ");

const displayLabelForStage = (stageKey: string) => {
  if (stageKey === "GHOSTED") return "Ghosted";
  if (stageKey === "FINAL_ROUND") return "Final round";
  return formatStageLabel(stageKey);
};

const kindPriority = (kindKey: string) => {
  switch (kindKey) {
    case "root":
      return 0;
    case "ghosted":
      return 1;
    case "rejected":
      return 2;
    case "progress":
      return 3;
    case "terminal":
      return 4;
    default:
      return 5;
  }
};

const stageOrderValue = (stageKey: string) =>
  STAGE_FALLBACK_ORDER[stageKey] ?? 99;

const toLocalDateInputValue = (date: Date) => {
  const adjusted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return adjusted.toISOString().slice(0, 10);
};

const getPresetRange = (
  preset: Exclude<SankeySnapshotFilters["preset"], "custom">
): SankeySnapshotFilters => {
  if (preset === "all") {
    return { preset: "all" };
  }

  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - (preset === "last30" ? 29 : 89));

  return {
    preset,
    start_date: toLocalDateInputValue(start),
    end_date: toLocalDateInputValue(end),
  };
};

const normalizeFilters = (
  filters: SankeySnapshotFilters
): SankeySnapshotFilters => {
  if (filters.preset === "all") {
    return { preset: "all" };
  }

  const start_date = filters.start_date || undefined;
  const end_date = filters.end_date || undefined;
  const preset =
    filters.preset === "last30" || filters.preset === "last90"
      ? filters.preset
      : "custom";

  if (!start_date && !end_date) {
    return { preset: "all" };
  }

  return { preset, start_date, end_date };
};

const getFilterKey = (filters: SankeySnapshotFilters) => {
  const normalized = normalizeFilters(filters);
  if (normalized.preset === "all") return "all";
  return `start=${normalized.start_date || "none"}|end=${normalized.end_date || "none"}`;
};

const getRangeLabel = (filters: SankeySnapshotFilters) => {
  const normalized = normalizeFilters(filters);
  if (normalized.preset === "all") return "All time";
  if (normalized.preset === "last30") return "Last 30 days";
  if (normalized.preset === "last90") return "Last 90 days";
  if (normalized.start_date && normalized.end_date) {
    return `${normalized.start_date} to ${normalized.end_date}`;
  }
  if (normalized.start_date) return `From ${normalized.start_date}`;
  if (normalized.end_date) return `Until ${normalized.end_date}`;
  return "Custom range";
};

const getSankeyCacheKey = (userId: string, filters: SankeySnapshotFilters) =>
  `jobhub:sankey:v2:${userId}:${getFilterKey(filters)}`;

const readCachedSnapshot = (
  userId: string,
  filters: SankeySnapshotFilters
): SankeySnapshotCache | null => {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(getSankeyCacheKey(userId, filters));
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<SankeySnapshotCache>;
    if (
      parsed.schema_version !== SANKEY_CACHE_SCHEMA_VERSION ||
      !parsed.generated_at ||
      !parsed.payload ||
      !parsed.filters
    ) {
      window.localStorage.removeItem(getSankeyCacheKey(userId, filters));
      return null;
    }
    return parsed as SankeySnapshotCache;
  } catch {
    window.localStorage.removeItem(getSankeyCacheKey(userId, filters));
    return null;
  }
};

const writeCachedSnapshot = (
  userId: string,
  filters: SankeySnapshotFilters,
  payload: SankeyResponse
): SankeySnapshotCache | null => {
  if (typeof window === "undefined") return null;

  const normalized = normalizeFilters(filters);
  const snapshot: SankeySnapshotCache = {
    generated_at: new Date().toISOString(),
    schema_version: SANKEY_CACHE_SCHEMA_VERSION,
    filters: normalized,
    payload,
  };

  window.localStorage.setItem(
    getSankeyCacheKey(userId, normalized),
    JSON.stringify(snapshot)
  );
  return snapshot;
};

const clearCachedSnapshot = (userId: string, filters: SankeySnapshotFilters) => {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(getSankeyCacheKey(userId, filters));
};

const resolveStageKey = (node: SankeyNode) =>
  normalizeStageKey(node.stage || node.id || node.label);

const resolveKindKey = (node: SankeyNode) => {
  const stageKey = resolveStageKey(node);
  const rawKind = (node.kind || STAGE_FALLBACK_KINDS[stageKey] || "fallback")
    .toString()
    .toLowerCase();
  if (rawKind in NODE_PALETTE) return rawKind;
  if (rawKind === "root" || rawKind === "ghosted" || rawKind === "rejected") {
    return rawKind;
  }
  if (rawKind === "terminal" || rawKind === "progress") {
    return rawKind;
  }
  return STAGE_FALLBACK_KINDS[stageKey] || "fallback";
};

const resolveColumnIndex = (node: SankeyNode) => {
  if (typeof node.column === "number" && Number.isFinite(node.column)) {
    return node.column;
  }
  return STAGE_FALLBACK_COLUMNS[resolveStageKey(node)] ?? 2;
};

const resolvePalette = (kindKey: string, stageKey: string) => {
  if (kindKey in NODE_PALETTE) return NODE_PALETTE[kindKey];
  const mapped = STAGE_FALLBACK_KINDS[stageKey];
  if (mapped && mapped in NODE_PALETTE) return NODE_PALETTE[mapped];
  return NODE_PALETTE.fallback;
};

const wrapLabel = (label: string, maxCharsPerLine: number) => {
  if (!label) return [""];

  const words = label.split(" ");
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxCharsPerLine && current) {
      lines.push(current);
      current = word;
      continue;
    }
    current = next;
  }

  if (current) lines.push(current);
  return lines.length ? lines.slice(0, 2) : [label];
};

const formatPercent = (value: number) => `${value.toFixed(1)}%`;

const SankeyDiagram = ({ userId, onStageSelect }: SankeyDiagramProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [filters, setFilters] = useState<SankeySnapshotFilters>({ preset: "all" });
  const [cachedSnapshot, setCachedSnapshot] = useState<SankeySnapshotCache | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredLinkKey, setHoveredLinkKey] = useState<string | null>(null);
  const [selectedStageKey, setSelectedStageKey] = useState<string | null>(null);
  const [selectedLinkKey, setSelectedLinkKey] = useState<string | null>(null);

  const normalizedFilters = useMemo(() => normalizeFilters(filters), [filters]);
  const currentRangeLabel = useMemo(
    () => getRangeLabel(normalizedFilters),
    [normalizedFilters]
  );
  const hasInvalidDateRange = Boolean(
    normalizedFilters.start_date &&
      normalizedFilters.end_date &&
      normalizedFilters.start_date > normalizedFilters.end_date
  );

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const update = () => setContainerWidth(node.getBoundingClientRect().width);
    update();

    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setHoveredNodeId(null);
    setHoveredLinkKey(null);
    setSelectedStageKey(null);
    setSelectedLinkKey(null);
    setCachedSnapshot(readCachedSnapshot(userId, normalizedFilters));
    setLoading(false);
  }, [normalizedFilters, userId]);

  const data = cachedSnapshot?.payload ?? null;

  const layout = useMemo(() => {
    const chartWidth = clamp(containerWidth > 0 ? containerWidth - 32 : 960, 320, 1280);
    const chartHeight = clamp(
      containerWidth < 640 ? 340 : containerWidth < 1024 ? 440 : 520,
      320,
      560
    );

    if (!data?.nodes?.length) {
      return {
        chartWidth,
        chartHeight,
        nodes: [] as LayoutNode[],
        links: [] as LayoutLink[],
      };
    }

    const nodeWidth = chartWidth < 640 ? 14 : 18;
    const nodePadding = chartWidth < 640 ? 20 : 26;

    const nodes: LayoutNodeDatum[] = data.nodes.map((node) => {
      const stageKey = resolveStageKey(node);
      const kindKey = resolveKindKey(node);
      const columnIndex = resolveColumnIndex(node);
      return {
        ...node,
        stageKey,
        kindKey,
        columnIndex,
        palette: resolvePalette(kindKey, stageKey),
        labelLines: wrapLabel(
          displayLabelForStage(stageKey),
          chartWidth < 640 ? 11 : 15
        ),
        sortIndex:
          kindPriority(kindKey) * 100 +
          stageOrderValue(stageKey) * 10 -
          Math.min(node.count, 9),
      };
    });

    const links: LayoutLinkDatum[] = data.links.map((link) => ({
      ...link,
      key: `${link.source}__${link.target}`,
      kindKey:
        (link.kind ||
          nodes.find((node) => node.id === link.target)?.kindKey ||
          "progress")
          .toString()
          .toLowerCase(),
    }));

    const graph = createSankey<LayoutNodeDatum, LayoutLinkDatum>()
      .nodeId((node) => node.id)
      .nodeAlign((node, totalColumns) =>
        Math.max(0, Math.min(node.columnIndex, totalColumns - 1))
      )
      .nodeSort((a, b) => a.sortIndex - b.sortIndex || b.count - a.count)
      .linkSort((a, b) => b.value - a.value)
      .nodeWidth(nodeWidth)
      .nodePadding(nodePadding)
      .extent([
        [20, 24],
        [chartWidth - 20, chartHeight - 24],
      ])({
        nodes: nodes.map((node) => ({ ...node })),
        links: links.map((link) => ({ ...link })),
      });

    return {
      chartWidth,
      chartHeight,
      nodes: graph.nodes as LayoutNode[],
      links: graph.links as LayoutLink[],
    };
  }, [containerWidth, data]);

  const totalApplications = data?.meta?.total_applications ?? 0;
  const inferredCount = data?.meta?.inferred_count ?? 0;
  const ghostedCount = data?.meta?.ghosted_count ?? 0;
  const pendingReviewCount = data?.meta?.pending_review_count ?? 0;
  const generatedAt = cachedSnapshot?.generated_at ?? null;

  const hoveredNode = layout.nodes.find((node) => node.id === hoveredNodeId) || null;
  const hoveredLink = layout.links.find((link) => link.key === hoveredLinkKey) || null;
  const selectedLink = layout.links.find((link) => link.key === selectedLinkKey) || null;

  const resetSelection = () => {
    setHoveredNodeId(null);
    setHoveredLinkKey(null);
    setSelectedStageKey(null);
    setSelectedLinkKey(null);
  };

  const formatGeneratedAt = (value: string) =>
    new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));

  const handlePresetSelect = (preset: "all" | "last30" | "last90") => {
    setFilters(getPresetRange(preset));
  };

  const handleCustomDateChange = (
    field: "start_date" | "end_date",
    value: string
  ) => {
    setFilters((current) =>
      normalizeFilters({
        preset: "custom",
        start_date:
          field === "start_date" ? value || undefined : current.start_date,
        end_date: field === "end_date" ? value || undefined : current.end_date,
      })
    );
  };

  const handleGenerate = async () => {
    if (hasInvalidDateRange) {
      setError("Start date must be before end date.");
      return;
    }

    setGenerating(true);
    setError(null);
    try {
      const payload = await apiService.generateSankeyData({
        start_date: normalizedFilters.start_date,
        end_date: normalizedFilters.end_date,
      });
      const snapshot = writeCachedSnapshot(userId, normalizedFilters, payload);
      setCachedSnapshot(snapshot);
      resetSelection();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to generate Sankey snapshot";
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleClearSnapshot = () => {
    clearCachedSnapshot(userId, normalizedFilters);
    setCachedSnapshot(null);
    setError(null);
    resetSelection();
  };

  const handleExport = async () => {
    if (!svgRef.current || !data) return;

    setExporting(true);
    try {
      const serializer = new XMLSerializer();
      const source = serializer.serializeToString(svgRef.current);
      const svgMarkup = source.includes("xmlns=")
        ? source
        : source.replace(
            "<svg",
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
          );

      const blob = new Blob([svgMarkup], {
        type: "image/svg+xml;charset=utf-8",
      });
      const blobUrl = URL.createObjectURL(blob);

      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("Could not render Sankey export."));
        img.src = blobUrl;
      });

      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = layout.chartWidth * scale;
      canvas.height = layout.chartHeight * scale;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Canvas export is not available.");

      context.scale(scale, scale);
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, layout.chartWidth, layout.chartHeight);
      context.drawImage(image, 0, 0, layout.chartWidth, layout.chartHeight);

      const pngBlob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((result) => {
          if (result) resolve(result);
          else reject(new Error("Failed to encode Sankey PNG."));
        }, "image/png");
      });

      const downloadUrl = URL.createObjectURL(pngBlob);
      const link = document.createElement("a");
      const dateLabel = new Date().toISOString().slice(0, 10);
      const rangeLabel = getFilterKey(normalizedFilters)
        .replace(/[^a-zA-Z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      link.href = downloadUrl;
      link.download = `jobhub-sankey-${rangeLabel || "all"}-${dateLabel}.png`;
      document.body.appendChild(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(downloadUrl);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to export Sankey image";
      toast.error(message);
    } finally {
      setExporting(false);
    }
  };

  const displayPercent = (count: number) =>
    totalApplications ? formatPercent((count / totalApplications) * 100) : "0.0%";

  const linkLabel = (link: LayoutLink) => {
    const source = displayLabelForStage(link.source.stageKey);
    const target = displayLabelForStage(link.target.stageKey);
    return `${source} -> ${target}`;
  };

  const handleNodeSelect = (node: LayoutNode) => {
    setSelectedStageKey(node.stageKey);
    setSelectedLinkKey(null);
    if (FILTERABLE_STAGES.has(node.stageKey)) {
      onStageSelect?.(node.stageKey);
    }
  };

  const handleLinkSelect = (link: LayoutLink) => {
    setSelectedLinkKey(link.key);
    setSelectedStageKey(link.target.stageKey);
    if (FILTERABLE_STAGES.has(link.target.stageKey)) {
      onStageSelect?.(link.target.stageKey);
    }
  };

  const linkPath = sankeyLinkHorizontal<LayoutNode, LayoutLink>();

  return (
    <Card className="overflow-hidden border-slate-200 bg-gradient-to-br from-slate-50 via-white to-slate-100 shadow-sm">
      <CardHeader className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="rounded-full bg-emerald-100 p-2 text-emerald-700 shadow-sm">
                <SlidersHorizontal className="h-4 w-4" />
              </div>
              <CardTitle className="text-lg">Application Outcomes</CardTitle>
              {pendingReviewCount > 0 && (
                <Badge variant="secondary">{pendingReviewCount} review</Badge>
              )}
            </div>
            <CardDescription className="max-w-2xl">
              Applied branches into rejection, active progress, or Ghosted when there is no downstream signal in this snapshot.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">{currentRangeLabel}</Badge>
            <Badge variant="outline">{totalApplications} applications</Badge>
            <Badge variant="outline">{ghostedCount} ghosted</Badge>
            <Badge variant="outline">{inferredCount} inferred</Badge>
            {generatedAt && (
              <Badge variant="outline">Generated {formatGeneratedAt(generatedAt)}</Badge>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {PRESET_OPTIONS.map((preset) => (
            <Button
              key={preset.id}
              variant={normalizedFilters.preset === preset.id ? "default" : "outline"}
              size="sm"
              onClick={() =>
                handlePresetSelect(preset.id as "all" | "last30" | "last90")
              }
            >
              {preset.label}
            </Button>
          ))}
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
            <CalendarRange className="h-4 w-4 text-slate-500" />
            <Input
              type="date"
              value={normalizedFilters.start_date || ""}
              onChange={(event) =>
                handleCustomDateChange("start_date", event.target.value)
              }
              className="h-8 w-[150px] border-0 px-0 shadow-none focus-visible:ring-0"
            />
            <span className="text-sm text-muted-foreground">to</span>
            <Input
              type="date"
              value={normalizedFilters.end_date || ""}
              onChange={(event) =>
                handleCustomDateChange("end_date", event.target.value)
              }
              className="h-8 w-[150px] border-0 px-0 shadow-none focus-visible:ring-0"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={data ? "outline" : "default"}
            onClick={handleGenerate}
            disabled={generating || hasInvalidDateRange}
            className="gap-2"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {data ? "Refresh Sankey" : "Generate Sankey"}
          </Button>
          <Button
            variant="ghost"
            onClick={handleClearSnapshot}
            disabled={generating || !data}
            className="gap-2"
          >
            <Trash2 className="h-4 w-4" />
            Clear snapshot
          </Button>
          <Button
            variant="ghost"
            onClick={handleExport}
            disabled={exporting || !data}
            className="gap-2"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export image
          </Button>
          {hasInvalidDateRange && (
            <span className="text-sm text-red-600">
              Start date must be before end date.
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div
          ref={containerRef}
          className="relative w-full overflow-hidden rounded-2xl border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.08),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.08),_transparent_30%),linear-gradient(180deg,_rgba(255,255,255,0.9),_rgba(248,250,252,0.85))] p-4"
        >
          {loading ? (
            <div
              className="flex items-center justify-center text-sm text-muted-foreground"
              style={{ minHeight: `${layout.chartHeight}px` }}
            >
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading Sankey snapshot...
            </div>
          ) : error ? (
            <div
              className="flex items-center justify-center rounded-xl border border-dashed bg-white/85 text-sm text-muted-foreground"
              style={{ minHeight: `${layout.chartHeight}px` }}
            >
              {error}
            </div>
          ) : !layout.nodes.length ? (
            <div
              className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed bg-white/85 px-6 text-center text-sm text-muted-foreground"
              style={{ minHeight: `${layout.chartHeight}px` }}
            >
              <div className="space-y-1">
                <p className="font-medium text-foreground">
                  No Sankey snapshot for {currentRangeLabel.toLowerCase()} yet.
                </p>
                <p>Generate one to capture this date-scoped branching view.</p>
              </div>
              <Button onClick={handleGenerate} disabled={generating} className="gap-2">
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Generate Sankey
              </Button>
            </div>
          ) : (
            <>
              <svg
                ref={svgRef}
                width={layout.chartWidth}
                height={layout.chartHeight}
                viewBox={`0 0 ${layout.chartWidth} ${layout.chartHeight}`}
                className="mx-auto block max-w-full overflow-visible"
              >
                <defs>
                  {layout.links.map((link) => (
                    <linearGradient
                      key={`gradient-${link.key}`}
                      id={`gradient-${link.key}`}
                      x1={`${link.source.x1}`}
                      y1="0"
                      x2={`${link.target.x0}`}
                      y2="0"
                      gradientUnits="userSpaceOnUse"
                    >
                      <stop
                        offset="0%"
                        stopColor={link.source.palette.stroke}
                        stopOpacity="0.24"
                      />
                      <stop
                        offset="100%"
                        stopColor={link.target.palette.stroke}
                        stopOpacity="0.56"
                      />
                    </linearGradient>
                  ))}
                </defs>

                {layout.links.map((link) => {
                  const isActive =
                    selectedLinkKey === link.key ||
                    selectedStageKey === link.source.stageKey ||
                    selectedStageKey === link.target.stageKey;
                  const isHovered = hoveredLinkKey === link.key;
                  const isGhosted =
                    link.kindKey === "ghosted" || link.target.kindKey === "ghosted";
                  const isRejected =
                    link.kindKey === "rejected" || link.target.kindKey === "rejected";
                  const opacity = isHovered || isActive ? 0.92 : isGhosted ? 0.28 : isRejected ? 0.42 : 0.38;

                  return (
                    <path
                      key={link.key}
                      d={linkPath(link) || ""}
                      fill="none"
                      stroke={
                        isGhosted || isRejected
                          ? link.target.palette.stroke
                          : `url(#gradient-${link.key})`
                      }
                      strokeWidth={Math.max(3, link.width || 0)}
                      strokeLinecap="round"
                      opacity={opacity}
                      className="cursor-pointer transition-opacity duration-200"
                      onMouseEnter={() => {
                        setHoveredLinkKey(link.key);
                        setHoveredNodeId(null);
                      }}
                      onMouseLeave={() => setHoveredLinkKey(null)}
                      onClick={() => handleLinkSelect(link)}
                    />
                  );
                })}

                {layout.nodes.map((node) => {
                  const nodeWidth = Math.max(12, node.x1 - node.x0);
                  const nodeHeight = Math.max(14, node.y1 - node.y0);
                  const isActive = selectedStageKey === node.stageKey;
                  const isHovered = hoveredNodeId === node.id;
                  const isGhosted = node.kindKey === "ghosted";
                  const isRejected = node.kindKey === "rejected";
                  const labelOnRight = node.x1 + 150 < layout.chartWidth;
                  const labelX = labelOnRight ? node.x1 + 10 : node.x0 - 10;
                  const anchor = labelOnRight ? "start" : "end";

                  return (
                    <g
                      key={node.id}
                      className="cursor-pointer"
                      onMouseEnter={() => {
                        setHoveredNodeId(node.id);
                        setHoveredLinkKey(null);
                      }}
                      onMouseLeave={() => setHoveredNodeId(null)}
                      onClick={() => handleNodeSelect(node)}
                    >
                      <rect
                        x={node.x0}
                        y={node.y0}
                        width={nodeWidth}
                        height={nodeHeight}
                        rx={Math.min(14, nodeWidth / 2)}
                        fill={node.palette.fill}
                        stroke={node.palette.stroke}
                        strokeWidth={isActive || isHovered ? 2.5 : 1.5}
                        strokeDasharray={isGhosted ? "7 6" : undefined}
                        opacity={isGhosted ? 0.84 : 1}
                      />
                      {nodeWidth > 10 && (
                        <rect
                          x={node.x0}
                          y={node.y0}
                          width={Math.min(8, nodeWidth)}
                          height={nodeHeight}
                          rx={Math.min(14, nodeWidth / 2)}
                          fill={node.palette.accent}
                          opacity={isGhosted ? 0.45 : 0.9}
                        />
                      )}
                      <text
                        x={labelX}
                        y={node.y0 + 16}
                        textAnchor={anchor}
                        style={{
                          fill: node.palette.text,
                          fontSize: "13px",
                          fontWeight: 700,
                          letterSpacing: "-0.01em",
                        }}
                      >
                        {node.labelLines.map((line, index) => (
                          <tspan
                            key={`${node.id}-label-${index}`}
                            x={labelX}
                            dy={index === 0 ? 0 : 15}
                          >
                            {line}
                          </tspan>
                        ))}
                      </text>
                      <text
                        x={labelX}
                        y={node.y0 + (node.labelLines.length > 1 ? 48 : 34)}
                        textAnchor={anchor}
                        style={{
                          fill: node.palette.muted,
                          fontSize: "11px",
                          fontWeight: 500,
                        }}
                      >
                        {node.count} applications
                      </text>
                      {isRejected && (
                        <text
                          x={labelX}
                          y={node.y0 + (node.labelLines.length > 1 ? 62 : 48)}
                          textAnchor={anchor}
                          style={{
                            fill: node.palette.muted,
                            fontSize: "10px",
                            fontWeight: 600,
                            letterSpacing: "0.08em",
                            textTransform: "uppercase",
                          }}
                        >
                          Terminal
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>

              {(hoveredLink || hoveredNode || selectedLink) && (
                <div className="pointer-events-none absolute right-4 top-4 max-w-xs rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl backdrop-blur">
                  {hoveredLink ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">{linkLabel(hoveredLink)}</p>
                      <p className="text-muted-foreground">
                        {hoveredLink.value} applications
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {displayPercent(hoveredLink.value)} of all applications
                      </p>
                      {hoveredLink.kindKey === "ghosted" && (
                        <p className="text-xs text-muted-foreground">
                          Ghosted = no downstream signal in this snapshot
                        </p>
                      )}
                    </div>
                  ) : hoveredNode ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">{hoveredNode.label}</p>
                      <p className="text-muted-foreground">
                        {hoveredNode.count} applications reached this node
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {displayPercent(hoveredNode.count)} of all applications
                      </p>
                      {hoveredNode.kindKey === "ghosted" && (
                        <p className="text-xs text-muted-foreground">
                          Ghosted = no downstream signal in this snapshot
                        </p>
                      )}
                    </div>
                  ) : selectedLink ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">{linkLabel(selectedLink)}</p>
                      <p className="text-muted-foreground">
                        {selectedLink.value} applications selected
                      </p>
                    </div>
                  ) : null}
                </div>
              )}
            </>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Legend:</span>
          <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-900">
            Applied
          </Badge>
          <Badge variant="outline" className="border-slate-200 bg-slate-50 text-slate-800">
            Ghosted
          </Badge>
          <Badge variant="outline" className="border-rose-200 bg-rose-50 text-rose-900">
            Rejected
          </Badge>
          <Badge variant="outline" className="border-violet-200 bg-violet-50 text-violet-900">
            Assessment
          </Badge>
          <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-900">
            Interview
          </Badge>
          <Badge variant="outline" className="border-sky-200 bg-sky-50 text-sky-900">
            Final round
          </Badge>
          <Badge variant="outline" className="border-teal-200 bg-teal-50 text-teal-900">
            Offer
          </Badge>
          <span className="ml-2 inline-flex items-center gap-2">
            <span className="font-medium text-foreground">Tip:</span>
            Click a node to filter the dashboard, or hover a branch for snapshot counts.
          </span>
          <ArrowRight className="h-3 w-3" />
        </div>
      </CardContent>
    </Card>
  );
};

export default SankeyDiagram;
