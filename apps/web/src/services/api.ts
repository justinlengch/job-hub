import { supabase } from "./supabase";
import {
  EmailParseRequest,
  EmailParseResponse,
  FinalRoundToggleResponse,
  LinkedInImportResult,
  ReviewQueueResponse,
  SankeyResponse,
} from "@/types/application";

const API_BASE_URL = import.meta.env.VITE_API_URL;

const getAccessToken = async () => {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error("No authentication token available");
  }

  return session.access_token;
};

const getAuthHeaders = async (contentType?: string) => {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${await getAccessToken()}`,
  };

  if (contentType) {
    headers["Content-Type"] = contentType;
  }

  return headers;
};

const parseJsonResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const error = await response.json();
      detail = error.detail || error.message || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
};

const requestJson = async <T>(
  path: string,
  init: RequestInit = {}
): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(await getAuthHeaders("application/json")),
      ...(init.headers || {}),
    },
  });

  return parseJsonResponse<T>(response);
};

const requestFormData = async <T>(path: string, formData: FormData): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: await getAuthHeaders(),
    body: formData,
  });

  return parseJsonResponse<T>(response);
};

export const apiService = {
  async parseEmail(data: EmailParseRequest): Promise<EmailParseResponse> {
    return requestJson<EmailParseResponse>("/api/parse-email", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async importLinkedInHistory(file: File): Promise<LinkedInImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    return requestFormData<LinkedInImportResult>("/api/linkedin/import", formData);
  },

  async getReviewQueue(): Promise<ReviewQueueResponse> {
    return requestJson<ReviewQueueResponse>("/api/applications/review-queue");
  },

  async confirmReviewQueueItem(sourceId: string): Promise<{ success: boolean }> {
    return requestJson<{ success: boolean }>(
      `/api/applications/review-queue/${sourceId}/confirm`,
      { method: "POST" }
    );
  },

  async separateReviewQueueItem(sourceId: string): Promise<{ success: boolean }> {
    return requestJson<{ success: boolean }>(
      `/api/applications/review-queue/${sourceId}/separate`,
      { method: "POST" }
    );
  },

  async getSankeyData(params?: {
    start_date?: string;
    end_date?: string;
    source_type?: string;
    company?: string;
  }): Promise<SankeyResponse> {
    const search = new URLSearchParams();
    if (params?.start_date) search.set("start_date", params.start_date);
    if (params?.end_date) search.set("end_date", params.end_date);
    if (params?.source_type) search.set("source_type", params.source_type);
    if (params?.company) search.set("company", params.company);

    const query = search.toString();
    return requestJson<SankeyResponse>(
      `/api/analytics/sankey${query ? `?${query}` : ""}`
    );
  },

  async generateSankeyData(): Promise<SankeyResponse> {
    return requestJson<SankeyResponse>("/api/analytics/sankey/generate", {
      method: "POST",
    });
  },

  async toggleFinalRound(
    applicationId: string,
    enabled: boolean
  ): Promise<FinalRoundToggleResponse> {
    return requestJson<FinalRoundToggleResponse>(
      `/api/applications/${applicationId}/final-round`,
      {
        method: enabled ? "POST" : "DELETE",
      }
    );
  },
};
