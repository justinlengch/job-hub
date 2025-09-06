import { useState, useEffect } from "react";
import { supabase } from "@/services/supabase";

export const useGmailAutomation = () => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLinked, setIsLinked] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAutomationStatus = async () => {
      try {
        const session = await supabase.auth.getSession();

        if (!session?.data?.session) {
          setIsLoading(false);
          return;
        }

        const API_BASE_URL = import.meta.env.VITE_API_URL;

        const response = await fetch(
          `${API_BASE_URL}/api/auth/user-preferences`,
          {
            headers: {
              Authorization: `Bearer ${session.data.session.access_token}`,
            },
          }
        );

        const result = await response.json();

        if (result.success) {
          const linked = Boolean(
            result.preferences?.gmail_refresh_nonce_b64 &&
              result.preferences?.gmail_refresh_cipher_b64
          );
          setIsLinked(linked);
          setIsEnabled(Boolean(result.preferences?.gmail_automation_enabled && linked));
        }
      } catch (error) {
        console.error("Error checking Gmail automation status:", error);
      } finally {
        setIsLoading(false);
      }
    };

    checkAutomationStatus();
  }, []);

  return { isEnabled, isLinked, isLoading };
};
