from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from src.routes import contacts, auth, users
from src.conf.config import config

app = FastAPI(
    title="Contacts API",
    description="API for managing contacts"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(users.router, prefix="/api")

@app.on_event("startup")
async def startup():
    redis_client = redis.Redis(
        host=config.REDIS_DOMAIN,
        port=config.REDIS_PORT,
        db=0,
        password=config.REDIS_PASSWORD
    )
    await FastAPILimiter.init(redis_client)



app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
