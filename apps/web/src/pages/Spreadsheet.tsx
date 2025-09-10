import { useState } from "react";
import { useApplications } from "@/hooks/useApplications";
import ApplicationsTable from "@/components/ApplicationsTable";
import Navigation from "@/components/Navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, XCircle, Plus, Download } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { ApplicationStatus, JobApplication } from "@/types/application";

const Spreadsheet = () => {
  const { applications, loading, error, deleteApplication, createApplication } = useApplications();

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<{ company: string; role: string; status: ApplicationStatus; location: string; salary_range: string; job_posting_url: string; notes: string; applied_date: Date | null }>({
    company: "",
    role: "",
    status: "APPLIED",
    location: "",
    salary_range: "",
    job_posting_url: "",
    notes: "",
    applied_date: null,
  });

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-gray-600">Loading applications...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600">
                Error loading applications: {error}
              </p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <Table className="h-8 w-8 text-primary" />
            Applications Spreadsheet
          </h1>
          <p className="text-gray-600">
            Detailed view of all your job applications
          </p>
        </div>

        {/* New Application Dialog */}
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Application</DialogTitle>
            </DialogHeader>
            <form
              className="space-y-4"
              onSubmit={async (e) => {
                e.preventDefault();
                if (!form.company || !form.role) return;
                setSubmitting(true);
                try {
                  const payload = {
                    company: form.company,
                    role: form.role,
                    status: form.status,
                    location: form.location || undefined,
                    salary_range: form.salary_range || undefined,
                    job_posting_url: form.job_posting_url || undefined,
                    notes: form.notes || undefined,
                    applied_date: form.applied_date ? form.applied_date.toISOString() : undefined,
                  } as unknown as Omit<JobApplication, "id" | "created_at" | "last_updated_at" | "user_id">;
                  await createApplication(payload);
                  setOpen(false);
                  setForm({
                    company: "",
                    role: "",
                    status: "APPLIED",
                    location: "",
                    salary_range: "",
                    job_posting_url: "",
                    notes: "",
                    applied_date: null,
                  });
                } finally {
                  setSubmitting(false);
                }
              }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="company">Company</Label>
                  <Input
                    id="company"
                    value={form.company}
                    onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="role">Role</Label>
                  <Input
                    id="role"
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="status">Status</Label>
                  <select
                    id="status"
                    className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={form.status}
                    onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as ApplicationStatus }))}
                  >
                    <option value="APPLIED">Applied</option>
                    <option value="ASSESSMENT">Assessment</option>
                    <option value="INTERVIEW">Interview</option>
                    <option value="OFFERED">Offered</option>
                    <option value="ACCEPTED">Accepted</option>
                    <option value="REJECTED">Rejected</option>
                    <option value="WITHDRAWN">Withdrawn</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="applied_date">Applied Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                      >
                        {form.applied_date ? form.applied_date.toLocaleDateString() : "Pick a date"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent align="start" className="p-0">
                      <Calendar
                        mode="single"
                        selected={form.applied_date ?? undefined}
                        onSelect={(date) => setForm((f) => ({ ...f, applied_date: date ?? null }))}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <Label htmlFor="location">Location</Label>
                  <Input
                    id="location"
                    value={form.location}
                    onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="salary_range">Salary Range</Label>
                  <Input
                    id="salary_range"
                    value={form.salary_range}
                    onChange={(e) => setForm((f) => ({ ...f, salary_range: e.target.value }))}
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="job_posting_url">Job Posting URL</Label>
                  <Input
                    id="job_posting_url"
                    value={form.job_posting_url}
                    onChange={(e) => setForm((f) => ({ ...f, job_posting_url: e.target.value }))}
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea
                    id="notes"
                    value={form.notes}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  />
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Creating..." : "Create"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>All Applications ({applications.length})</CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" className="flex items-center gap-2" onClick={() => setOpen(true)}>
                <Plus className="h-4 w-4" />
                New Application
              </Button>
              <Button
                variant="outline"
                className="flex items-center gap-2"
                onClick={() => {
                  const headers = [
                    "Company",
                    "Role",
                    "Status",
                    "Date Created",
                    "Last Update",
                    "Location",
                    "Salary Range",
                  ];
                  const csvContent = [
                    headers.join(","),
                    ...applications.map((app) =>
                      [
                        app.company,
                        app.role,
                        app.status,
                        app.created_at,
                        app.last_updated_at,
                        app.location || "",
                        app.salary_range || "",
                      ]
                        .map((field) => `"${field}"`)
                        .join(",")
                    ),
                  ].join("\n");
                  const blob = new Blob([csvContent], { type: "text/csv" });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "job-applications.csv";
                  a.click();
                  window.URL.revokeObjectURL(url);
                }}
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <ApplicationsTable applications={applications} onDelete={deleteApplication} hideExport />
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Spreadsheet;
