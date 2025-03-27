from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, ConfigDict

from app.extensions import get_db
from app.services.user_service import (
    create_user,
    get_user_by_id,
    get_all_users,
    update_user,
    delete_user
)

# Pydantic Model for User
class UserModel(BaseModel):
    id: int | None = None
    name: str
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)

# Create the router
router = APIRouter(
    tags=["users"],
    responses={404: {"description": "Not found"}}
)

# User List and Creation Endpoint
@router.get("", response_model=List[UserModel])
async def list_users(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all users
    """
    return await get_all_users(db)

@router.post("", response_model=UserModel, status_code=201)
async def create_new_user(user: UserModel, db: AsyncSession = Depends(get_db)):
    """
    Create a new user
    """
    return await create_user(user.model_dump(), db)

# Single User Endpoints
@router.get("/{user_id}", response_model=UserModel)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific user by ID
    """
    return await get_user_by_id(user_id, db)

@router.put("/{user_id}", response_model=UserModel)
async def update_existing_user(
    user_id: int,
    user: UserModel,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing user
    """
    return await update_user(user_id, user.model_dump(), db)

@router.delete("/{user_id}", status_code=204)
async def remove_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a user
    """
    await delete_user(user_id, db)
    return None
