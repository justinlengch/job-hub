import { createClient } from "@supabase/supabase-js";
import { JobApplication, ApplicationEvent, Email, EmailRef } from "@/types/application";

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
      .order("last_updated_at", { ascending: false });

    if (error) throw error;
    type DbJobApplication = Omit<JobApplication, "id" | "created_at"> & {
      application_id: string;
      created_at: string;
      applied_date?: string;
    };
    const rows = (data ?? []) as DbJobApplication[];
    return rows.map((row) => {
      const createdAt = row.applied_date ?? row.created_at;
      // Normalize last_updated_at: if null/epoch fallback to applied_date or created_at
      let lastUpdated = row.last_updated_at;
      if (!lastUpdated || new Date(lastUpdated).getTime() === 0) {
        lastUpdated = row.applied_date ?? row.created_at ?? lastUpdated;
      }
      return {
        ...row,
        created_at: createdAt,
        last_updated_at: lastUpdated,
        id: row.application_id,
      };
    });
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
    if (!data) return null;
    {
      type DbJobApplication = Omit<JobApplication, "id" | "created_at"> & {
        application_id: string;
        created_at: string;
        applied_date?: string;
        last_updated_at?: string | null;
      };
      const row = data as unknown as DbJobApplication;
      const createdAt = row.applied_date ?? row.created_at;
      let lastUpdated = row.last_updated_at;
      if (!lastUpdated || new Date(lastUpdated).getTime() === 0) {
        lastUpdated = row.applied_date ?? row.created_at ?? lastUpdated;
      }
      const shaped: JobApplication = {
        ...(row as Omit<JobApplication, "id" | "created_at">),
        id: row.application_id,
        created_at: createdAt,
        last_updated_at: lastUpdated || createdAt,
      };
      return shaped;
    }
  },

  async updateApplication(
    id: string,
    updates: Partial<JobApplication>
  ): Promise<JobApplication> {
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .update(updates)
      .eq("application_id", id)
      .eq("user_id", userId)
      .select()
      .single();

    if (error) throw error;
    if (!data) return null;
    {
      type DbJobApplication = Omit<JobApplication, "id" | "created_at"> & {
        application_id: string;
        created_at: string;
        applied_date?: string;
        last_updated_at?: string | null;
      };
      const row = data as unknown as DbJobApplication;
      const createdAt = row.applied_date ?? row.created_at;
      let lastUpdated = row.last_updated_at;
      if (!lastUpdated || new Date(lastUpdated).getTime() === 0) {
        lastUpdated = row.applied_date ?? row.created_at ?? lastUpdated;
      }
      const shaped: JobApplication = {
        ...(row as Omit<JobApplication, "id" | "created_at">),
        id: row.application_id,
        created_at: createdAt,
        last_updated_at: lastUpdated || createdAt,
      };
      return shaped;
    }
  },

  async deleteApplication(id: string): Promise<void> {
    const userId = await getCurrentUserId();
    const { error } = await supabase
      .from("job_applications")
      .delete()
      .eq("application_id", id)
      .eq("user_id", userId);

    if (error) throw error;
  },

  async getApplicationsByUserId(userId: string): Promise<JobApplication[]> {
    const currentUserId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("job_applications")
      .select("*")
      .eq("user_id", userId === currentUserId ? userId : currentUserId)
      .order("last_updated_at", { ascending: false });

    if (error) throw error;
    type DbJobApplication = Omit<JobApplication, "id" | "created_at"> & {
      application_id: string;
      created_at: string;
      applied_date?: string;
      last_updated_at?: string | null;
    };
    const rows = (data ?? []) as DbJobApplication[];
    return rows.map((row) => {
      const createdAt = row.applied_date ?? row.created_at;
      let lastUpdated = row.last_updated_at;
      if (!lastUpdated || new Date(lastUpdated).getTime() === 0) {
        lastUpdated = row.applied_date ?? row.created_at ?? lastUpdated;
      }
      return {
        ...row,
        created_at: createdAt,
        last_updated_at: lastUpdated || createdAt,
        id: row.application_id,
      };
    });
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
        // If backend trigger doesn't immediately set last_updated_at, initialize it to applied_date or now
        last_updated_at: (application as any).applied_date || new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw error;
    {
      type DbJobApplication = Omit<JobApplication, "id" | "created_at"> & {
        application_id: string;
        created_at: string;
        applied_date?: string;
        last_updated_at?: string | null;
      };
      const row = data as unknown as DbJobApplication;
      const createdAt = row.applied_date ?? row.created_at;
      let lastUpdated = row.last_updated_at;
      if (!lastUpdated || new Date(lastUpdated).getTime() === 0) {
        lastUpdated = row.applied_date ?? row.created_at ?? lastUpdated;
      }
      const shaped: JobApplication = {
        ...(row as Omit<JobApplication, "id" | "created_at">),
        id: row.application_id,
        created_at: createdAt,
        last_updated_at: lastUpdated || createdAt,
      };
      return shaped;
    }
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
        job_applications!inner(user_id,company,role)
      `
      )
      .eq("job_applications.user_id", userId)
      .order("event_date", { ascending: false })
      .limit(20);

    if (error) throw error;
    return (data || []).map((e: any) => ({
      ...e,
      company: e?.company ?? e?.job_applications?.company ?? undefined,
      role: e?.role ?? e?.job_applications?.role ?? undefined,
    }));
  },

  async getEventsByApplicationId(
    applicationId: string
  ): Promise<ApplicationEvent[]> {
    const { data, error } = await supabase
      .from("application_events")
      .select(`
        *,
        job_applications!inner(company,role)
      `)
      .eq("application_id", applicationId)
      .order("event_date", { ascending: false });

    if (error) throw error;
    return (data || []).map((e: any) => ({
      ...e,
      company: e?.company ?? e?.job_applications?.company ?? undefined,
      role: e?.role ?? e?.job_applications?.role ?? undefined,
    }));
  },

  async createEvent(
    event: Omit<ApplicationEvent, "id" | "created_at">
  ): Promise<ApplicationEvent> {
    const { data, error } = await supabase
      .from("application_events")
      .insert(event)
      .select(`
        *,
        job_applications!inner(company,role)
      `)
      .single();

    if (error) throw error;
    return {
      ...data,
      company: (data as any)?.company ?? (data as any)?.job_applications?.company ?? undefined,
      role: (data as any)?.role ?? (data as any)?.job_applications?.role ?? undefined,
    } as any;
  },

  async deleteEvent(id: string): Promise<void> {
    const { error } = await supabase
      .from("application_events")
      .delete()
      .eq("id", id);

    if (error) throw error;
  },

  async getEventsWithEmailRefsByApplicationId(
    applicationId: string
  ): Promise<ApplicationEvent[]> {
    const { data, error } = await supabase
      .from("application_events")
      .select(`
        *,
        job_applications!inner(company,role)
      `)
      .eq("application_id", applicationId);

    if (error) throw error;
    const events = (data || []).map((e: any) => ({
      ...e,
      company: e?.company ?? e?.job_applications?.company ?? undefined,
      role: e?.role ?? e?.job_applications?.role ?? undefined,
    }));

    const emailIds = Array.from(
      new Set(events.map((e: any) => e.email_id).filter(Boolean))
    ) as string[];

    let refsById: Record<string, any> = {};
    if (emailIds.length) {
      const { data: refData, error: refErr } = await supabase
        .from("email_refs")
        .select("email_id,external_email_id,thread_id,received_at")
        .in("email_id", emailIds);
      if (refErr) throw refErr;
      refsById = Object.fromEntries(
        (refData || []).map((r: any) => [r.email_id, r])
      );
    }

    const enriched = await Promise.all(
      events.map(async (e: any) => {
        const ref = refsById[e.email_id as string];
        let gmail_url: string | undefined;
        let email_received_at: string | undefined;
        if (ref) {
          gmail_url = await buildGmailUrlWithPrefs(
            ref.external_email_id,
            ref.thread_id
          );
          email_received_at = ref.received_at;
        }
        return { ...e, gmail_url, email_received_at };
      })
    );

    enriched.sort((a: any, b: any) => {
      const ad = a.email_received_at || a.event_date;
      const bd = b.email_received_at || b.event_date;
      return new Date(ad).getTime() - new Date(bd).getTime();
    });

    return enriched as ApplicationEvent[];
  },

  async getEventsWithEmailRefsByApplicationIds(
    applicationIds: string[]
  ): Promise<Record<string, ApplicationEvent[]>> {
    if (!applicationIds?.length) return {};
    const { data, error } = await supabase
      .from("application_events")
      .select(`
        *,
        job_applications!inner(company,role)
      `)
      .in("application_id", applicationIds);

    if (error) throw error;

    const events = (data || []).map((e: any) => ({
      ...e,
      company: e?.company ?? e?.job_applications?.company ?? undefined,
      role: e?.role ?? e?.job_applications?.role ?? undefined,
    }));

    const emailIds = Array.from(
      new Set(events.map((e: any) => e.email_id).filter(Boolean))
    ) as string[];

    let refsById: Record<string, any> = {};
    if (emailIds.length) {
      const { data: refData, error: refErr } = await supabase
        .from("email_refs")
        .select("email_id,external_email_id,thread_id,received_at")
        .in("email_id", emailIds);
      if (refErr) throw refErr;
      refsById = Object.fromEntries(
        (refData || []).map((r: any) => [r.email_id, r])
      );
    }

    const enriched = await Promise.all(
      events.map(async (e: any) => {
        const ref = refsById[e.email_id as string];
        let gmail_url: string | undefined;
        let email_received_at: string | undefined;
        if (ref) {
          gmail_url = await buildGmailUrlWithPrefs(
            ref.external_email_id,
            ref.thread_id
          );
          email_received_at = ref.received_at;
        }
        return { ...e, gmail_url, email_received_at };
      })
    );

    const grouped: Record<string, ApplicationEvent[]> = {};
    for (const e of enriched as any[]) {
      const appId = e.application_id as string;
      if (!grouped[appId]) grouped[appId] = [];
      grouped[appId].push(e);
    }
    for (const appId of Object.keys(grouped)) {
      grouped[appId].sort((a: any, b: any) => {
        const ad = a.email_received_at || a.event_date;
        const bd = b.email_received_at || b.event_date;
        return new Date(ad).getTime() - new Date(bd).getTime();
      });
    }
    return grouped;
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
    const userId = await getCurrentUserId();
    const { data, error } = await supabase
      .from("emails")
      .update(updates)
      .eq("application_id", id)
      .eq("user_id", userId)
      .select()
      .single();

    if (error) throw error;
    return { ...(data as any), id: (data as any).application_id } as any;
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

export const buildGmailUrl = (
  externalEmailId?: string,
  threadId?: string,
  accountIndex: number = 0
): string => {
  const anchor = threadId || externalEmailId;
  return anchor
    ? `https://mail.google.com/mail/u/${accountIndex}/#all/${anchor}`
    : `https://mail.google.com/mail/u/${accountIndex}/#inbox`;
};

export const emailRefsService = {
  async getRefsByApplicationId(applicationId?: string): Promise<EmailRef[]> {
    const userId = await getCurrentUserId();
    let query = supabase
      .from("email_refs")
      .select("*")
      .eq("user_id", userId);
    if (applicationId) {
      query = query.eq("application_id", applicationId);
    }
    const { data, error } = await query.order("received_at", { ascending: false });

    if (error) throw error;
    const list = (data || []) as any[];
    return list.map((row) => ({
      ...row,
      gmail_url: buildGmailUrl(row.external_email_id, row.thread_id),
    }));
  },

  async getLatestRefByApplicationId(
    applicationId?: string
  ): Promise<EmailRef | null> {
    if (!applicationId) return null;
    const refs = await this.getRefsByApplicationId(applicationId);
    return refs[0] || null;
  },

  async getRefsForUser(userId?: string): Promise<EmailRef[]> {
    const currentUserId = await getCurrentUserId();
    const targetUserId = userId || currentUserId;
    const { data, error } = await supabase
      .from("email_refs")
      .select("*")
      .eq("user_id", targetUserId)
      .order("received_at", { ascending: false });

    if (error) throw error;
    const list = (data || []) as any[];
    return list.map((row) => ({
      ...row,
      gmail_url: buildGmailUrl(row.external_email_id, row.thread_id),
    }));
  },
};

export const userPreferencesService = {
  async getPreferences(userId?: string): Promise<{ user_id: string; gmail_email: string } | null> {
    const currentUserId = await getCurrentUserId();
    const targetUserId = userId || currentUserId;

    const { data, error } = await supabase
      .from("user_preferences")
      .select("user_id,gmail_email")
      .eq("user_id", targetUserId)
      .limit(1);

    if (error) throw error;
    const row = (data || [])[0];
    return row || null;
  },

  getGmailAccountIndexFromPreferences(
    prefs: { gmail_email?: string } | null,
    fallbackIndex: number = 0
  ): number {
    try {
      if (typeof window === "undefined" || !prefs?.gmail_email) return fallbackIndex;
      const key = `gmailAccountIndex:${prefs.gmail_email}`;
      const raw = window.localStorage.getItem(key);
      const idx = raw ? parseInt(raw, 10) : NaN;
      return Number.isFinite(idx) && idx >= 0 ? idx : fallbackIndex;
    } catch {
      return fallbackIndex;
    }
  },

  async getGmailAccountIndexForUser(userId?: string, fallbackIndex: number = 0): Promise<number> {
    const prefs = await this.getPreferences(userId);
    return this.getGmailAccountIndexFromPreferences(prefs, fallbackIndex);
  },
};

export const buildGmailUrlWithPrefs = async (
  externalEmailId?: string,
  threadId?: string,
  userId?: string
): Promise<string> => {
  const prefs = await userPreferencesService.getPreferences(userId);
  const anchor = threadId || externalEmailId;
  const base = "https://mail.google.com/mail/";
  if (anchor && prefs?.gmail_email) {
    const email = encodeURIComponent(prefs.gmail_email);
    return `${base}?authuser=${email}#all/${anchor}`;
  }
  if (anchor) {
    return `${base}#all/${anchor}`;
  }
  return `${base}#inbox`;
};
