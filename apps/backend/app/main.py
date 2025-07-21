from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# TODO: Email Parsing Enhancement - Complete Implementation
# This file coordinates all the email parsing tasks. See individual TODOs in:
# - Task 1: app/models/llm/llm_email.py
# - Task 2: app/services/llm.py  
# - Task 3: app/services/application_matcher.py
# - Task 4-5: app/routes/parse.py
# - Task 6: app/models/api/email.py
# - Task 7: app/services/error_handler.py
# - Task 8: app/tests/test_email_parsing.py

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Job Hub API is running"}

from app.routes.parse import router as parse_router
from app.routes.gmail import router as gmail_router
from app.routes.auth import router as auth_router

app.include_router(parse_router, prefix="/api")
app.include_router(gmail_router)
app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)