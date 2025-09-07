import { useApplications } from "@/hooks/useApplications";
import ApplicationsTable from "@/components/ApplicationsTable";
import Navigation from "@/components/Navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, XCircle } from "lucide-react";

const Spreadsheet = () => {
  const { applications, loading, error, deleteApplication } = useApplications();

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
            Detailed view of all your job applications with search, sort, and
            export capabilities
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>All Applications ({applications.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ApplicationsTable applications={applications} onDelete={deleteApplication} />
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Spreadsheet;
