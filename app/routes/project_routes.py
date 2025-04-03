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
    project_data: ProjectCreateModel, # Use the specific create model
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project.
    """
    # Note: Cache invalidation for the list endpoint (page 0) would ideally happen here.
    # Relying on expiration for now.

    # Dump the model data for the service function
    project_dict = project_data.model_dump()
    created_project = await create_project(project_dict, db)

    # Trigger standard mapping after creation
    try:
        await map_project_standard(created_project.id, ProjectStandardListResponse, db)
    except HTTPException as e:
        # Log the error, but potentially allow project creation to succeed anyway?
        print(f"Standard mapping failed after creating project {created_project.id}: {e.detail}")
        # Decide if this should cause the POST to fail entirely
        # raise e # Re-raise if mapping failure should prevent success

    # Fetch the potentially updated project data (including standard_mapping)
    # This call might benefit from the get_project cache if called again soon.
    final_project = await get_project_by_id(created_project.id, db)
    if final_project is None:
         # Should not happen if creation succeeded, but good practice
         raise HTTPException(status_code=500, detail="Failed to retrieve created project.")

    return final_project


# --- Single Project Endpoints ---

@router.get("/{project_id}", response_model=ProjectResponseModel,dependencies=[Depends(ensure_cache_initialized)]) # Use ProjectResponseModel
@cache(expire=60) # Cache based on project_id
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific project by ID. Cached for 60 seconds.
    """
    project = await get_project_by_id(project_id, db)
    if project is None:
         raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponseModel,dependencies=[Depends(ensure_cache_initialized)]) # Use ProjectResponseModel
async def update_existing_project(
    project_id: int,
    project_update_data: ProjectUpdateModel, # Use the specific update model
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing project. Only provided fields will be updated.
    """
    # Note: Cache invalidation for this project_id and potentially list pages
    # would ideally happen here. Relying on expiration for now.

    # Get a dictionary with only the fields that were actually sent in the request
    update_data = project_update_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    updated_project = await update_project(project_id, update_data, db)

    if updated_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Consider manually clearing the cache for this project_id here:
    # from fastapi_cache import FastAPICache
    # await FastAPICache.clear(namespace="default", key=f"...") # Key construction needed

    return updated_project

@router.delete("/{project_id}", status_code=204,dependencies=[Depends(ensure_cache_initialized)])
async def remove_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a project.
    """
    # Note: Cache invalidation for this project_id and potentially list pages
    # would ideally happen here. Relying on expiration for now.

    deleted = await delete_project(project_id, db)
    if not deleted:
         raise HTTPException(status_code=404, detail="Project not found")

    # Consider manually clearing the cache for this project_id here

    return None # Return None for 204 No Content

# --- Project Standard Mapping Endpoint ---

@router.post("/{project_id}/map_standard", response_model=ProjectResponseModel,dependencies=[Depends(ensure_cache_initialized)]) # Return updated project
async def map_project_to_standard(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Map project to standards. Fetches the project, calls the mapping service,
    updates the project, and returns the updated project.
    """
    # Note: Cache invalidation for this project_id would ideally happen here.

    # Service function handles checking if project exists and updates it
    mapping_result = await map_project_standard(project_id, ProjectStandardListResponse, db)

    if mapping_result is None: # Indicates project was not found by the service
         raise HTTPException(status_code=404, detail="Project not found")

    # Fetch the updated project data to return
    # This call will benefit from the cache added to the get_project route
    updated_project = await get_project_by_id(project_id, db)
    if updated_project is None:
         # Should not happen if mapping succeeded, but good practice
         raise HTTPException(status_code=500, detail="Failed to retrieve project after mapping.")

    return updated_project
