
import { useState } from "react";
import { mockApplications, mockTimelineEvents } from "@/data/mockData";
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
  TrendingUp
} from "lucide-react";

const Dashboard = () => {
  const [selectedStatus, setSelectedStatus] = useState<JobApplication['status'] | 'all'>('all');

  // Calculate status counts
  const statusCounts: StatusCounts = mockApplications.reduce(
    (acc, app) => {
      acc[app.status]++;
      return acc;
    },
    { applied: 0, 'in-progress': 0, offer: 0, rejected: 0 }
  );

  // Filter timeline events based on selected status
  const filteredEvents = selectedStatus === 'all' 
    ? mockTimelineEvents 
    : mockTimelineEvents.filter(event => event.status === selectedStatus);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Job Application Dashboard</h1>
          <p className="text-gray-600">Track your job applications and stay organized</p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatusCard
            title="Applied"
            count={statusCounts.applied}
            icon={FileText}
            color="text-blue-600"
            bgColor="bg-blue-100"
          />
          <StatusCard
            title="In Progress"
            count={statusCounts['in-progress']}
            icon={Clock}
            color="text-yellow-600"
            bgColor="bg-yellow-100"
          />
          <StatusCard
            title="Offers"
            count={statusCounts.offer}
            icon={CheckCircle}
            color="text-green-600"
            bgColor="bg-green-100"
          />
          <StatusCard
            title="Rejected"
            count={statusCounts.rejected}
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
