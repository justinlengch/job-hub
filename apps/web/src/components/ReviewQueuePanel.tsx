import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiService } from "@/services/api";
import { ReviewQueueResponse } from "@/types/application";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, RefreshCw, ShieldAlert, Check, X } from "lucide-react";

interface ReviewQueuePanelProps {
  compact?: boolean;
}

const ReviewQueuePanel = ({ compact = false }: ReviewQueuePanelProps) => {
  const [data, setData] = useState<ReviewQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getReviewQueue();
      setData(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load review queue";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiService.getReviewQueue();
        if (!cancelled) {
          setData(response);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : "Failed to load review queue";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const resolveItem = async (sourceId: string, action: "confirm" | "separate") => {
    setSavingId(sourceId);
    try {
      if (action === "confirm") {
        await apiService.confirmReviewQueueItem(sourceId);
        toast.success("Merge confirmed");
      } else {
        await apiService.separateReviewQueueItem(sourceId);
        toast.success("Kept separate");
      }

      setData((current) =>
        current
          ? {
              ...current,
              items: current.items.filter((item) => item.source_id !== sourceId),
              pending_count: Math.max(0, current.pending_count - 1),
            }
          : current
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update review item";
      toast.error(message);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <Card className="border-slate-200 bg-gradient-to-br from-slate-50 to-white">
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="rounded-full bg-amber-100 p-2 text-amber-700">
                <ShieldAlert className="h-4 w-4" />
              </div>
              <CardTitle className="text-lg">Review Queue</CardTitle>
              {data && <Badge variant="secondary">{data.pending_count}</Badge>}
            </div>
            <CardDescription>
              Low-confidence merges stay here until you confirm or separate them.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={loadQueue} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && !data ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading queue...
          </div>
        ) : data?.items.length ? (
          <div className={`space-y-3 ${compact ? "max-h-[420px] overflow-y-auto pr-1" : ""}`}>
            {data.items.map((item) => (
              <div key={item.source_id} className="rounded-lg border bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold">{item.company}</p>
                      <Badge variant="outline">{item.source_type}</Badge>
                      <Badge variant="secondary">{Math.round(item.confidence_score * 100)}%</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{item.role}</p>
                    {item.candidate_company && (
                      <p className="text-xs text-muted-foreground">
                        Candidate: {item.candidate_company}
                        {item.candidate_role ? ` • ${item.candidate_role}` : ""}
                      </p>
                    )}
                    <p className="text-sm text-foreground/90">{item.review_reason}</p>
                    {item.sender_domain && (
                      <p className="text-xs text-muted-foreground">Sender domain: {item.sender_domain}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      size="sm"
                      onClick={() => resolveItem(item.source_id, "confirm")}
                      disabled={savingId === item.source_id}
                      className="gap-2"
                    >
                      <Check className="h-4 w-4" />
                      Confirm
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => resolveItem(item.source_id, "separate")}
                      disabled={savingId === item.source_id}
                      className="gap-2"
                    >
                      <X className="h-4 w-4" />
                      Separate
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed bg-white p-6 text-sm text-muted-foreground">
            No items need review right now.
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ReviewQueuePanel;
