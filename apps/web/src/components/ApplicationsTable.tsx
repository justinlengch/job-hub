import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { JobApplication } from "@/types/application";
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
} from "lucide-react";

interface ApplicationsTableProps {
  applications: JobApplication[];
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

const ApplicationsTable = ({ applications }: ApplicationsTableProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] =
    useState<keyof JobApplication>("created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Filter applications based on search term
  const filteredApplications = applications.filter(
    (app) =>
      app.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      app.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
      app.status.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort applications
  const sortedApplications = [...filteredApplications].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];

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

  const handleSort = (field: keyof JobApplication) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
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
        <Button onClick={exportToCSV} className="flex items-center gap-2">
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Applications Grid */}
      <div className="grid gap-4">
        {paginatedApplications.map((application) => (
          <Card
            key={application.id}
            className="p-6 hover:shadow-md transition-shadow duration-200"
          >
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
                  <span>
                    Applied:{" "}
                    {new Date(application.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                {application.notes && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {application.notes}
                  </p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

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
