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
  const { isEnabled, isLinked, isLoading: checkingStatus } = useGmailAutomation();

  const handleGmailSetup = async () => {
    setIsLoading(true);
    setSetupStatus(null);

    try {
      const session = await supabase.auth.getSession();

      if (!session?.data?.session) {
        setSetupStatus("Please sign in first");
        return;
      }

      const API_BASE_URL = import.meta.env.VITE_API_URL;

      const redirectUri = `${window.location.origin}/oauth/google/callback`;
      const successUrl = `${window.location.origin}/settings/integrations`;

      const startUrl = new URL(`${API_BASE_URL}/api/auth/google/start`);
      startUrl.searchParams.set("redirect_uri", redirectUri);
      startUrl.searchParams.set("success_url", successUrl);


      const response = await fetch(startUrl.toString(), {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.data.session.access_token}`,
        },
      });

      if (!response.ok) {
        const errText = await response.text();
        setSetupStatus(`Failed to start Google OAuth: ${errText}`);
        return;
      }

      const data = await response.json();
      if (data?.auth_url) {
        setSetupStatus("Redirecting to Google for consent...");
        window.location.href = data.auth_url;
        return;
      }

      setSetupStatus("Failed to get Google OAuth URL. Please try again.");
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
          {!isLinked
            ? "Link your Gmail account to set up automatic email parsing"
            : isEnabled
            ? "Gmail automation is active and monitoring your emails"
            : "Gmail is linked; enable automation to start monitoring"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isEnabled ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm font-medium">
                Gmail automation is enabled
              </span>
            </div>
            <Button
              onClick={handleGmailSetup}
              disabled={isLoading}
              variant="outline"
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Opening Google consent...
                </>
              ) : (
                <>
                  <Mail className="h-4 w-4 mr-2" />
                  Re-link Gmail Account
                </>
              )}
            </Button>
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
