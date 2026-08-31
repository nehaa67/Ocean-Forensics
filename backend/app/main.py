from fastapi import FastAPI

from backend.app.routes import router as api_router


app = FastAPI(
    title="Ocean Forensics API",
    description="AI-assisted marine oil spill investigation system",
    version="0.1.0",
)


app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get("/")
def root():
    return {
        "service": "Ocean Forensics",
        "status": "running",
        "version": "0.1.0",
    }