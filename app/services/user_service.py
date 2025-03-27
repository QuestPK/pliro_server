from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_model import User

async def create_user(data: dict, session: AsyncSession):
    """
    Create a new user

    Args:
        data (dict): User creation data
        session (AsyncSession): Database session

    Returns:
        User: Created user object
    """
    new_user = User(**data)
    new_user.set_password(data["password"])
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

async def get_user_by_id(user_id: int, session: AsyncSession):
    """
    Retrieve a user by ID

    Args:
        user_id (int): ID of the user
        session (AsyncSession): Database session

    Returns:
        User: User object

    Raises:
        HTTPException: If user is not found
    """
    result = await session.get(User, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result

async def get_all_users(session: AsyncSession):
    """
    Retrieve all users

    Args:
        session (AsyncSession): Database session

    Returns:
        list: List of all users
    """
    result = await session.execute(select(User))
    return result.scalars().all()

async def update_user(user_id: int, data: dict, session: AsyncSession):
    """
    Update an existing user

    Args:
        user_id (int): ID of the user to update
        data (dict): Update data
        session (AsyncSession): Database session

    Returns:
        User: Updated user object
    """
    user = await get_user_by_id(user_id, session)
    for key, value in data.items():
        if key == "password":
            user.set_password(value)
        else:
            setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user

async def delete_user(user_id: int, session: AsyncSession):
    """
    Delete a user by ID

    Args:
        user_id (int): ID of the user to delete
        session (AsyncSession): Database session
    """
    user = await get_user_by_id(user_id, session)
    await session.delete(user)
    await session.commit()
