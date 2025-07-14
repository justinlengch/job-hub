import { useState, useEffect } from "react";
import { applicationEventsService } from "@/services/supabase";
import { ApplicationEvent } from "@/types/application";

export const useApplicationEvents = (applicationId?: string) => {
  const [events, setEvents] = useState<ApplicationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      setError(null);

      let data: ApplicationEvent[];
      if (applicationId) {
        data = await applicationEventsService.getEventsByApplicationId(
          applicationId
        );
      } else {
        data = await applicationEventsService.getAllEvents();
      }

      setEvents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [applicationId]);

  const createEvent = async (
    event: Omit<ApplicationEvent, "id" | "created_at">
  ) => {
    try {
      const newEvent = await applicationEventsService.createEvent(event);
      setEvents((prev) => [newEvent, ...prev]);
      return newEvent;
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to create event"
      );
    }
  };

  const deleteEvent = async (id: string) => {
    try {
      await applicationEventsService.deleteEvent(id);
      setEvents((prev) => prev.filter((event) => event.id !== id));
    } catch (err) {
      throw new Error(
        err instanceof Error ? err.message : "Failed to delete event"
      );
    }
  };

  return {
    events,
    loading,
    error,
    refetch: fetchEvents,
    createEvent,
    deleteEvent,
  };
};
