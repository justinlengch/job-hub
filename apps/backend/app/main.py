from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.gmail import router as gmail_router
from app.routes.parse import router as parse_router

app = FastAPI(
    title="Job Hub API",
    description="API for parsing job application emails and managing job applications",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Default Vite dev server
        # Add your production frontend URL when deploying
        "https://job-hub-web.vercel.app"
    ],
    allow_origin_regex=r"https://job-hub-web(-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
