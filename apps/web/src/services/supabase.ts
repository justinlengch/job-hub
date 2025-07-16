import { createClient } from "@supabase/supabase-js";
import { JobApplication, ApplicationEvent, Email } from "@/types/application";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL!;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

const getCurrentUserId = async (): Promise<string> => {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("User not authenticated");
  return user.id;
};

export const jobApplicationsService = {
  async getApplications(): Promise<JobApplication[]> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });

    if (error) throw error;
    return data || [];
  },

  async getApplicationById(id: string): Promise<JobApplication | null> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .select("*")
      .eq("id", id)
      .eq("user_id", userId)
      .single();

    if (error) throw error;
    return data;
  },

  async updateApplication(
    id: string,
    updates: Partial<JobApplication>
  ): Promise<JobApplication> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .update(updates)
      .eq("id", id)
      .eq("user_id", userId)
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async deleteApplication(id: string): Promise<void> {
    const userId = await getCurrentUserId();
    const { error } = await supabase
      .from("job_applications")
      .delete()
      .eq("id", id)
      .eq("user_id", userId);

    if (error) throw error;
  },

  async getApplicationsByUserId(userId: string): Promise<JobApplication[]> {
    const currentUserId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .select("*")
      .eq("user_id", userId === currentUserId ? userId : currentUserId)
      .order("created_at", { ascending: false });

    if (error) throw error;
    return data || [];
  },

  async createApplication(
    application: Omit<JobApplication, "id" | "created_at" | "last_updated_at">
  ): Promise<JobApplication> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .insert({
        ...application,
        user_id: userId,
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },
};

export const applicationEventsService = {
  async getAllEvents(): Promise<ApplicationEvent[]> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("application_events")
      .select(
        `
        *,
        job_applications!inner(user_id)
      `
      )
      .eq("job_applications.user_id", userId)
      .order("event_date", { ascending: false })
      .limit(20);

    if (error) throw error;
    return data || [];
  },

  async getEventsByApplicationId(
    applicationId: string
  ): Promise<ApplicationEvent[]> {
    const { data, error } = await supabase
      .from("application_events")
      .select("*")
      .eq("application_id", applicationId)
      .order("event_date", { ascending: false });

    if (error) throw error;
    return data || [];
  },

  async createEvent(
    event: Omit<ApplicationEvent, "id" | "created_at">
  ): Promise<ApplicationEvent> {
    const { data, error } = await supabase
      .from("application_events")
      .insert(event)
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async deleteEvent(id: string): Promise<void> {
    const { error } = await supabase
      .from("application_events")
      .delete()
      .eq("id", id);

    if (error) throw error;
  },
};

export const emailsService = {
  async getEmailsByUserId(userId?: string): Promise<Email[]> {
    const currentUserId = await getCurrentUserId();
    const targetUserId = userId || currentUserId;
    const { data, error } = await supabase
      .from("emails")
      .select("*")
      .eq("user_id", targetUserId)
      .order("received_date", { ascending: false });

    if (error) throw error;
    return data || [];
  },

  async getEmailsByApplicationId(applicationId: string): Promise<Email[]> {
    const { data, error } = await supabase
      .from("emails")
      .select("*")
      .eq("application_id", applicationId)
      .order("received_date", { ascending: false });

    if (error) throw error;
    return data || [];
  },

  async createEmail(email: Omit<Email, "id" | "created_at">): Promise<Email> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("emails")
      .insert({
        ...email,
        user_id: userId,
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async updateEmail(id: string, updates: Partial<Email>): Promise<Email> {
    const { data, error } = await supabase
      .from("emails")
      .update(updates)
      .eq("id", id)
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async markEmailAsParsed(
    id: string,
    applicationId: string,
    confidence?: number
  ): Promise<Email> {
    const { data, error } = await supabase
      .from("emails")
      .update({
        parsed: true,
        application_id: applicationId,
        parsing_confidence: confidence,
      })
      .eq("id", id)
      .select()
      .single();

    if (error) throw error;
    return data;
  },
};
