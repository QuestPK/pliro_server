from fastapi import HTTPException
from pydantic import BaseModel

from app.models.project_model import ProjectModel
from app.extensions import AsyncSessionLocal
from app.services.standard_service import get_all_standards
from app.utils.openai_utils import call_openai_structured
from sqlalchemy.future import select
from typing import Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession


async def create_project(data: Dict[str, Any], session: AsyncSession):
    """
    Create a new project

    Args:
        data (dict): Project creation data
        session (AsyncSession): Database session

    Returns:
        ProjectModel: Created project object
    """
    new_project = ProjectModel(**data)
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)
    return new_project


async def get_project_by_id(project_id: int, session: AsyncSession):
    """
    Retrieve a project by its ID

    Args:
        project_id (int): ID of the project
        session (AsyncSession): Database session

    Returns:
        ProjectModel: Project object

    Raises:
        HTTPException: If project is not found
    """
    result = await session.get(ProjectModel, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


async def get_all_projects(session: AsyncSession):
    """
    Retrieve all projects

    Args:
        session (AsyncSession): Database session

    Returns:
        list: List of all projects
    """
    result = await session.execute(select(ProjectModel))
    return result.scalars().all()


async def update_project(project_id: int, data: Dict[str, Any], session: AsyncSession):
    """
    Update an existing project

    Args:
        project_id (int): ID of the project to update
        data (dict): Update data
        session (AsyncSession): Database session

    Returns:
        ProjectModel: Updated project object
    """
    project = await get_project_by_id(project_id, session)
    for key, value in data.items():
        setattr(project, key, value)
    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(project_id: int, session: AsyncSession):
    """
    Delete a project by its ID

    Args:
        project_id (int): ID of the project to delete
        session (AsyncSession): Database session
    """
    project = await get_project_by_id(project_id, session)
    await session.delete(project)
    await session.commit()


async def map_project_standard(project_id: int, structured_response, session: AsyncSession):
    """
    Map project to standards

    Args:
        project_id (int): ID of the project
        structured_response (dict): Structured response for standard mapping
        session (AsyncSession): Database session

    Returns:
        dict: Mapped standards
    """
    project = await get_project_by_id(project_id, session)
    all_standards = await get_all_standards(session)

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
        Technical Details: {project.technical_details}

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

    result = call_openai_structured(prompt, structured_response)
    return result