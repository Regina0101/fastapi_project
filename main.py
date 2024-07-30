from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import contacts, auth

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

@app.get("/")
def index():
    return {"message": "Contacts Application"}
