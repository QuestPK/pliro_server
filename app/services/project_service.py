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
    """
    Map project to standards using an external service and update the project.

    Args:
        project_id (int): ID of the project.
        structured_response_model (Type): Pydantic model for the expected OpenAI response structure.
        session (AsyncSession): Database session.

    Returns:
        Optional[str]: JSON string of the mapped standards result from OpenAI, or None if project not found.
                       The project record is updated directly in the database.
    """
    project = await get_project_by_id(project_id, session)
    if project is None:
        # This case is handled in the route, but good practice to check here too
        return None

    # --- Potential Caching Opportunity ---
    # If get_all_standards is slow and standards don't change often,
    # consider caching its result using fastapi-cache or manual Redis caching.
    # Example (conceptual - requires standard_service setup):
    # @cache(expire=3600) # Cache for 1 hour
    # async def get_cached_all_standards(session: AsyncSession):
    #     return await get_all_standards(session)
    # all_standards = await get_cached_all_standards(session)
    # -------------------------------------
    all_standards = await get_all_standards(session) # Assuming this fetches from DB/another source

    # Ensure technical_details is a dictionary for the prompt
    tech_details_str = json.dumps(project.technical_details) if isinstance(project.technical_details, dict) else str(project.technical_details)

    prompt = f"""
        You are an expert standard mapper. You would be a given a product that is about to be launched and
        you would be required to map the product to the appropriate standards according to region and counties.

        Below are the product general details:
        Product Name: {project.name}
        Product Type: {project.product_type}
        Product Category: {project.product_category}
        Intended Use of Product: {project.use}
        Dimensions of Product: {project.dimensions}
        Weight of Product: {project.weight}
        Product Description: {project.description}
        Product Regions to launch product: {project.regions}
        Product Countries to launch product: {project.countries}
        Product has multiple variants: {project.multi_variant}
        Product uses pre-certified components: {project.pre_certified_components}

        Below are the Technical Details of the product, Standards are to be applied on basis of Technical Details:
        Technical Details: {tech_details_str}

        Please map the product to the appropriate standards according to region and countries and Specially Technical Details.

You have to return in form of json with the following structure:
        {{
            "mappings": [
                {{
                    "standard_name": "Standard Name",
                    "relevance_score": 0.9,
                    "technical_requirements_matched": ["Requirement 1", "Requirement 2"],
                    "reason_for_mapping": "Reason for mapping",
                    "in_repo": true
                }}
            ],
            "summary": "Summary of the mapping",
            "confidence_score": 0.9
        }}
        
        You can match other standards from your knowledge as well. But should have solid reason for mapping. But priority would be to analyze given standards map given standards then look for other standards.
        in_repo would be true if the standards is from the below provided standards list, if standard is from your knowledge then it would be false.

        Below are the standards available:
        {all_standards}
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
