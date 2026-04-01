import { useState, useEffect, type FormEvent } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApplicationEventType, JobApplication, ApplicationEvent } from "@/types/application";
import { emailRefsService, buildGmailUrlWithPrefs, applicationEventsService, jobApplicationsService } from "@/services/supabase";
import { apiService } from "@/services/api";
import { toast } from "sonner";
import {
  Search,
  Download,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Building2,
  MapPin,
  DollarSign,
  Calendar,
  ExternalLink,
  Trash,
  Plus,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import TimelineEventComponent from "@/components/TimelineEvent";
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction } from "@/components/ui/alert-dialog";

interface ApplicationsTableProps {
  applications: JobApplication[];
  onDelete?: (id: string) => void;
  hideExport?: boolean;
}

const statusColors = {
  APPLIED: "bg-blue-100 text-blue-800",
  ASSESSMENT: "bg-purple-100 text-purple-800",
  INTERVIEW: "bg-yellow-100 text-yellow-800",
  OFFERED: "bg-green-100 text-green-800",
  ACCEPTED: "bg-green-200 text-green-900",
  REJECTED: "bg-red-100 text-red-800",
  WITHDRAWN: "bg-gray-100 text-gray-800",
};

const manualEventTypeOptions: Array<{ value: ApplicationEventType; label: string }> = [
  { value: "APPLICATION_SUBMITTED", label: "Applied" },
  { value: "APPLICATION_RECEIVED", label: "Application Received" },
  { value: "APPLICATION_VIEWED", label: "Application Viewed" },
  { value: "APPLICATION_REVIEWED", label: "Application Reviewed" },
  { value: "ASSESSMENT_RECEIVED", label: "Assessment Received" },
  { value: "ASSESSMENT_COMPLETED", label: "Assessment Completed" },
  { value: "INTERVIEW_SCHEDULED", label: "Interview Scheduled" },
  { value: "INTERVIEW_COMPLETED", label: "Interview Completed" },
  { value: "FINAL_ROUND", label: "Final Round" },
  { value: "REFERENCE_REQUESTED", label: "Reference Requested" },
  { value: "OFFER_RECEIVED", label: "Offer Received" },
  { value: "OFFER_ACCEPTED", label: "Offer Accepted" },
  { value: "OFFER_DECLINED", label: "Offer Declined" },
  { value: "APPLICATION_REJECTED", label: "Rejected" },
  { value: "APPLICATION_WITHDRAWN", label: "Withdrawn" },
];

const ApplicationsTable = ({ applications, onDelete, hideExport }: ApplicationsTableProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] =
    useState<keyof JobApplication>("last_updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [gmailLinks, setGmailLinks] = useState<Record<string, string>>({});
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState<JobApplication | null>(null);
  const [appEvents, setAppEvents] = useState<ApplicationEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [updatingFinalRound, setUpdatingFinalRound] = useState(false);
  const [addingEvent, setAddingEvent] = useState(false);
  const [manualEventForm, setManualEventForm] = useState<{
    event_type: ApplicationEventType;
    event_date: string;
    description: string;
  }>({
    event_type: "APPLICATION_RECEIVED",
    event_date: "",
    description: "",
  });
  const itemsPerPage = 10;

  const [localApps, setLocalApps] = useState<JobApplication[]>(applications);
  useEffect(() => {
    setLocalApps(applications);
  }, [applications]);

  const [deleteDialogId, setDeleteDialogId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Filter applications based on search term
  const filteredApplications = localApps.filter(
    (app) =>
      app.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      app.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
      app.status.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort applications
  const sortedApplications = [...filteredApplications].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];

    const isDateField =
      typeof aValue === "string" &&
      typeof bValue === "string" &&
      sortField.endsWith("_at");

    if (isDateField) {
      const aTime = new Date(aValue as string).getTime();
      const bTime = new Date(bValue as string).getTime();
      if (aTime < bTime) return sortDirection === "asc" ? -1 : 1;
      if (aTime > bTime) return sortDirection === "asc" ? 1 : -1;
      return 0;
    }

    if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
    if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
    return 0;
  });

  // Paginate applications
  const totalPages = Math.ceil(sortedApplications.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedApplications = sortedApplications.slice(
    startIndex,
    startIndex + itemsPerPage
  );

  // Fetch latest Gmail links for the currently visible applications
  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const entries = await Promise.all(
          paginatedApplications.map(async (application) => {
            try {
              const appId = application.id;
              const ref = await emailRefsService.getLatestRefByApplicationId(appId);
              let url = "";
              if (ref) {
                url = await buildGmailUrlWithPrefs(ref.external_email_id, ref.thread_id);
              }
              return [application.id, url] as const;
            } catch {
              return [application.id, ""] as const;
            }
          })
        );

        if (!cancelled) {
          setGmailLinks((prev) => {
            const next = { ...prev };
            for (const [id, url] of entries) {
              if (url) next[id] = url;
            }
            return next;
          });
        }
      } catch {
        // no-op
      }
    };

    if (paginatedApplications.length) {
      run();
    }

    return () => {
      cancelled = true;
    };
  }, [paginatedApplications]);

  const handleSort = (field: keyof JobApplication) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const handleOpenDetails = async (application: JobApplication) => {
    setSelectedApp(application);
    setDetailsOpen(true);
    setEventsLoading(true);
    setManualEventForm({
      event_type: "APPLICATION_RECEIVED",
      event_date: new Date().toISOString().slice(0, 16),
      description: "",
    });
    try {
      const appId = application.id;
      const list = await applicationEventsService.getEventsWithEmailRefsByApplicationId(
        appId
      );
      setAppEvents(list);
    } catch {
      setAppEvents([]);
    } finally {
      setEventsLoading(false);
    }
  };

  const isFinalRound = appEvents.some((event) => event.event_type === "FINAL_ROUND");

  const handleFinalRoundToggle = async (enabled: boolean) => {
    if (!selectedApp) return;

    setUpdatingFinalRound(true);
    try {
      await apiService.toggleFinalRound(selectedApp.id, enabled);
      toast.success(enabled ? "Marked as final round" : "Final round cleared");
      await handleOpenDetails(selectedApp);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update final-round state";
      toast.error(message);
    } finally {
      setUpdatingFinalRound(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await jobApplicationsService.deleteApplication(id);
      setLocalApps((prev) =>
        prev.filter((app) => app.id !== id)
      );
      if (selectedApp) {
        if (selectedApp.id === id) {
          setDetailsOpen(false);
          setSelectedApp(null);
        }
      }
      if (onDelete) {
        onDelete(id);
      }
    } catch (err) {
      // no-op: surface via UI as needed
    } finally {
      setDeletingId(null);
      setDeleteDialogId(null);
    }
  };

  const handleCreateManualEvent = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedApp || !manualEventForm.event_date) return;

    setAddingEvent(true);
    try {
      await apiService.createManualApplicationEvent(selectedApp.id, {
        event_type: manualEventForm.event_type,
        event_date: new Date(manualEventForm.event_date).toISOString(),
        description: manualEventForm.description || undefined,
      });
      toast.success("Event added");
      const refreshedApp = await jobApplicationsService.getApplicationById(selectedApp.id);
      if (refreshedApp) {
        setSelectedApp(refreshedApp);
        setLocalApps((prev) => prev.map((app) => (app.id === refreshedApp.id ? refreshedApp : app)));
      }
      await handleOpenDetails(refreshedApp || selectedApp);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to add event";
      toast.error(message);
    } finally {
      setAddingEvent(false);
    }
  };

  const exportToCSV = () => {
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
      ...sortedApplications.map((app) =>
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
  };

  return (
    <div className="space-y-4">
      {/* Search and Export Controls */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            placeholder="Search applications..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        {!hideExport && (
          <Button variant="outline" onClick={exportToCSV} className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
        )}
      </div>

      {/* Applications Grid */}
      <div className="grid gap-4">
        {paginatedApplications.map((application) => (
          <Card
            key={application.id}
            onClick={() => handleOpenDetails(application)}
            className="relative p-6 pr-12 hover:shadow-md transition-shadow duration-200 cursor-pointer"
            role="button"
            tabIndex={0}
          >
            <AlertDialog
              open={deleteDialogId === application.id}
              onOpenChange={(open) =>
                setDeleteDialogId(open ? application.id : null)
              }
            >
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-3 right-3"
                onClick={(e) => {
                  e.stopPropagation();
                  setDeleteDialogId(application.id);
                }}
                disabled={deletingId === application.id}
                aria-label="Delete application"
                title="Delete application"
              >
                <Trash className="h-4 w-4 text-muted-foreground" />
              </Button>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete application?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will permanently delete this job application and its events. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel onClick={(e) => e.stopPropagation()}>
                    Cancel
                  </AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.stopPropagation();
                      const id = application.id;
                      handleDelete(id);
                    }}
                    disabled={deletingId === application.id}
                  >
                    Confirm Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Company and Position */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  <span className="font-semibold">{application.company}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {application.role}
                </p>
                <Badge
                  className={`text-xs w-fit ${
                    statusColors[application.status]
                  }`}
                >
                  {application.status
                    .replace("_", " ")
                    .replace(/\b\w/g, (l) => l.toUpperCase())}
                </Badge>
              </div>

              {/* Details */}
              <div className="space-y-2">
                {application.location && (
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="h-3 w-3 text-muted-foreground" />
                    <span>{application.location}</span>
                  </div>
                )}
                {application.salary_range && (
                  <div className="flex items-center gap-2 text-sm">
                    <DollarSign className="h-3 w-3 text-muted-foreground" />
                    <span>{application.salary_range}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="h-3 w-3 text-muted-foreground" />
                  <div className="flex flex-col">
                    <span>
                      Applied:{" "}
                      {new Date(application.applied_date || application.created_at).toLocaleDateString()}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Updated:{" "}
                      {new Date(application.last_updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                {gmailLinks[application.id] && (
                  <a
                    href={gmailLinks[application.id]}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    View email
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>

              {/* Notes */}
              <div className="space-y-2">
                {application.notes && (
                  <>
                    <Label className="text-xs text-muted-foreground">Notes</Label>
                    <p
                      className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-wrap"
                      title={application.notes}
                    >
                      {application.notes}
                    </p>
                  </>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-hidden p-0">
          <DialogHeader>
            <div className="border-b px-6 py-5">
              <DialogTitle>
                {selectedApp ? `${selectedApp.company} — ${selectedApp.role}` : "Application Details"}
              </DialogTitle>
              {selectedApp && (
                <div className="flex flex-wrap items-center gap-2 pt-2">
                  <Badge variant="secondary">{selectedApp.status}</Badge>
                  {selectedApp.application_inferred && <Badge variant="outline">Inferred</Badge>}
                  {selectedApp.needs_review && <Badge variant="destructive">Needs review</Badge>}
                  <div className="ml-auto flex items-center gap-3">
                    <span className="text-sm text-muted-foreground">Final round</span>
                    <Switch
                      checked={isFinalRound}
                      onCheckedChange={handleFinalRoundToggle}
                      disabled={eventsLoading || updatingFinalRound}
                    />
                  </div>
                </div>
              )}
            </div>
          </DialogHeader>
          <div className="max-h-[calc(85vh-120px)] overflow-y-auto px-6 py-4">
            {selectedApp && (
              <form
                className="mb-4 rounded-xl border bg-slate-50 p-4"
                onSubmit={handleCreateManualEvent}
              >
                <div className="mb-3 flex items-center gap-2">
                  <Plus className="h-4 w-4 text-primary" />
                  <p className="text-sm font-semibold">Add Manual Event</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <Label htmlFor="manual-event-type">Event Type</Label>
                    <select
                      id="manual-event-type"
                      className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={manualEventForm.event_type}
                      onChange={(event) =>
                        setManualEventForm((current) => ({
                          ...current,
                          event_type: event.target.value as ApplicationEventType,
                        }))
                      }
                    >
                      {manualEventTypeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="manual-event-date">Event Date</Label>
                    <Input
                      id="manual-event-date"
                      type="datetime-local"
                      className="mt-1"
                      value={manualEventForm.event_date}
                      onChange={(event) =>
                        setManualEventForm((current) => ({
                          ...current,
                          event_date: event.target.value,
                        }))
                      }
                      required
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Label htmlFor="manual-event-description">Description</Label>
                    <Textarea
                      id="manual-event-description"
                      className="mt-1 min-h-[88px]"
                      placeholder="Optional note about the event"
                      value={manualEventForm.description}
                      onChange={(event) =>
                        setManualEventForm((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="mt-3 flex justify-end">
                  <Button type="submit" size="sm" disabled={addingEvent}>
                    {addingEvent ? "Adding..." : "Add Event"}
                  </Button>
                </div>
              </form>
            )}
            {eventsLoading ? (
              <p className="text-sm text-muted-foreground">Loading events...</p>
            ) : appEvents.length ? (
              <div className="space-y-3">
                {[...appEvents]
                  .sort(
                    (a, b) =>
                      new Date(b.email_received_at || b.event_date).getTime() -
                      new Date(a.email_received_at || a.event_date).getTime()
                  )
                  .map((event) => (
                    <TimelineEventComponent key={event.id} event={event} />
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No events yet</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {startIndex + 1}-
            {Math.min(startIndex + itemsPerPage, sortedApplications.length)} of{" "}
            {sortedApplications.length} applications
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setCurrentPage((prev) => Math.min(totalPages, prev + 1))
              }
              disabled={currentPage === totalPages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicationsTable;
