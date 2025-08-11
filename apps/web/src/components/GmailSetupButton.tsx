import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Mail, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { supabase } from "@/services/supabase";
import { useGmailAutomation } from "@/hooks/useGmailAutomation";

export const GmailSetupButton = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [setupStatus, setSetupStatus] = useState<string | null>(null);
  const { isEnabled, isLoading: checkingStatus } = useGmailAutomation();

  const handleGmailSetup = async () => {
    setIsLoading(true);
    setSetupStatus(null);

    try {
      const session = await supabase.auth.getSession();

      if (!session?.data?.session) {
        setSetupStatus("Please sign in first");
        return;
      }

      const { provider_token, provider_refresh_token } = session.data.session;

      if (!provider_token || !provider_refresh_token) {
        setSetupStatus(
          "No Gmail tokens found. Please sign in again with Gmail permissions."
        );
        return;
      }

      const API_BASE_URL = import.meta.env.BACKEND_API_URL;

      const response = await fetch(`${API_BASE_URL}/api/auth/setup-user`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.data.session.access_token}`,
        },
        body: JSON.stringify({
          access_token: provider_token,
          refresh_token: provider_refresh_token,
          setup_gmail_automation: true,
          label_name: "Job Applications",
        }),
      });

      const result = await response.json();
      setSetupStatus(result.success ? result.message : result.error);
    } catch (error) {
      setSetupStatus("Setup failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (checkingStatus) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Gmail Integration
          </CardTitle>
          <CardDescription>Checking automation status...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Gmail Integration
        </CardTitle>
        <CardDescription>
          {isEnabled
            ? "Gmail automation is active and monitoring your emails"
            : "Set up automatic email parsing and organization"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isEnabled ? (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm font-medium">
              Gmail automation is enabled
            </span>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Enable Gmail automation to:
              </p>
              <ul className="text-sm text-muted-foreground ml-4 space-y-1">
                <li>• Automatically parse job-related emails</li>
                <li>• Organize emails with labels and filters</li>
                <li>• Track application status changes</li>
              </ul>
            </div>
            <Button
              onClick={handleGmailSetup}
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Setting up...
                </>
              ) : (
                <>
                  <Mail className="h-4 w-4 mr-2" />
                  Set Up Gmail Automation
                </>
              )}
            </Button>
          </>
        )}
        {setupStatus && (
          <div
            className={`flex items-center gap-2 p-3 rounded-md ${
              setupStatus.toLowerCase().includes("success") ||
              setupStatus.toLowerCase().includes("initiated")
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-red-50 text-red-700 border border-red-200"
            }`}
          >
            {setupStatus.toLowerCase().includes("success") ||
            setupStatus.toLowerCase().includes("initiated") ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <span className="text-sm">{setupStatus}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
