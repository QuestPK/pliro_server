from fastapi import HTTPException
import json

from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Type, Optional, List  # Added Optional

from app.models.project_model import ProjectModel
# Assuming StandardModel exists for get_all_standards
# from app.models.standard_model import StandardModel
from app.extensions import AsyncSessionLocal # Keep if used elsewhere, but get_db is preferred in routes
from app.services.standard_service import get_all_standards # Assuming this exists
from app.utils.openai_utils import call_openai_structured # Assuming this exists

# Note: Caching is generally applied at the route level for simplicity with fastapi-cache decorators.
# However, you *could* implement caching here manually or use a different caching library
# if you need finer-grained control within the service layer.

async def create_project(data: Dict[str, Any], session: AsyncSession) -> ProjectModel:
    """
    Create a new project.

    Args:
        data (dict): Project creation data, excluding None values.
        session (AsyncSession): Database session.

    Returns:
        ProjectModel: Created project object.
    """
    # Filter out None values to avoid overwriting defaults in the model
    filtered_data = {k: v for k, v in data.items() if v is not None}
    new_project = ProjectModel(**filtered_data)
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)
    return new_project


async def get_project_by_id(project_id: int, session: AsyncSession) -> Optional[ProjectModel]:
    """
    Retrieve a project by its ID.
    Note: This function is called by the cached `get_project` route.
          The caching happens at the route level.

    Args:
        project_id (int): ID of the project.
        session (AsyncSession): Database session.

    Returns:
        Optional[ProjectModel]: Project object or None if not found.
    """
    result = await session.get(ProjectModel, project_id)
    # Route handler will raise HTTPException if None is returned
    return result


async def get_all_projects(session: AsyncSession, skip: int = 0, limit: int = 10) -> List[ProjectModel]:
    """
    Retrieve a list of projects with pagination.
    Note: This function is called by the cached `list_projects` route.
          The caching happens at the route level, including skip/limit parameters.

    Args:
        session (AsyncSession): Database session.
        skip (int): Number of projects to skip.
        limit (int): Maximum number of projects to return.

    Returns:
        list[ProjectModel]: List of projects for the requested page.
    """
    result = await session.execute(
        select(ProjectModel)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_projects_count(session: AsyncSession) -> int:
    """
    Get the total count of projects.

    Args:
        session (AsyncSession): Database session.

    Returns:
        int: Total number of projects.
    """
    result = await session.execute(select(func.count(ProjectModel.id)))
    return result.scalar_one()




async def update_project(project_id: int, data: Dict[str, Any], session: AsyncSession) -> Optional[ProjectModel]:
    """
    Update an existing project with partial data.
    Only fields present in the 'data' dictionary will be updated.

    Args:
        project_id (int): ID of the project to update.
        data (dict): Dictionary containing only the fields to update.
                     Should be generated using model_dump(exclude_unset=True).
        session (AsyncSession): Database session.

    Returns:
        Optional[ProjectModel]: Updated project object or None if not found.
    """
    project = await get_project_by_id(project_id, session)
    if project is None:
        return None # Let the route handler raise HTTPException

    # Update only the fields provided in the data dictionary
    for key, value in data.items():
        if hasattr(project, key):
             setattr(project, key, value)
        # else: log a warning or ignore if extra fields are sent (e.g., fields not in ProjectModel)

    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(project_id: int, session: AsyncSession) -> bool:
    """
    Delete a project by its ID.

    Args:
        project_id (int): ID of the project to delete.
        session (AsyncSession): Database session.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    project = await get_project_by_id(project_id, session)
    if project is None:
        return False # Indicate not found

    await session.delete(project)
    await session.commit()
    return True


async def map_project_standard(project_id: int, structured_response_model: Type, session: AsyncSession) -> Optional[str]:

    project = await get_project_by_id(project_id, session)
    if project is None:
        # This case is handled in the route, but good practice to check here too
        return None

    all_standards = await get_all_standards(session) # Assuming this fetches from DB/another source
    modified_standards = [
        {"name": standard.name, "description": standard.description, "regions": standard.regions}
        for standard in all_standards
    ]

    # Ensure technical_details is a dictionary for the prompt
    tech_details_str = json.dumps(project.technical_details) if isinstance(project.technical_details, dict) else str(project.technical_details)

    prompt = f"""
       You are an expert standard mapper.You will be given a product that is about to be launched, and your task is to map the product to all appropriate standards based on the following:
        * Product details (general, technical, and regional)
        * Technical specifications
        * Known global standards (both from my provided repository and your own knowledge)
        Your priority is to:
        1. First, analyze and recommend standards from the provided repository.
        2. Then, you must go beyond and recommend additional standards from your own knowledge or external sources — this is mandatory, even if you feel the repo standards already cover the basics.
        3. Ensure each recommendation is well-reasoned, especially for external standards, and technically aligned with the product details.
        
        Product General Details:
        Product Name: {project.name}
        Product Type: {project.product_type}
        Product Category: {project.product_category}
        Intended Use: {project.use}
        Dimensions: {project.dimensions}
        Weight: {project.weight}
        Description: {project.description}
        Regions to launch: {project.regions}
        Countries to launch: {project.countries}
        Multiple Variants: {project.multi_variant}
        Uses Pre-certified Components: {project.pre_certified_components}
        
        Technical Details (Prioritize these for mappings):
        {tech_details_str}
        
        Standards Repository (for in_repo: true):
        {modified_standards}
        
        Output format (JSON):
            "mappings": [
                {{
                    "standard_name": "Standard Name",
                    "relevance_score": 0.9,
                    "technical_requirements_matched": ["Requirement 1", "Requirement 2"],
                    "reason_for_mapping": "Reason for mapping",
                    "in_repo": true
                }},
                {{
                    "standard_name": "External Standard Name",
                    "relevance_score": 0.85,
                    "technical_requirements_matched": ["Requirement A", "Requirement B"],
                    "reason_for_mapping": "Mapped based on external expertise and region-specific compliance needs.",
                    "in_repo": false
                }}
            ],
            "summary": "Summary of the overall mapping decisions.",
            "confidence_score": 0.9
        
        Important Notes:
        * Always recommend external standards (not in the repo) — this is mandatory.
        * For each standard, provide:
            * Relevance score (out of 1.0)
            * Matched technical requirements
            * Reason for inclusion (specific and technical)
        * For "in_repo":
            * true → if the standard comes from {modified_standards}
            * false → if it comes from your knowledge or external trusted sources
        * The summary should clearly explain:
            * Overall mapping approach
            * Priority standards
            * Regional compliance focus
        * Focus on technical accuracy and practical applicability.
    """

    # Call the external service (e.g., OpenAI)
    # Note: Caching this call might be complex due to the dynamic prompt content
    # and the side effect (updating the DB). Generally not cached unless the exact
    # same request needs to be repeated frequently without changes.
    try:
        result_json_str =  call_openai_structured(prompt, structured_response_model) # Expecting JSON string
        mapped_data = json.loads(result_json_str) # Parse the JSON string
    except Exception as e:
        # Handle potential errors from OpenAI call or JSON parsing
        print(f"Error during standard mapping or parsing OpenAI response: {e}")
        # Depending on requirements, you might raise an HTTPException or return an error indicator
        raise HTTPException(status_code=500, detail=f"Failed to map standards: {e}")


    # Update the project record with the mapping result
    project.standard_mapping = mapped_data # Store the parsed dictionary
    await session.commit()
    await session.refresh(project) # Refresh to get the updated state if needed elsewhere

    return result_json_str # Return the original JSON string result if needed by caller
