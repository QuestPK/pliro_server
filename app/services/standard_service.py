from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.standard_model import Standard

async def create_standard(data: dict, session: AsyncSession):
    """
    Create a new standard

    Args:
        data (dict): Standard creation data
        session (AsyncSession): Database session

    Returns:
        Standard: Created standard object
    """
    new_standard = Standard(**data)
    session.add(new_standard)
    await session.commit()
    await session.refresh(new_standard)
    return new_standard

async def get_standard_by_id(standard_id: int, session: AsyncSession):
    """
    Retrieve a standard by its ID

    Args:
        standard_id (int): ID of the standard
        session (AsyncSession): Database session

    Returns:
        Standard: Standard object

    Raises:
        HTTPException: If standard is not found
    """
    result = await session.get(Standard, standard_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Standard not found")
    return result

async def get_all_standards(session: AsyncSession):
    """
    Retrieve all standards

    Args:
        session (AsyncSession): Database session

    Returns:
        list: List of all standards
    """
    result = await session.execute(select(Standard))
    return result.scalars().all()

async def update_standard(standard_id: int, data: dict, session: AsyncSession):
    """
    Update an existing standard

    Args:
        standard_id (int): ID of the standard to update
        data (dict): Update data
        session (AsyncSession): Database session

    Returns:
        Standard: Updated standard object
    """
    standard = await get_standard_by_id(standard_id, session)
    for key, value in data.items():
        setattr(standard, key, value)
    await session.commit()
    await session.refresh(standard)
    return standard

async def delete_standard(standard_id: int, session: AsyncSession):
    """
    Delete a standard by its ID

    Args:
        standard_id (int): ID of the standard to delete
        session (AsyncSession): Database session
    """
    standard = await get_standard_by_id(standard_id, session)
    await session.delete(standard)
    await session.commit()
