import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { BarChart3, Table, FileText, LogOut } from "lucide-react";

const Navigation = () => {
  const location = useLocation();
  const { signOut } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error("Sign out error:", error);
    }
  };

  return (
    <nav className="bg-white border-b shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-2">
            <FileText className="h-8 w-8 text-blue-600" />
            <h1 className="text-xl font-bold text-gray-900">Job Hub</h1>
          </div>

          <div className="flex items-center gap-4">
            <Button
              variant={isActive("/dashboard") ? "default" : "ghost"}
              asChild
              className="flex items-center gap-2"
            >
              <Link to="/dashboard">
                <BarChart3 className="h-4 w-4" />
                Dashboard
              </Link>
            </Button>

            <Button
              variant={isActive("/dashboard/spreadsheet") ? "default" : "ghost"}
              asChild
              className="flex items-center gap-2"
            >
              <Link to="/dashboard/spreadsheet">
                <Table className="h-4 w-4" />
                Spreadsheet
              </Link>
            </Button>

            <Button
              variant="ghost"
              onClick={handleSignOut}
              className="flex items-center gap-2"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
