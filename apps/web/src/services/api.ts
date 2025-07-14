import { EmailParseRequest, EmailParseResponse } from "@/types/application";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const apiService = {
  async parseEmail(data: EmailParseRequest): Promise<EmailParseResponse> {
    const response = await fetch(`${API_BASE_URL}/api/parse-email`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to parse email");
    }

    return response.json();
  },
};
