import { useState, useEffect } from "react";
import { supabase } from "@/services/supabase";
import { User } from "@supabase/supabase-js";

const setupUserGmailAutomation = async (session: any) => {
  try {
    const { provider_token, provider_refresh_token } = session;

    if (!provider_token || !provider_refresh_token) {
      console.warn("No OAuth tokens available for Gmail setup");
      return;
    }

    const API_BASE_URL = import.meta.env.VITE_API_URL;

    const response = await fetch(`${API_BASE_URL}/api/auth/setup-user`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        access_token: provider_token,
        refresh_token: provider_refresh_token,
        setup_gmail_automation: true,
        label_name: "Job Applications",
      }),
    });

    const result = await response.json();

    if (result.success) {
      console.log("Gmail automation setup initiated:", result.message);
    } else {
      console.error("Gmail setup failed:", result.error);
    }
  } catch (error) {
    console.error("Error setting up Gmail automation:", error);
  }
};

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      setLoading(false);
    };

    getSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);

      if (event === "SIGNED_IN" && session) {
        setupUserGmailAutomation(session);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        scopes: [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.labels",
          "https://www.googleapis.com/auth/gmail.settings.basic",
        ].join(" "),
        queryParams: {
          access_type: "offline",
          prompt: "consent",
        },
      },
    });
    if (error) throw error;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  return { user, loading, signInWithGoogle, signOut };
};
