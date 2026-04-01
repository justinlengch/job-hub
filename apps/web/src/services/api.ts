import { supabase } from "./supabase";
import {
  EmailParseRequest,
  EmailParseResponse,
  FinalRoundToggleResponse,
  LinkedInImportOptions,
  LinkedInImportResult,
  ManualApplicationEventCreate,
  ReviewQueueResponse,
  SankeySnapshotFilters,
  SankeyResponse,
} from "@/types/application";

const API_BASE_URL = import.meta.env.VITE_API_URL;

const getAccessToken = async () => {
  const {
    data: { session: initialSession },
  } = await supabase.auth.getSession();

  let session = initialSession;
  const expiresAt = session?.expires_at ? session.expires_at * 1000 : null;
  const isExpiringSoon = expiresAt ? expiresAt <= Date.now() + 60_000 : false;

  if (!session?.access_token || isExpiringSoon) {
    const { data, error } = await supabase.auth.refreshSession();
    if (!error) {
      session = data.session;
    }
  }

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

  async importLinkedInHistory(
    file: File,
    options: LinkedInImportOptions = {}
  ): Promise<LinkedInImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    if (options.min_applied_date) {
      formData.append("min_applied_date", options.min_applied_date);
    }
    if (options.max_applied_date) {
      formData.append("max_applied_date", options.max_applied_date);
    }
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

  async generateSankeyData(
    filters?: Pick<SankeySnapshotFilters, "start_date" | "end_date">
  ): Promise<SankeyResponse> {
    return requestJson<SankeyResponse>("/api/analytics/sankey/generate", {
      method: "POST",
      body: JSON.stringify(filters ?? {}),
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

  async createManualApplicationEvent(
    applicationId: string,
    payload: ManualApplicationEventCreate
  ): Promise<void> {
    return requestJson<void>(`/api/applications/${applicationId}/events`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
