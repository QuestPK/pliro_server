from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from app.extensions import get_db
from app.services.standard_service import (
    create_standard,
    get_standard_by_id,
    get_all_standards,
    update_standard,
    delete_standard
)

# Pydantic Model for Standard
class StandardModel(BaseModel):
    id: int | None = None
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)

# Create the router
router = APIRouter(
    tags=["standards"],
    responses={404: {"description": "Not found"}}
)

# Standard List and Creation Endpoint
@router.get("", response_model=List[StandardModel])
async def list_standards(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all standards
    """
    return await get_all_standards(db)

@router.post("", response_model=StandardModel, status_code=201)
async def create_new_standard(standard: StandardModel, db: AsyncSession = Depends(get_db)):
    """
    Create a new standard
    """
    return await create_standard(standard.model_dump(), db)

# Single Standard Endpoints
@router.get("/{standard_id}", response_model=StandardModel)
async def get_standard(standard_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific standard by ID
    """
    return await get_standard_by_id(standard_id, db)

@router.put("/{standard_id}", response_model=StandardModel)
async def update_existing_standard(
    standard_id: int,
    standard: StandardModel,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing standard
    """
    return await update_standard(standard_id, standard.model_dump(), db)

@router.delete("/{standard_id}", status_code=204)
async def remove_standard(standard_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a standard
    """
    await delete_standard(standard_id, db)
    return None
