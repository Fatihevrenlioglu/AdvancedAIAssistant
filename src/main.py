from fastapi import FastAPI

app = FastAPI(title="AdvancedAIAssistant")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
