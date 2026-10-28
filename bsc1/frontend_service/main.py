from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Frontend Service")

# index.html, main.py ile aynı dizinde
templates = Jinja2Templates(directory=Path(__file__).resolve().parent)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy"}