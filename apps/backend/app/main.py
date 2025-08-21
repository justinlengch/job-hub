from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.gmail import router as gmail_router
from app.routes.parse import router as parse_router
from app.routes.pubsub import router as pubsub_router

app = FastAPI(
    title="Job Hub API",
    description="API for parsing job application emails and managing job applications",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://job-hub-web.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Job Hub API is healthy"}


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Job Hub API is running"}


app.include_router(parse_router, prefix="/api")
app.include_router(gmail_router)
app.include_router(auth_router)
app.include_router(pubsub_router, prefix="/api")
