import os

from dotenv import load_dotenv


class Settings:
    load_dotenv()

    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    CRYPTO_KEY_B64: str = os.getenv("CRYPTO_KEY_B64")
    GMAIL_KEY_VERSION: int = int(os.getenv("GMAIL_KEY_VERSION", "1"))
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_PROJECT_ID: str = os.getenv("GOOGLE_PROJECT_ID")

    PUSH_SA_EMAIL: str = os.getenv("PUSH_SA_EMAIL")
    PUBSUB_AUDIENCE: str = os.getenv("PUBSUB_AUDIENCE")
    PROJECT_ID: str = os.getenv("PROJECT_ID") or os.getenv("GOOGLE_PROJECT_ID")
    PUBSUB_TOPIC: str = os.getenv("PUBSUB_TOPIC")
    PUBSUB_TOPIC_FQN: str = os.getenv("PUBSUB_TOPIC_FQN")
    JOB_LABEL_NAME: str = os.getenv("JOB_LABEL_NAME", "Job Applications")
    GMAIL_SCOPES: str = os.getenv(
        "GMAIL_SCOPES",
        "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.labels,https://www.googleapis.com/auth/gmail.settings.basic",
    )
    WATCH_REFRESH_INTERVAL_SECONDS: int = int(
        os.getenv("WATCH_REFRESH_INTERVAL_SECONDS", "300")
    )
    WATCH_REFRESH_THRESHOLD_SECONDS: int = int(
        os.getenv("WATCH_REFRESH_THRESHOLD_SECONDS", "600")
    )
    EMAIL_INGEST_WORKER_CONCURRENCY: int = int(
        os.getenv("EMAIL_INGEST_WORKER_CONCURRENCY", "1")
    )
    EMAIL_INGEST_WORKER_BATCH_SIZE: int = int(
        os.getenv("EMAIL_INGEST_WORKER_BATCH_SIZE", "10")
    )
    EMAIL_INGEST_WORKER_POLL_SECONDS: int = int(
        os.getenv("EMAIL_INGEST_WORKER_POLL_SECONDS", "5")
    )
    EMAIL_INGEST_QUEUE_LEASE_SECONDS: int = int(
        os.getenv("EMAIL_INGEST_QUEUE_LEASE_SECONDS", "300")
    )
    EMAIL_INGEST_MAX_ATTEMPTS: int = int(
        os.getenv("EMAIL_INGEST_MAX_ATTEMPTS", "5")
    )


settings = Settings()
