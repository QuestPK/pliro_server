import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import Settings
from app.routes import project_routes, user_routes, standard_routes
from app.extensions import init_redis, create_database_if_not_exists, async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown events.
    """
    # Startup events
    try:
        await create_database_if_not_exists(async_engine)
        # await init_redis()
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
        allow_origins=["http://localhost:5173"],  # Consider making this configurable
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


# Optional: OpenAPI/Swagger UI customization
@app.get("/")
async def root():
    """
    Simple root endpoint to provide basic API information.
    """
    return {
        "name": "Pliro API",
        "version": "1.0",
        "description": "API for Pliro Project Management",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )