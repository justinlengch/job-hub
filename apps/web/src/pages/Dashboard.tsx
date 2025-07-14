import { useState } from "react";
import { useApplications } from "@/hooks/useApplications";
import { useApplicationEvents } from "@/hooks/useApplicationEvents";
import { JobApplication, StatusCounts } from "@/types/application";
import StatusCard from "@/components/StatusCard";
import TimelineEventComponent from "@/components/TimelineEvent";
import FilterControls from "@/components/FilterControls";
import StatsChart from "@/components/StatsChart";
import Navigation from "@/components/Navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  TrendingUp,
  ClipboardCheck,
} from "lucide-react";

const Dashboard = () => {
  const [selectedStatus, setSelectedStatus] = useState<
    JobApplication["status"] | "all"
  >("all");

  // Fetch real data from Supabase
  const {
    applications,
    loading: appsLoading,
    error: appsError,
  } = useApplications();
  const {
    events: timelineEvents,
    loading: eventsLoading,
    error: eventsError,
  } = useApplicationEvents();

  // Show loading state
  if (appsLoading || eventsLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your applications...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (appsError || eventsError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">
            Error loading data: {appsError || eventsError}
          </p>
        </div>
      </div>
    );
  }

  // Calculate status counts
  const statusCounts: StatusCounts = applications.reduce(
    (acc, app) => {
      acc[app.status]++;
      return acc;
    },
    {
      APPLIED: 0,
      ASSESSMENT: 0,
      INTERVIEW: 0,
      REJECTED: 0,
      OFFERED: 0,
      ACCEPTED: 0,
      WITHDRAWN: 0,
    }
  );

  // Filter timeline events based on selected status
  const filteredEvents =
    selectedStatus === "all"
      ? timelineEvents
      : timelineEvents.filter((event) => {
          const app = applications.find((a) => a.id === event.application_id);
          return app?.status === selectedStatus;
        });

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Job Application Dashboard
          </h1>
          <p className="text-gray-600">
            Track your job applications and stay organized
          </p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <StatusCard
            title="Applied"
            count={statusCounts.APPLIED}
            icon={FileText}
            color="text-blue-600"
            bgColor="bg-blue-100"
          />
          <StatusCard
            title="Assessment"
            count={statusCounts.ASSESSMENT}
            icon={ClipboardCheck}
            color="text-purple-600"
            bgColor="bg-purple-100"
          />
          <StatusCard
            title="Interview"
            count={statusCounts.INTERVIEW}
            icon={Clock}
            color="text-yellow-600"
            bgColor="bg-yellow-100"
          />
          <StatusCard
            title="Offers"
            count={statusCounts.OFFERED}
            icon={CheckCircle}
            color="text-green-600"
            bgColor="bg-green-100"
          />
          <StatusCard
            title="Rejected"
            count={statusCounts.REJECTED}
            icon={XCircle}
            color="text-red-600"
            bgColor="bg-red-100"
          />
        </div>

        {/* Charts */}
        <div className="mb-8">
          <StatsChart statusCounts={statusCounts} />
        </div>

        {/* Filter Controls */}
        <div className="mb-6">
          <FilterControls
            selectedStatus={selectedStatus}
            onStatusChange={setSelectedStatus}
          />
        </div>

        {/* Timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredEvents.length > 0 ? (
                filteredEvents.map((event) => (
                  <TimelineEventComponent key={event.id} event={event} />
                ))
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No recent activity for the selected status
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Dashboard;
