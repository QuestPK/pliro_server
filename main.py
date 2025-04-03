import os

import uvicorn
from starlette.responses import FileResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routes import project_routes, user_routes, standard_routes
from app.extensions import create_database_if_not_exists, async_engine, init_redis
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown events.
    """
    # Startup events

    try:
        await create_database_if_not_exists(async_engine)
    except Exception as e:
        print(f"Failed to Database: {e}")

    try:
        await init_redis()
        print("Redis and rate limiting initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Redis: {e}")

    yield

    # Shutdown events (if any)
    # Add any cleanup logic here


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pliro API",
        version="1.0",
        description="API Documentation",
        lifespan=lifespan  # Use the new lifespan context manager
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
    allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(project_routes.router, prefix="/api/projects")
    # Uncomment when ready
    app.include_router(user_routes.router, prefix="/api/users")
    app.include_router(standard_routes.router, prefix="/api/standards")

    return app


app = create_app()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dist", StaticFiles(directory="dist"), name="dist")



@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = os.path.join("dist", full_path)  # Construct file path

    # If the requested file exists in `dist`, serve it
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    # Otherwise, serve `index.html` (for SPA routes like `/dashboard`)
    return FileResponse(os.path.join("dist", "index.html"))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )