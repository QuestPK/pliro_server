from datetime import datetime

from fastapi import UploadFile, HTTPException
import json
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List, Type

from app.models.standard_model import Standard
from app.utils.file_storage import upload_file_to_do, delete_file_from_do  # Assuming these utilities exist
from app.utils.openai_utils import call_openai_structured


async def create_standard(data: Dict[str, Any], file: Optional[UploadFile] = None,
                          session: AsyncSession = None) -> Standard:
    filtered_data = {k: v for k, v in data.items() if v is not None}

    # Handle file upload if provided
    if file:
        file_path = await upload_file_to_do(file)
        filtered_data["file_path"] = file_path

    new_standard = Standard(**filtered_data)
    session.add(new_standard)
    await session.commit()
    await session.refresh(new_standard)
    return new_standard


async def get_standard_by_id(standard_id: int, session: AsyncSession) -> Optional[Standard]:
    result = await session.get(Standard, standard_id)
    return result


async def get_all_standards(session: AsyncSession, skip: int = 0, limit: int = 100,
                            approval_status: Optional[str] = None) -> List[Standard]:
    query = select(Standard)

    if approval_status:
        query = query.filter(Standard.approval_status == approval_status)

    result = await session.execute(
        query.offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_standards_count(session: AsyncSession, approval_status: Optional[str] = None) -> int:
    query = select(func.count(Standard.id))

    if approval_status:
        query = query.filter(Standard.approval_status == approval_status)

    result = await session.execute(query)
    return result.scalar_one()


async def update_standard(standard_id: int, data: Dict[str, Any], file: Optional[UploadFile] = None,
                          session: AsyncSession = None) -> Optional[Standard]:
    standard = await get_standard_by_id(standard_id, session)
    if standard is None:
        return None

    # Handle file upload if a new file is provided
    if file:
        # Delete old file if it exists
        if standard.file_path:
            await delete_file_from_do(standard.file_path)

        # Upload new file
        file_path = await upload_file_to_do(file)
        data["file_path"] = file_path

    for key, value in data.items():
        if hasattr(standard, key):
            setattr(standard, key, value)

    await session.commit()
    await session.refresh(standard)
    return standard


async def delete_standard(standard_id: int, session: AsyncSession) -> bool:
    standard = await get_standard_by_id(standard_id, session)
    if standard is None:
        return False

    # Delete associated file if it exists
    if standard.file_path:
        try:
            await delete_file_from_do(standard.file_path)
        except Exception as e:
            # Log error but continue with deletion
            print(f"Error deleting file {standard.file_path}: {e}")

    await session.delete(standard)
    await session.commit()
    return True


async def upload_standard(file: UploadFile, session: AsyncSession, structured_response_model: Type):
    try:
        file_path = await upload_file_to_do(file)

        prompt = f'''
                        You will be provided with a Standard Name, and you will have to find certain information regarding that standard and fill out the details below and return the JSON object.
                        The Date for standard should be from the latest version available. If you don't have information of some fields return null for those fields.
                        Below are the necessary fields to be returned:

                        name,
                        description,
                        issuingOrganization,
                        standardNumber,
                        version,
                        standardOwner,
                        standardWebsite,
                        issueDate ( Should be a date in format YYYY-MM-DD ),
                        effectiveDate ( Should be a date in format YYYY-MM-DD ),
                        revisions,
                        generalCategories,
                        itCategories,
                        additionalNotes

                        below is the name of Standard 

                        ${file.filename}

                    '''

        standard_data = call_openai_structured(prompt, structured_response_model)

        print('Structured Data Testing Err', standard_data)
        standard_data = json.loads(standard_data)

        # Parse date fields safely
        def parse_date(date_str):
            try:
                # Try parsing the date in YYYY-MM-DD format
                return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
            except Exception as e:
                print(f'Error parsing date {date_str} {e}')
                return None

        standard_data["issueDate"] = parse_date(standard_data["issueDate"])
        standard_data["effectiveDate"] = parse_date(standard_data["effectiveDate"])

        standard_data["file_path"] = file_path
        standard_data["approval_status"] = "pending"

        new_standard = Standard(**standard_data)

        session.add(new_standard)

        await session.commit()
        await session.refresh(new_standard)


    except Exception as e:
        print('Upload Standard Error', e)
        raise HTTPException(status_code=400, detail="No file provided")

    return new_standard


async def bulk_upload_standards(files: List[UploadFile], session: AsyncSession, structured_response_model: Type) -> \
List[Dict[str, Any]]:
    """
    Process multiple standard files for bulk upload

    Args:
        files (List[UploadFile]): List of PDF files to process
        session (AsyncSession): Database session

    Returns:
        List[Dict[str, Any]]: List of extracted standard data with pending approval status
        :param files:
        :param session:
        :param structured_response_model:
    """
    results = []

    for file in files:
        try:
            # Upload file to DigitalOcean
            file_path = await upload_file_to_do(file)

            # Extract standard info from PDF
            # standard_data = await extract_standard_info_from_pdf(file)

            prompt = f'''
                You will be provided with a Standard Name, and you will have to find certain information regarding that standard and fill out the details below and return the JSON object.
                Below are the necessary fields to be returned:
                
                name,
                description,
                issuingOrganization,
                standardNumber,
                version,
                standardOwner,
                standardWebsite,
                issueDate,
                effectiveDate,
                revisions,
                generalCategories,
                itCategories,
                additionalNotes
                
                below is the name of Standard 
                
                ${file.filename}
                
            '''

            standard_data = call_openai_structured(prompt, structured_response_model)

            mapped_data = json.loads(standard_data)  # Parse the JSON string

            # Add file path and set approval status to pending
            standard_data["file_path"] = file_path
            standard_data["approval_status"] = "pending"

            # Create standard with pending status
            new_standard = Standard(**standard_data)
            session.add(new_standard)
            await session.commit()
            await session.refresh(new_standard)

            # Add to results
            results.append({
                "id": new_standard.id,
                "file_name": file.filename,
                "extracted_data": standard_data,
                "status": "success"
            })

        except Exception as e:
            # Add failed result
            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": str(e)
            })

    return results


async def approve_standard(standard_id: int, session: AsyncSession) -> Optional[Standard]:
    """
    Approve a pending standard

    Args:
        standard_id (int): ID of the standard to approve
        session (AsyncSession): Database session

    Returns:
        Optional[Standard]: Updated standard or None if not found
    """
    standard = await get_standard_by_id(standard_id, session)
    if standard is None:
        return None

    standard.approval_status = "approved"
    await session.commit()
    await session.refresh(standard)
    return standard


async def reject_standard(standard_id: int, session: AsyncSession) -> bool:
    """
    Reject and delete a pending standard

    Args:
        standard_id (int): ID of the standard to reject
        session (AsyncSession): Database session

    Returns:
        bool: True if successfully rejected and deleted
    """
    return await delete_standard(standard_id, session)
