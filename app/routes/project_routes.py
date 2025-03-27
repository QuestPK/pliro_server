import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from app.extensions import get_db
from app.services.project_service import (
    create_project,
    get_project_by_id,
    get_all_projects,
    update_project,
    delete_project,
    map_project_standard
)

# Pydantic Model for Project
class ProjectModel(BaseModel):
    id: int | None = None
    name: str
    use: str | None = None
    description: str | None = None
    dimensions: str | None = None
    weight: str | None = None
    regions: List[str] | None = None
    countries: List[str] | None = None
    technical_details: Dict[str, Any] | None = None
    multi_variant: bool | None = None
    pre_certified_components: bool | None = None
    user_id: int | None = None
    product_type: str | None = None
    product_category: str | None = None

    model_config = ConfigDict(from_attributes=True)

# Standard Mapping Models
class StandardMapping(BaseModel):
    standard_name: str
    relevance_score: float
    technical_requirements_matched: List[str]
    reason_for_mapping: str
    in_repo: bool

class ProjectStandardListResponse(BaseModel):
    mappings: List[StandardMapping]
    summary: str
    confidence_score: float

# Create the router
router = APIRouter(
    tags=["projects"],
    responses={404: {"description": "Not found"}}
)

# Project List and Creation Endpoint
@router.get("", response_model=List[ProjectModel])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all projects
    """
    return await get_all_projects(db)

@router.post("", response_model=ProjectModel, status_code=201)
async def create_new_project(project: ProjectModel, db: AsyncSession = Depends(get_db)):
    """
    Create a new project
    """
    return await create_project(project.model_dump(), db)

# Single Project Endpoints
@router.get("/{project_id}", response_model=ProjectModel)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific project by ID
    """
    return await get_project_by_id(project_id, db)

@router.put("/{project_id}", response_model=ProjectModel)
async def update_existing_project(
    project_id: int,
    project: ProjectModel,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing project
    """
    return await update_project(project_id, project.model_dump(), db)

@router.delete("/{project_id}", status_code=204)
async def remove_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a project
    """
    await delete_project(project_id, db)
    return None

# Project Standard Mapping Endpoint
@router.post("/{project_id}/map_standard", response_model=Dict[str, Any])
async def map_project_to_standard(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Map project to standards
    """

    result = await map_project_standard(project_id, ProjectStandardListResponse, db)

    print("Resutl on Map Standard", result)

    if isinstance(result, str):  # Ensure it's not a JSON string
        result = json.loads(result)

    return result