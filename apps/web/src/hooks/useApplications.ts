import { useState, useEffect } from "react";
import { jobApplicationsService } from "@/services/supabase";
import { JobApplication } from "@/types/application";

export const useApplications = (userId?: string) => {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApplications = async () => {
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
  };

  useEffect(() => {
    fetchApplications();
  }, [userId]);

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
    deleteApplication,
  };
};
