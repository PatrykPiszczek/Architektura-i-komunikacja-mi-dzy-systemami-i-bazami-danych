from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .errors import add_error_handlers
from .routers import auth, budgets, categories, expenses, rates, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SpendSync API",
    version="1.0.0",
    description="REST API for an offline-first personal expense tracker.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_error_handlers(app)

for module in (auth, categories, expenses, budgets, sync, rates):
    app.include_router(module.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
