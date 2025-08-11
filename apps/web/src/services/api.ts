import { EmailParseRequest, EmailParseResponse } from "@/types/application";
import { supabase } from "./supabase";

const API_BASE_URL = import.meta.env.BACKEND_API_URL;

const getAuthHeaders = async () => {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error("No authentication token available");
  }

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.access_token}`,
  };
};

export const apiService = {
  async parseEmail(data: EmailParseRequest): Promise<EmailParseResponse> {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}/api/parse-email`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to parse email");
    }

    return response.json();
  },
};
