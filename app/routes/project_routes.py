import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query # Added Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field # Added Field
from fastapi_cache.decorator import cache

from app.extensions import get_db, ensure_cache_initialized
from app.services.project_service import (
    create_project,
    get_project_by_id,
    get_all_projects,
    get_projects_count, # Import count function
    update_project,
    delete_project,
    map_project_standard
)

# --- Pydantic Models ---

# Base Project Model (can be used for response)
class ProjectBase(BaseModel):
    name: str
    use: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    regions: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    technical_details: Optional[Dict[str, Any]] = None
    multi_variant: Optional[bool] = False # Default value
    pre_certified_components: Optional[bool] = False # Default value
    product_type: Optional[str] = None
    product_category: Optional[str] = None
    standard_mapping: Optional[Dict[str, Any]] = None

# Model for creating a project (inherits from Base, makes fields required as needed)
class ProjectCreateModel(ProjectBase):
    name: str # Make required fields explicit if they differ from Base
    use: str
    description: str
    product_type: str
    product_category: str
    user_id: int # Required for creation

# Model for updating a project (all fields optional)
class ProjectUpdateModel(BaseModel):
    name: Optional[str] = None
    use: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    regions: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    technical_details: Optional[Dict[str, Any]] = None
    multi_variant: Optional[bool] = None
    pre_certified_components: Optional[bool] = None
    product_type: Optional[str] = None
    product_category: Optional[str] = None
    # standard_mapping is usually updated via map_standard, not direct PUT
    # user_id should generally not be updatable

    model_config = ConfigDict(from_attributes=True) # Keep if needed, but often not for update models

# Model representing a full Project response (includes ID)
class ProjectResponseModel(ProjectBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

# Model for the paginated list response
class ProjectPage(BaseModel):
    items: List[ProjectResponseModel]
    total: int
    page: int
    size: int

# Standard Mapping Models (assuming these are correct)
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

# --- Router Setup ---
router = APIRouter(
    prefix="", # Add prefix here for consistency
    tags=["projects"],
    responses={404: {"description": "Not found"}}
)

# --- Project List and Creation Endpoint ---

# Apply caching to the endpoint that lists all projects.
# Cache expires after 60 seconds. Cache key includes skip and limit.
@router.get("", response_model=ProjectPage, dependencies=[Depends(ensure_cache_initialized)]) # Use the new paginated response model
@cache(expire=60) # Cache includes function arguments (skip, limit)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, alias="page", description="Page number (0-indexed)"), # Use alias for clarity
    limit: int = Query(10, ge=1, le=100, alias="pageSize", description="Number of items per page") # Use alias
):
    """
    Retrieve projects with pagination.
    Cached for 60 seconds based on page and pageSize.
    """
    page_number = skip # Keep original name for calculation if needed
    offset = page_number * limit

    total_projects = await get_projects_count(db)
    projects = await get_all_projects(db, skip=offset, limit=limit)

    return ProjectPage(
        items=projects,
        total=total_projects,
        page=page_number,
        size=limit
    )

@router.post("", response_model=ProjectResponseModel, status_code=201,dependencies=[Depends(ensure_cache_initialized)]) # Use ProjectResponseModel
async def create_new_project(
    project_data: ProjectCreateModel,
    db: AsyncSession = Depends(get_db)
):

    project_dict = project_data.model_dump()
    created_project = await create_project(project_dict, db)

    try:
        await map_project_standard(created_project.id, ProjectStandardListResponse, db)
    except HTTPException as e:
        print(f"Standard mapping failed after creating project {created_project.id}: {e.detail}")

    final_project = await get_project_by_id(created_project.id, db)
    if final_project is None:
         raise HTTPException(status_code=500, detail="Failed to retrieve created project.")

    return final_project



@router.get("/{project_id}", response_model=ProjectResponseModel,dependencies=[Depends(ensure_cache_initialized)]) # Use ProjectResponseModel
@cache(expire=60)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_id(project_id, db)
    if project is None:
         raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponseModel,dependencies=[Depends(ensure_cache_initialized)]) # Use ProjectResponseModel
async def update_existing_project(
    project_id: int,
    project_update_data: ProjectUpdateModel,
    db: AsyncSession = Depends(get_db)
):
    update_data = project_update_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    updated_project = await update_project(project_id, update_data, db)

    if updated_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return updated_project

@router.delete("/{project_id}", status_code=204,dependencies=[Depends(ensure_cache_initialized)])
async def remove_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a project.
    """

    deleted = await delete_project(project_id, db)
    if not deleted:
         raise HTTPException(status_code=404, detail="Project not found")


    return None


@router.post("/{project_id}/map_standard", response_model=ProjectResponseModel,dependencies=[Depends(ensure_cache_initialized)]) # Return updated project
async def map_project_to_standard(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    mapping_result = await map_project_standard(project_id, ProjectStandardListResponse, db)

    if mapping_result is None: # Indicates project was not found by the service
         raise HTTPException(status_code=404, detail="Project not found")

    updated_project = await get_project_by_id(project_id, db)
    if updated_project is None:
         raise HTTPException(status_code=500, detail="Failed to retrieve project after mapping.")

    return updated_project
