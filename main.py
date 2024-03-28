from fastapi import FastAPI
from app.api.completion import router as completion_router
from app.api.usage import router as usage_router

app = FastAPI()
app.include_router(completion_router)
app.include_router(usage_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)