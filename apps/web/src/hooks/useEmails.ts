import { useState, useEffect } from "react";
import { emailsService } from "@/services/supabase";
import { Email } from "@/types/application";

export const useEmails = (applicationId?: string, userId?: string) => {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEmails = async () => {
    try {
      setLoading(true);
      setError(null);

      let data: Email[];
      if (applicationId) {
        data = await emailsService.getEmailsByApplicationId(applicationId);
      } else {
        data = await emailsService.getEmailsByUserId(userId);
      }

      setEmails(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch emails");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmails();
  }, [applicationId, userId]);

  const createEmail = async (email: Omit<Email, "id" | "created_at">) => {
    try {
      const newEmail = await emailsService.createEmail(email);
      setEmails((prev) => [newEmail, ...prev]);
      return newEmail;
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to create email"
      );
    }
  };

  const updateEmail = async (id: string, updates: Partial<Email>) => {
    try {
      const updated = await emailsService.updateEmail(id, updates);
      setEmails((prev) =>
        prev.map((email) => (email.id === id ? updated : email))
      );
      return updated;
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to update email"
      );
    }
  };

  const markEmailAsParsed = async (
    id: string,
    applicationId: string,
    confidence?: number
  ) => {
    try {
      const updated = await emailsService.markEmailAsParsed(
        id,
        applicationId,
        confidence
      );
      setEmails((prev) =>
        prev.map((email) => (email.id === id ? updated : email))
      );
      return updated;
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to mark email as parsed"
      );
    }
  };

  return {
    emails,
    loading,
    error,
    refetch: fetchEmails,
    createEmail,
    updateEmail,
    markEmailAsParsed,
  };
};
