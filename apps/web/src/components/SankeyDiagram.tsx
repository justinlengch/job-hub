import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { apiService } from "@/services/api";
import {
  SankeyLink,
  SankeyNode,
  SankeyResponse,
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
  Loader2,
  RotateCcw,
  SlidersHorizontal,
} from "lucide-react";

const STAGE_ORDER = [
  "APPLIED",
  "ASSESSMENT",
  "INTERVIEW",
  "FINAL_ROUND",
  "OFFERED",
  "ACCEPTED",
  "REJECTED",
  "WITHDRAWN",
];

type SankeyFilters = {
  start_date: string;
  end_date: string;
  source_type: string;
  company: string;
};

type LayoutNode = SankeyNode & {
  stageKey: string;
  x: number;
  y: number;
  width: number;
  height: number;
  incoming: number;
  outgoing: number;
};

type LayoutLink = SankeyLink & {
  key: string;
  sourceNode: LayoutNode;
  targetNode: LayoutNode;
  thickness: number;
  sourceY: number;
  targetY: number;
};

interface SankeyDiagramProps {
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

const SankeyDiagram = ({ onStageSelect }: SankeyDiagramProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [data, setData] = useState<SankeyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredLinkKey, setHoveredLinkKey] = useState<string | null>(null);
  const [selectedStageKey, setSelectedStageKey] = useState<string | null>(null);
  const [selectedLinkKey, setSelectedLinkKey] = useState<string | null>(null);
  const [filters, setFilters] = useState<SankeyFilters>({
    start_date: "",
    end_date: "",
    source_type: "all",
    company: "",
  });

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
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiService.getSankeyData({
          start_date: filters.start_date || undefined,
          end_date: filters.end_date || undefined,
          source_type:
            filters.source_type && filters.source_type !== "all"
              ? filters.source_type
              : undefined,
          company: filters.company || undefined,
        });

        if (!cancelled) {
          setData(response);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : "Failed to load Sankey data";
          setError(message);
          toast.error(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [filters]);

  const layout = useMemo(() => {
    const chartHeight = 420;
    const baseWidth = Math.max(containerWidth || 960, 760);
    const nodeWidth = 164;
    const leftPad = 28;
    const rightPad = 28;
    const topPad = 24;
    const bottomPad = 24;

    if (!data || !data.nodes.length) {
      return {
        chartHeight,
        chartWidth: baseWidth,
        nodes: [] as LayoutNode[],
        links: [] as LayoutLink[],
      };
    }

    const stageKeys = Array.from(
      new Set([
        ...STAGE_ORDER,
        ...data.nodes.map((node) =>
          normalizeStageKey(node.stage || node.id || node.label)
        ),
      ])
    ).filter((stageKey) =>
      data.nodes.some(
        (node) =>
          normalizeStageKey(node.stage || node.id || node.label) === stageKey
      )
    );

    const nodesInOrder: LayoutNode[] = stageKeys.map((stageKey, index) => {
      const node =
        data.nodes.find(
          (candidate) =>
            normalizeStageKey(candidate.stage || candidate.id || candidate.label) ===
            stageKey
        ) || data.nodes[index];

      return {
        ...node,
        stageKey,
        x: leftPad + index * (nodeWidth + 48),
        y: topPad,
        width: nodeWidth,
        height: 72,
        incoming: 0,
        outgoing: 0,
      };
    });

    const maxValue = Math.max(
      1,
      ...data.links.map((link) => link.value),
      ...data.nodes.map((node) => node.count)
    );
    const flowUnit = clamp((chartHeight - topPad - bottomPad - 80) / maxValue, 4, 18);
    const stageCount = nodesInOrder.length;
    const requiredWidth =
      leftPad + rightPad + stageCount * nodeWidth + Math.max(0, stageCount - 1) * 48;
    const chartWidth = Math.max(baseWidth, requiredWidth);
    const gap =
      stageCount > 1
        ? Math.max(
            48,
            (chartWidth - leftPad - rightPad - stageCount * nodeWidth) /
              (stageCount - 1)
          )
        : 0;

    nodesInOrder.forEach((node, index) => {
      node.x = leftPad + index * (nodeWidth + gap);
    });

    const nodeMap = new Map<string, LayoutNode>();
    nodesInOrder.forEach((node) => {
      nodeMap.set(node.id, node);
      nodeMap.set(node.stageKey, node);
    });

    const linkItems: LayoutLink[] = data.links
      .map((link) => {
        const sourceNode =
          nodeMap.get(link.source) ||
          nodeMap.get(normalizeStageKey(link.source)) ||
          nodesInOrder[0];
        const targetNode =
          nodeMap.get(link.target) ||
          nodeMap.get(normalizeStageKey(link.target)) ||
          nodesInOrder[nodesInOrder.length - 1];

        if (!sourceNode || !targetNode) return null;

        const thickness = Math.max(4, link.value * flowUnit);
        return {
          ...link,
          key: `${link.source}__${link.target}`,
          sourceNode,
          targetNode,
          thickness,
          sourceY: 0,
          targetY: 0,
        };
      })
      .filter(Boolean) as LayoutLink[];

    const sourceOrder = new Map(
      nodesInOrder.map((node, index) => [node.id, index] as const)
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

    const sortLinks = (a: LayoutLink, b: LayoutLink) => {
      const stageA = sourceOrder.get(a.targetNode.id) ?? 0;
      const stageB = sourceOrder.get(b.targetNode.id) ?? 0;
      return stageA - stageB || b.value - a.value;
    };

    for (const node of nodesInOrder) {
      const outgoing = (outgoingByNode.get(node.id) || []).sort(sortLinks);
      const incoming = (incomingByNode.get(node.id) || []).sort(sortLinks);
      const outgoingHeight = outgoing.reduce((sum, link) => sum + link.thickness, 0);
      const incomingHeight = incoming.reduce((sum, link) => sum + link.thickness, 0);
      node.outgoing = outgoingHeight;
      node.incoming = incomingHeight;
      node.height = Math.max(72, Math.max(outgoingHeight, incomingHeight) + 24);
      node.y = topPad + Math.max(0, (chartHeight - topPad - bottomPad - node.height) / 2);
    }

    for (const node of nodesInOrder) {
      const outgoing = (outgoingByNode.get(node.id) || []).sort(sortLinks);
      let offset = 0;
      for (const link of outgoing) {
        link.sourceY = node.y + offset + link.thickness / 2;
        offset += link.thickness;
      }
    }

    for (const node of nodesInOrder) {
      const incoming = (incomingByNode.get(node.id) || []).sort(sortLinks);
      let offset = 0;
      for (const link of incoming) {
        link.targetY = node.y + offset + link.thickness / 2;
        offset += link.thickness;
      }
    }

    return {
      chartHeight,
      chartWidth,
      nodes: nodesInOrder,
      links: linkItems,
    };
  }, [containerWidth, data]);

  const totalApplications = data?.meta?.total_applications ?? 0;
  const inferredCount = data?.meta?.inferred_count ?? 0;
  const pendingReviewCount = data?.meta?.pending_review_count ?? 0;

  const selectedLink = layout.links.find((link) => link.key === selectedLinkKey) || null;
  const hoveredLink = layout.links.find((link) => link.key === hoveredLinkKey) || null;
  const hoveredNode = layout.nodes.find((node) => node.id === hoveredNodeId) || null;

  const resetFilters = () => {
    setFilters({
      start_date: "",
      end_date: "",
      source_type: "all",
      company: "",
    });
  };

  const linkLabel = (link: LayoutLink) => {
    const source = link.sourceNode.label || formatStageLabel(link.sourceNode.stageKey);
    const target = link.targetNode.label || formatStageLabel(link.targetNode.stageKey);
    return `${source} -> ${target}`;
  };

  return (
    <Card className="border-slate-200 bg-gradient-to-br from-white to-slate-50 shadow-sm">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="rounded-full bg-indigo-100 p-2 text-indigo-700">
                <SlidersHorizontal className="h-4 w-4" />
              </div>
              <CardTitle className="text-lg">Application Flow</CardTitle>
              {pendingReviewCount > 0 && <Badge variant="secondary">{pendingReviewCount} review</Badge>}
            </div>
            <CardDescription>
              Hover for counts, click a stage to filter the dashboard, and use the controls to slice by source or date.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">{totalApplications} applications</Badge>
            <Badge variant="outline">{inferredCount} inferred</Badge>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_1fr_160px_160px_auto]">
          <Input
            type="date"
            value={filters.start_date}
            onChange={(event) =>
              setFilters((current) => ({ ...current, start_date: event.target.value }))
            }
          />
          <Input
            type="date"
            value={filters.end_date}
            onChange={(event) =>
              setFilters((current) => ({ ...current, end_date: event.target.value }))
            }
          />
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={filters.source_type}
            onChange={(event) =>
              setFilters((current) => ({ ...current, source_type: event.target.value }))
            }
          >
            <option value="all">All sources</option>
            <option value="EMAIL">Email</option>
            <option value="LINKEDIN_EASY_APPLY">LinkedIn</option>
          </select>
          <Input
            placeholder="Company"
            value={filters.company}
            onChange={(event) =>
              setFilters((current) => ({ ...current, company: event.target.value }))
            }
          />
          <Button variant="outline" onClick={resetFilters} className="gap-2">
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <div ref={containerRef} className="relative w-full overflow-x-auto">
          {loading ? (
            <div className="flex h-[420px] items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading Sankey...
            </div>
          ) : error ? (
            <div className="flex h-[420px] items-center justify-center rounded-lg border border-dashed bg-white text-sm text-muted-foreground">
              {error}
            </div>
          ) : !layout.nodes.length ? (
            <div className="flex h-[420px] items-center justify-center rounded-lg border border-dashed bg-white text-sm text-muted-foreground">
              No Sankey data yet.
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
                        <stop offset="0%" stopColor="#64748b" stopOpacity={0.15} />
                        <stop offset="100%" stopColor="#2563eb" stopOpacity={0.35} />
                      </linearGradient>
                    );
                  })}
                </defs>

                {layout.links.map((link) => {
                  const x1 = link.sourceNode.x + link.sourceNode.width;
                  const x2 = link.targetNode.x;
                  const dx = Math.max(72, x2 - x1);
                  const c1x = x1 + dx * 0.35;
                  const c2x = x2 - dx * 0.35;
                  const isActive =
                    selectedLinkKey === link.key || selectedStageKey === link.targetNode.stageKey;
                  const isHovered = hoveredLinkKey === link.key;

                  return (
                    <path
                      key={link.key}
                      d={`M ${x1} ${link.sourceY} C ${c1x} ${link.sourceY}, ${c2x} ${link.targetY}, ${x2} ${link.targetY}`}
                      fill="none"
                      stroke={`url(#gradient-${link.key})`}
                      strokeWidth={link.thickness}
                      strokeLinecap="round"
                      opacity={isHovered || isActive ? 0.95 : 0.45}
                      className="cursor-pointer transition-opacity"
                      onMouseEnter={() => {
                        setHoveredLinkKey(link.key);
                        setHoveredNodeId(null);
                      }}
                      onMouseLeave={() => setHoveredLinkKey(null)}
                      onClick={() => {
                        setSelectedLinkKey(link.key);
                        if (layout.nodes.find((node) => node.stageKey === link.targetNode.stageKey)) {
                          setSelectedStageKey(link.targetNode.stageKey);
                          onStageSelect?.(link.targetNode.stageKey);
                        }
                      }}
                    />
                  );
                })}

                {layout.nodes.map((node) => {
                  const isActive = selectedStageKey === node.stageKey;
                  const isHovered = hoveredNodeId === node.id;
                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x},${node.y})`}
                      className="cursor-pointer"
                      onMouseEnter={() => {
                        setHoveredNodeId(node.id);
                        setHoveredLinkKey(null);
                      }}
                      onMouseLeave={() => setHoveredNodeId(null)}
                      onClick={() => {
                        setSelectedStageKey(node.stageKey);
                        onStageSelect?.(node.stageKey);
                      }}
                    >
                      <rect
                        width={node.width}
                        height={node.height}
                        rx={16}
                        className={isActive || isHovered ? "fill-indigo-50 stroke-indigo-500" : "fill-white stroke-slate-200"}
                        strokeWidth={1.5}
                      />
                      <text
                        x={18}
                        y={28}
                        className="fill-slate-900"
                        style={{ fontSize: "14px", fontWeight: 600 }}
                      >
                        {node.label || formatStageLabel(node.stageKey)}
                      </text>
                      <text
                        x={18}
                        y={48}
                        className="fill-slate-500"
                        style={{ fontSize: "12px" }}
                      >
                        {node.count} applications
                      </text>
                    </g>
                  );
                })}
              </svg>

              {(hoveredLink || hoveredNode || selectedLink) && (
                <div className="pointer-events-none absolute right-4 top-4 max-w-xs rounded-xl border bg-white/95 p-4 shadow-lg backdrop-blur">
                  {hoveredLink ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">{linkLabel(hoveredLink)}</p>
                      <p className="text-muted-foreground">{hoveredLink.value} applications</p>
                      {hoveredLink.application_ids?.length ? (
                        <p className="text-xs text-muted-foreground">
                          {hoveredLink.application_ids.length} underlying application IDs
                        </p>
                      ) : null}
                    </div>
                  ) : hoveredNode ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">
                        {hoveredNode.label || formatStageLabel(hoveredNode.stageKey)}
                      </p>
                      <p className="text-muted-foreground">{hoveredNode.count} applications reached this stage</p>
                    </div>
                  ) : selectedLink ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">{linkLabel(selectedLink)}</p>
                      <p className="text-muted-foreground">{selectedLink.value} applications selected</p>
                    </div>
                  ) : null}
                </div>
              )}
            </>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Tip:</span>
          <span>Click a stage to filter the dashboard, or use hover to inspect flow counts.</span>
          <ArrowRight className="h-3 w-3" />
        </div>
      </CardContent>
    </Card>
  );
};

export default SankeyDiagram;
