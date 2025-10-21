from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")  # type: ignore[misc]
def healthz() -> dict[str, str]:
    return {"status": "ok"}
