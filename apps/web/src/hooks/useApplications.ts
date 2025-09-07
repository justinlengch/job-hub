import { useState, useEffect, useCallback } from "react";
import { jobApplicationsService, supabase } from "@/services/supabase";
import { JobApplication } from "@/types/application";

export const useApplications = (userId?: string) => {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApplications = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let data: JobApplication[];
      if (userId) {
        data = await jobApplicationsService.getApplicationsByUserId(userId);
      } else {
        data = await jobApplicationsService.getApplications();
      }

      setApplications(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch applications"
      );
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const updateApplication = async (
    id: string,
    updates: Partial<JobApplication>
  ) => {
    try {
      const updated = await jobApplicationsService.updateApplication(
        id,
        updates
      );
      setApplications((prev) =>
        prev.map((app) => (app.id === id ? updated : app))
      );
      return updated;
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to update application"
      );
    }
  };

  const createApplication = async (
    application: Omit<JobApplication, "id" | "created_at" | "last_updated_at" | "user_id">
  ): Promise<JobApplication> => {
    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user?.id) {
        throw new Error("User not authenticated");
      }
      const payload: Omit<JobApplication, "id" | "created_at" | "last_updated_at"> = {
        ...application,
        user_id: user.id,
      };
      const created = await jobApplicationsService.createApplication(payload);
      setApplications((prev) => [created, ...prev]);
      return created;
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to create application"
      );
    }
  };

  const deleteApplication = async (id: string) => {
    try {
      await jobApplicationsService.deleteApplication(id);
      setApplications((prev) => prev.filter((app) => app.id !== id));
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to delete application"
      );
    }
  };

  return {
    applications,
    loading,
    error,
    refetch: fetchApplications,
    updateApplication,
    createApplication,
    deleteApplication,
  };
};
