import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/services/supabase";

function base64UrlDecode(input: string): string {
  // Convert from base64url to base64
  let s = input.replace(/-/g, "+").replace(/_/g, "/");
  // Add padding
  const pad = s.length % 4;
  if (pad === 2) s += "==";
  else if (pad === 3) s += "=";
  else if (pad !== 0) throw new Error("Invalid base64url string");
  // Decode
  try {
    return decodeURIComponent(
      Array.prototype.map
        .call(atob(s), (c: string) => {
          return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join("")
    );
  } catch {
    // Fallback if URI decoding fails
    return atob(s);
  }
}

function parseSuccessUrlFromState(state?: string | null): string | null {
  if (!state) return null;
  try {
    const decoded = base64UrlDecode(state);
    const obj = JSON.parse(decoded);
    const url = obj?.success_url;
    if (typeof url !== "string") return null;
    return url;
  } catch {
    return null;
  }
}

export default function OAuthCallback() {
  const navigate = useNavigate();
  const [message, setMessage] = useState<string>("Linking your Google account…");
  const [error, setError] = useState<string | null>(null);

  const currentUrl = useMemo(() => new URL(window.location.href), []);
  const code = currentUrl.searchParams.get("code");
  const state = currentUrl.searchParams.get("state");
  const successUrlFromState = useMemo(() => parseSuccessUrlFromState(state), [state]);
  const defaultSuccessPath = "/settings";

  useEffect(() => {
    const run = async () => {
      const API_BASE_URL = import.meta.env.VITE_API_URL as string | undefined;
      if (!API_BASE_URL) {
        setError("Missing API base URL configuration.");
        return;
      }

      if (!code) {
        setError("Missing authorization code.");
        return;
      }

      // Must be signed in to attach Supabase JWT to the backend callback request
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session?.access_token) {
        setError("You must be signed in first. Please sign in and try again.");
        return;
      }

      const redirectUri = `${window.location.origin}/oauth/google/callback`;
      const callbackUrl = new URL(`${API_BASE_URL}/api/auth/google/callback`);
      callbackUrl.searchParams.set("code", code);
      callbackUrl.searchParams.set("redirect_uri", redirectUri);
      if (state) callbackUrl.searchParams.set("state", state);

      setMessage("Finalizing account linking…");
      try {
        const resp = await fetch(callbackUrl.toString(), {
          method: "GET",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        // If backend responds with non-OK, surface the error text
        if (!resp.ok) {
          const text = await resp.text();
          setError(
            `Failed to complete linking. ${
              text || `Status ${resp.status}`
            }`
          );
          return;
        }

        // Best-effort parse; backend might 302 in a browser-initiated flow
        // but fetch won't navigate. That's okay—we navigate client-side below.
        await resp
          .clone()
          .json()
          .catch(() => null);

        // Clean up the URL to remove code/state from the address bar
        try {
          window.history.replaceState(
            {},
            document.title,
            window.location.origin + window.location.pathname
          );
        } catch {
          // ignore history errors
        }

        // Prefer success_url from state if it matches the frontend origin
        const target = (() => {
          if (successUrlFromState && successUrlFromState.startsWith(window.location.origin)) {
            try {
              const u = new URL(successUrlFromState);
              return u.pathname + u.search + u.hash;
            } catch {
              // Fallback to stripping origin
              return successUrlFromState.replace(window.location.origin, "");
            }
          }
          return defaultSuccessPath;
        })();

        setMessage("Linked successfully. Redirecting…");
        navigate(target, { replace: true });
      } catch (e: any) {
        setError(e?.message || "Unexpected error during linking.");
      }
    };

    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        {!error ? (
          <>
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4" />
            <p className="text-gray-700">{message}</p>
          </>
        ) : (
          <>
            <p className="text-red-600 mb-4 font-medium">OAuth Linking Error</p>
            <p className="text-gray-700 mb-6">{error}</p>
            <button
              className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              onClick={() => navigate("/", { replace: true })}
            >
              Go to Sign In
            </button>
          </>
        )}
      </div>
    </div>
  );
}
