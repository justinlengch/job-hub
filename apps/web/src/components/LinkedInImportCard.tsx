import { useState } from "react";
import { toast } from "sonner";
import { apiService } from "@/services/api";
import { LinkedInImportResult } from "@/types/application";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { AlertCircle, CheckCircle2, FileText, Loader2, UploadCloud } from "lucide-react";

interface LinkedInImportCardProps {
  onImported?: (result: LinkedInImportResult) => void | Promise<void>;
}

const LinkedInImportCard = ({ onImported }: LinkedInImportCardProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<LinkedInImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [minAppliedDate, setMinAppliedDate] = useState("");
  const [maxAppliedDate, setMaxAppliedDate] = useState("");

  const handleImport = async () => {
    if (!selectedFile) return;
    if (minAppliedDate && maxAppliedDate && minAppliedDate > maxAppliedDate) {
      const message = "Start date must be on or before end date";
      setError(message);
      toast.error(message);
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await apiService.importLinkedInHistory(selectedFile, {
        min_applied_date: minAppliedDate || undefined,
        max_applied_date: maxAppliedDate || undefined,
      });
      setResult(response);
      toast.success("LinkedIn history imported");
      await Promise.resolve(onImported?.(response));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Import failed";
      setError(message);
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card className="border-dashed border-2 bg-gradient-to-br from-slate-50 to-white">
      <CardHeader className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="rounded-full bg-sky-100 p-2 text-sky-700">
            <UploadCloud className="h-4 w-4" />
          </div>
          <CardTitle className="text-lg">Import LinkedIn Easy Apply</CardTitle>
        </div>
        <CardDescription>
          Upload a CSV or JSON export. The backend will normalize the rows and merge them with your existing applications.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Input
            type="file"
            accept=".csv,.json,application/json,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setSelectedFile(file);
              setResult(null);
              setError(null);
            }}
            className="max-w-sm"
          />
          <Button
            type="button"
            onClick={handleImport}
            disabled={!selectedFile || isUploading}
            className="gap-2"
          >
            {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
            {isUploading ? "Importing..." : "Import file"}
          </Button>
          {selectedFile && (
            <Badge variant="secondary" className="gap-2">
              <CheckCircle2 className="h-3 w-3" />
              {selectedFile.name}
            </Badge>
          )}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">From applied date</label>
            <Input
              type="date"
              value={minAppliedDate}
              onChange={(event) => setMinAppliedDate(event.target.value)}
              max={maxAppliedDate || undefined}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">To applied date</label>
            <Input
              type="date"
              value={maxAppliedDate}
              onChange={(event) => setMaxAppliedDate(event.target.value)}
              min={minAppliedDate || undefined}
            />
          </div>
        </div>

        <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
          Required fields: company, role, and applied date. LinkedIn exports like
          <span className="font-medium text-foreground"> Company Name</span>,
          <span className="font-medium text-foreground"> Job Title</span>,
          <span className="font-medium text-foreground"> Application Date</span>, and
          <span className="font-medium text-foreground"> Job Url</span> are supported directly.
          Contact details, resume names, and question-answer export fields are ignored for job parsing.
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="grid gap-3 md:grid-cols-6">
            <SummaryTile label="Processed" value={result.summary.processed_rows} />
            <SummaryTile label="Skipped" value={result.summary.skipped_rows ?? 0} />
            <SummaryTile label="Created" value={result.summary.created_applications} />
            <SummaryTile label="Merged" value={result.summary.merged_applications} />
            <SummaryTile label="Review" value={result.summary.review_items} />
            <SummaryTile label="Failed" value={result.summary.failed_rows} tone={result.summary.failed_rows > 0 ? "warn" : "default"} />
          </div>
        )}
      </CardContent>
    </Card>
  );
};

interface SummaryTileProps {
  label: string;
  value: number;
  tone?: "default" | "warn";
}

const SummaryTile = ({ label, value, tone = "default" }: SummaryTileProps) => (
  <div
    className={`rounded-lg border p-3 ${
      tone === "warn" ? "border-amber-200 bg-amber-50" : "bg-white"
    }`}
  >
    <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
    <p className="mt-1 text-2xl font-semibold">{value}</p>
  </div>
);

export default LinkedInImportCard;
