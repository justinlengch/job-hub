
import { mockApplications } from "@/data/mockData";
import ApplicationsTable from "@/components/ApplicationsTable";
import Navigation from "@/components/Navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table } from "lucide-react";

const Spreadsheet = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <Table className="h-8 w-8 text-primary" />
            Applications Spreadsheet
          </h1>
          <p className="text-gray-600">Detailed view of all your job applications with search, sort, and export capabilities</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>All Applications ({mockApplications.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ApplicationsTable applications={mockApplications} />
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Spreadsheet;
