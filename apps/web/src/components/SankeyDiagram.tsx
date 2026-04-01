import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { apiService } from "@/services/api";
import {
  SankeyLink,
  SankeyNode,
  SankeyResponse,
  SankeySnapshotCache,
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
import {
  ArrowRight,
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

const SANKEY_CACHE_SCHEMA_VERSION = 1;

type LayoutNode = SankeyNode & {
  stageKey: string;
  kindKey: string;
  columnIndex: number;
  x: number;
  y: number;
  width: number;
  height: number;
  incoming: number;
  outgoing: number;
  palette: (typeof NODE_PALETTE)["fallback"];
  labelLines: string[];
};

type LayoutLink = SankeyLink & {
  key: string;
  kindKey: string;
  sourceNode: LayoutNode;
  targetNode: LayoutNode;
  thickness: number;
  sourceY: number;
  targetY: number;
  palette: (typeof NODE_PALETTE)["fallback"];
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

const getSankeyCacheKey = (userId: string) => `jobhub:sankey:v1:${userId}`;

const readCachedSnapshot = (userId: string): SankeySnapshotCache | null => {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(getSankeyCacheKey(userId));
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<SankeySnapshotCache>;
    if (
      parsed.schema_version !== SANKEY_CACHE_SCHEMA_VERSION ||
      !parsed.generated_at ||
      !parsed.payload
    ) {
      window.localStorage.removeItem(getSankeyCacheKey(userId));
      return null;
    }
    return parsed as SankeySnapshotCache;
  } catch {
    window.localStorage.removeItem(getSankeyCacheKey(userId));
    return null;
  }
};

const writeCachedSnapshot = (
  userId: string,
  payload: SankeyResponse
): SankeySnapshotCache | null => {
  if (typeof window === "undefined") return null;

  const snapshot: SankeySnapshotCache = {
    generated_at: new Date().toISOString(),
    schema_version: SANKEY_CACHE_SCHEMA_VERSION,
    payload,
  };
  window.localStorage.setItem(getSankeyCacheKey(userId), JSON.stringify(snapshot));
  return snapshot;
};

const clearCachedSnapshot = (userId: string) => {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(getSankeyCacheKey(userId));
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

  const stageKey = resolveStageKey(node);
  return STAGE_FALLBACK_COLUMNS[stageKey] ?? 2;
};

const resolvePalette = (kindKey: string, stageKey: string) => {
  if (kindKey in NODE_PALETTE) {
    return NODE_PALETTE[kindKey];
  }

  if (stageKey in STAGE_FALLBACK_KINDS) {
    const mapped = STAGE_FALLBACK_KINDS[stageKey];
    if (mapped in NODE_PALETTE) {
      return NODE_PALETTE[mapped];
    }
  }

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

  if (current) {
    lines.push(current);
  }

  return lines.length ? lines.slice(0, 2) : [label];
};

const formatPercent = (value: number) => `${value.toFixed(1)}%`;

const SankeyDiagram = ({ userId, onStageSelect }: SankeyDiagramProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [cachedSnapshot, setCachedSnapshot] = useState<SankeySnapshotCache | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredLinkKey, setHoveredLinkKey] = useState<string | null>(null);
  const [selectedStageKey, setSelectedStageKey] = useState<string | null>(null);
  const [selectedLinkKey, setSelectedLinkKey] = useState<string | null>(null);

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
    setCachedSnapshot(readCachedSnapshot(userId));
    setLoading(false);
  }, [userId]);

  const data = cachedSnapshot?.payload ?? null;

  const layout = useMemo(() => {
    const baseWidth = Math.max(containerWidth || 1024, 900);
    const leftPad = 28;
    const rightPad = 28;
    const topPad = 24;
    const bottomPad = 28;
    const columnGap = 84;
    const rowGap = 18;

    if (!data?.nodes?.length) {
      return {
        chartHeight: 460,
        chartWidth: baseWidth,
        nodes: [] as LayoutNode[],
        links: [] as LayoutLink[],
      };
    }

    const nodesByColumn = new Map<number, LayoutNode[]>();
    const stageNodeMap = new Map<string, LayoutNode>();

    for (const node of data.nodes) {
      const stageKey = resolveStageKey(node);
      const kindKey = resolveKindKey(node);
      const columnIndex = resolveColumnIndex(node);
      const label = displayLabelForStage(stageKey);
      const palette = resolvePalette(kindKey, stageKey);
      const nodeWidth =
        columnIndex === 0
          ? 210
          : kindKey === "ghosted" || kindKey === "rejected"
            ? 176
            : 188;
      const baseHeight = kindKey === "root" ? 96 : kindKey === "ghosted" ? 86 : 82;
      const labelLines = wrapLabel(label, kindKey === "root" ? 16 : 14);
      const height = Math.max(baseHeight, 46 + labelLines.length * 16 + 12);
      const layoutNode: LayoutNode = {
        ...node,
        stageKey,
        kindKey,
        columnIndex,
        x: 0,
        y: 0,
        width: nodeWidth,
        height,
        incoming: 0,
        outgoing: 0,
        palette,
        labelLines,
      };

      const bucket = nodesByColumn.get(columnIndex) || [];
      bucket.push(layoutNode);
      nodesByColumn.set(columnIndex, bucket);
      stageNodeMap.set(stageKey, layoutNode);
      stageNodeMap.set(node.id, layoutNode);
      stageNodeMap.set((node.label || "").toUpperCase(), layoutNode);
    }

    const columns = Array.from(nodesByColumn.keys()).sort((a, b) => a - b);

    for (const column of columns) {
      const bucket = nodesByColumn.get(column) || [];
      bucket.sort(
        (a, b) =>
          kindPriority(a.kindKey) - kindPriority(b.kindKey) ||
          stageOrderValue(a.stageKey) - stageOrderValue(b.stageKey) ||
          b.count - a.count ||
          a.label.localeCompare(b.label)
      );
    }

    const columnWidths = columns.map((column) => {
      const bucket = nodesByColumn.get(column) || [];
      return Math.max(...bucket.map((node) => node.width), 176);
    });
    const columnHeights = columns.map((column) => {
      const bucket = nodesByColumn.get(column) || [];
      return (
        bucket.reduce((sum, node) => sum + node.height, 0) +
        Math.max(0, bucket.length - 1) * rowGap
      );
    });
    const chartHeight = Math.max(
      460,
      topPad + bottomPad + Math.max(...columnHeights, 0) + 40
    );
    const chartWidth = Math.max(
      baseWidth,
      leftPad +
        rightPad +
        columnWidths.reduce((sum, width) => sum + width, 0) +
        Math.max(0, columns.length - 1) * columnGap
    );

    let cursorX = leftPad;
    columns.forEach((column, index) => {
      const bucket = nodesByColumn.get(column) || [];
      const columnWidth = columnWidths[index];
      const columnHeight = columnHeights[index];
      const yStart =
        topPad +
        Math.max(0, (chartHeight - topPad - bottomPad - columnHeight) / 2);
      let cursorY = yStart;

      bucket.forEach((node) => {
        node.x = cursorX + (columnWidth - node.width) / 2;
        node.y = cursorY;
        cursorY += node.height + rowGap;
      });

      cursorX += columnWidth + columnGap;
    });

    const linkItems: LayoutLink[] = data.links
      .map((link) => {
        const sourceKey = normalizeStageKey(link.source);
        const targetKey = normalizeStageKey(link.target);
        const sourceNode =
          stageNodeMap.get(sourceKey) ||
          stageNodeMap.get(link.source) ||
          (data.nodes.length
            ? stageNodeMap.get(resolveStageKey(data.nodes[0]))
            : undefined);
        const targetNode =
          stageNodeMap.get(targetKey) ||
          stageNodeMap.get(link.target) ||
          (data.nodes.length
            ? stageNodeMap.get(resolveStageKey(data.nodes[data.nodes.length - 1]))
            : undefined);

        if (!sourceNode || !targetNode) return null;

        const kindKey = (
          link.kind || targetNode.kindKey || sourceNode.kindKey || "progress"
        )
          .toString()
          .toLowerCase();
        const palette = resolvePalette(kindKey, targetNode.stageKey);
        return {
          ...link,
          key: `${link.source}__${link.target}`,
          kindKey,
          sourceNode,
          targetNode,
          thickness: 0,
          sourceY: 0,
          targetY: 0,
          palette,
        };
      })
      .filter(Boolean) as LayoutLink[];

    const maxValue = Math.max(
      1,
      ...linkItems.map((link) => link.value),
      ...data.nodes.map((node) => node.count)
    );
    const flowUnit = clamp(
      (chartHeight - topPad - bottomPad - 72) / maxValue,
      3,
      18
    );

    const outgoingByNode = new Map<string, LayoutLink[]>();
    const incomingByNode = new Map<string, LayoutLink[]>();
    for (const link of linkItems) {
      const sourceList = outgoingByNode.get(link.sourceNode.id) || [];
      sourceList.push(link);
      outgoingByNode.set(link.sourceNode.id, sourceList);

      const targetList = incomingByNode.get(link.targetNode.id) || [];
      targetList.push(link);
      incomingByNode.set(link.targetNode.id, targetList);
    }

    const sortLinks = (a: LayoutLink, b: LayoutLink) =>
      a.targetNode.columnIndex - b.targetNode.columnIndex ||
      kindPriority(a.targetNode.kindKey) - kindPriority(b.targetNode.kindKey) ||
      b.value - a.value ||
      a.targetNode.label.localeCompare(b.targetNode.label);

    for (const node of stageNodeMap.values()) {
      const outgoing = (outgoingByNode.get(node.id) || []).sort(sortLinks);
      const incoming = (incomingByNode.get(node.id) || []).sort(sortLinks);
      node.outgoing = outgoing.reduce(
        (sum, link) => sum + Math.max(3, link.value * flowUnit),
        0
      );
      node.incoming = incoming.reduce(
        (sum, link) => sum + Math.max(3, link.value * flowUnit),
        0
      );
    }

    for (const node of stageNodeMap.values()) {
      const outgoing = (outgoingByNode.get(node.id) || []).sort(sortLinks);
      const totalThickness = outgoing.reduce(
        (sum, link) => sum + Math.max(3, link.value * flowUnit),
        0
      );
      let offset = -totalThickness / 2;
      for (const link of outgoing) {
        const thickness = Math.max(3, link.value * flowUnit);
        link.thickness = thickness;
        link.sourceY = node.y + node.height / 2 + offset + thickness / 2;
        offset += thickness;
      }
    }

    for (const node of stageNodeMap.values()) {
      const incoming = (incomingByNode.get(node.id) || []).sort(sortLinks);
      const totalThickness = incoming.reduce(
        (sum, link) => sum + Math.max(3, link.value * flowUnit),
        0
      );
      let offset = -totalThickness / 2;
      for (const link of incoming) {
        const thickness = Math.max(3, link.value * flowUnit);
        link.targetY = node.y + node.height / 2 + offset + thickness / 2;
        offset += thickness;
      }
    }

    const uniqueNodes = Array.from(
      new Map(
        Array.from(stageNodeMap.values()).map((node) => [node.id, node] as const)
      ).values()
    );

    return {
      chartHeight,
      chartWidth,
      nodes: uniqueNodes,
      links: linkItems,
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

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const payload = await apiService.generateSankeyData();
      const snapshot = writeCachedSnapshot(userId, payload);
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
    clearCachedSnapshot(userId);
    setCachedSnapshot(null);
    setError(null);
    resetSelection();
  };

  const displayPercent = (count: number) =>
    totalApplications ? formatPercent((count / totalApplications) * 100) : "0.0%";

  const linkLabel = (link: LayoutLink) => {
    const source = displayLabelForStage(link.sourceNode.stageKey);
    const target = displayLabelForStage(link.targetNode.stageKey);
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
    setSelectedStageKey(link.targetNode.stageKey);
    if (FILTERABLE_STAGES.has(link.targetNode.stageKey)) {
      onStageSelect?.(link.targetNode.stageKey);
    }
  };

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
            <Badge variant="outline">{totalApplications} applications</Badge>
            <Badge variant="outline">{ghostedCount} ghosted</Badge>
            <Badge variant="outline">{inferredCount} inferred</Badge>
            {generatedAt && (
              <Badge variant="outline">Generated {formatGeneratedAt(generatedAt)}</Badge>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!data ? (
            <Button onClick={handleGenerate} disabled={generating} className="gap-2">
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Generate Sankey
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleGenerate}
                disabled={generating}
                className="gap-2"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Refresh Sankey
              </Button>
              <Button
                variant="ghost"
                onClick={handleClearSnapshot}
                disabled={generating}
                className="gap-2"
              >
                <Trash2 className="h-4 w-4" />
                Clear snapshot
              </Button>
            </>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div
          ref={containerRef}
          className="relative w-full overflow-x-auto rounded-2xl border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.08),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.08),_transparent_30%),linear-gradient(180deg,_rgba(255,255,255,0.9),_rgba(248,250,252,0.85))] p-4"
        >
          {loading ? (
            <div className="flex h-[520px] items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading Sankey snapshot...
            </div>
          ) : error ? (
            <div className="flex h-[520px] items-center justify-center rounded-xl border border-dashed bg-white/85 text-sm text-muted-foreground">
              {error}
            </div>
          ) : !layout.nodes.length ? (
            <div className="flex h-[520px] flex-col items-center justify-center gap-4 rounded-xl border border-dashed bg-white/85 px-6 text-center text-sm text-muted-foreground">
              <div className="space-y-1">
                <p className="font-medium text-foreground">No Sankey snapshot yet.</p>
                <p>Generate one to capture the current full-dataset branching view.</p>
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
                width={layout.chartWidth}
                height={layout.chartHeight}
                viewBox={`0 0 ${layout.chartWidth} ${layout.chartHeight}`}
                className="overflow-visible"
              >
                <defs>
                  {layout.links.map((link) => {
                    const gradientId = `gradient-${link.key}`;
                    return (
                      <linearGradient
                        key={gradientId}
                        id={gradientId}
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="0%"
                      >
                        <stop
                          offset="0%"
                          stopColor={link.sourceNode.palette.stroke}
                          stopOpacity="0.25"
                        />
                        <stop
                          offset="100%"
                          stopColor={link.targetNode.palette.stroke}
                          stopOpacity="0.55"
                        />
                      </linearGradient>
                    );
                  })}
                </defs>

                {layout.links.map((link) => {
                  const x1 = link.sourceNode.x + link.sourceNode.width;
                  const x2 = link.targetNode.x;
                  const distance = Math.max(88, Math.abs(x2 - x1));
                  const bend = Math.min(180, distance * 0.48);
                  const c1x = x1 + bend;
                  const c2x = x2 - bend;
                  const isActive =
                    selectedLinkKey === link.key ||
                    selectedStageKey === link.sourceNode.stageKey ||
                    selectedStageKey === link.targetNode.stageKey;
                  const isHovered = hoveredLinkKey === link.key;
                  const isGhosted =
                    link.kindKey === "ghosted" || link.targetNode.kindKey === "ghosted";
                  const isRejected =
                    link.kindKey === "rejected" || link.targetNode.kindKey === "rejected";
                  const opacity = isHovered || isActive ? 0.92 : isGhosted ? 0.28 : isRejected ? 0.42 : 0.38;

                  return (
                    <path
                      key={link.key}
                      d={`M ${x1} ${link.sourceY} C ${c1x} ${link.sourceY}, ${c2x} ${link.targetY}, ${x2} ${link.targetY}`}
                      fill="none"
                      stroke={
                        isGhosted || isRejected
                          ? link.targetNode.palette.stroke
                          : `url(#gradient-${link.key})`
                      }
                      strokeWidth={Math.max(3, link.thickness)}
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
                  const isActive = selectedStageKey === node.stageKey;
                  const isHovered = hoveredNodeId === node.id;
                  const isGhosted = node.kindKey === "ghosted";
                  const isRejected = node.kindKey === "rejected";
                  const opacity = isGhosted ? 0.82 : 1;
                  const shadow =
                    isHovered || isActive
                      ? `drop-shadow(0 10px 24px ${node.palette.stroke}2a)`
                      : "drop-shadow(0 4px 10px rgba(15, 23, 42, 0.08))";

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x},${node.y})`}
                      className="cursor-pointer"
                      style={{ opacity, filter: shadow }}
                      onMouseEnter={() => {
                        setHoveredNodeId(node.id);
                        setHoveredLinkKey(null);
                      }}
                      onMouseLeave={() => setHoveredNodeId(null)}
                      onClick={() => handleNodeSelect(node)}
                    >
                      <rect
                        width={node.width}
                        height={node.height}
                        rx={18}
                        fill={node.palette.fill}
                        stroke={node.palette.stroke}
                        strokeWidth={isActive || isHovered ? 2.5 : 1.5}
                        strokeDasharray={isGhosted ? "7 6" : undefined}
                      />
                      <rect
                        x={0}
                        y={0}
                        width={8}
                        height={node.height}
                        rx={18}
                        fill={node.palette.accent}
                        opacity={isGhosted ? 0.45 : 0.9}
                      />
                      <text
                        x={22}
                        y={26}
                        style={{
                          fill: node.palette.text,
                          fontSize: "14px",
                          fontWeight: 700,
                          letterSpacing: "-0.01em",
                        }}
                      >
                        {node.labelLines.map((line, index) => (
                          <tspan
                            key={`${node.id}-label-${index}`}
                            x={22}
                            dy={index === 0 ? 0 : 17}
                          >
                            {line}
                          </tspan>
                        ))}
                      </text>
                      <text
                        x={22}
                        y={node.labelLines.length > 1 ? 54 : 46}
                        style={{
                          fill: node.palette.muted,
                          fontSize: "12px",
                          fontWeight: 500,
                        }}
                      >
                        {node.count} applications
                      </text>
                      {isRejected && (
                        <text
                          x={22}
                          y={node.labelLines.length > 1 ? 72 : 64}
                          style={{
                            fill: node.palette.muted,
                            fontSize: "11px",
                            fontWeight: 600,
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
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
