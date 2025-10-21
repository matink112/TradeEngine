from fastapi import FastAPI

from src.api import router as api_router

app = FastAPI(title="Trade Engine", version="0.1.0")
app.include_router(api_router)


# Simple health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
