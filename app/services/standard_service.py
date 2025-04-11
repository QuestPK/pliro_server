from datetime import datetime

from fastapi import UploadFile, HTTPException
import json
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List, Type, Coroutine

from sqlalchemy.orm import selectinload

from app.models.standard_model import Standard, Revision
from app.types.standard_types import StandardBase
from app.utils.file_storage import upload_file_to_do, delete_file_from_do, \
    generate_presigned_url  # Assuming these utilities exist
from app.utils.openai_utils import call_openai_structured

available_regions = [
    {
        'id': 'americas',
        'name': 'The Americas',
        'description': 'North and South America, Mexico, Brazil, and all islands falling under the jurisdiction of the US.'
    },
    {
        'id': 'eu',
        'name': 'Europe',
        'description': 'All countries in Europe, both those part of the European Union, and others who are not part. '
    },
    {
        'id': 'middleEast',
        'name': 'Middle East',
        'description': 'Bahrain, Qatar, Oman, and the Gulf Countries throughout the Gulf. Does not include Turkey.'
    },
    {
        'id': 'asia',
        'name': 'Asia',
        'description': 'All countries from southern India to Russia, including South East and East Asia.'
    }
]

available_countries = [
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar",
    "Kuwait",
    "Bahrain",
    "Oman",
    "Jordan",
    "Lebanon",
    "Iraq",
    "Yemen",
    "Brazil",
    "Argentina",
    "Chile",
    "Colombia",
    "Peru",
    "Venezuela",
    "Ecuador",
    "Uruguay",
    "Paraguay",
    "Bolivia",
    "Germany",
    "France",
    "Italy",
    "Spain",
    "Netherlands",
    "Belgium",
    "Poland",
    "Sweden",
    "Austria",
    "Denmark",
    "Finland",
    "Ireland",
    "Portugal",
    "Greece",
    "Czech Republic",
    "Romania",
    "Hungary",
    "Slovakia",
    "Luxembourg",
    "Slovenia",
    "Croatia",
    "Estonia",
    "Latvia",
    "Lithuania",
    "Malta",
    "Cyprus",
    "United Kingdom",
    "Switzerland",
    "Norway",
    "Iceland",
    "Ukraine",
    "Serbia",
    "Albania",
    "Montenegro",
    "North Macedonia",
    "China",
    "Japan",
    "South Korea",
    "Taiwan",
    "Hong Kong",
    "Macau",
    "Mongolia",
    "India",
    "Pakistan",
    "Bangladesh",
    "Sri Lanka",
    "Nepal",
    "Bhutan",
    "Maldives",
    "Singapore",
    "Malaysia",
    "Indonesia",
    "Thailand",
    "Vietnam",
    "Philippines",
    "Myanmar",
    "Cambodia",
    "Laos",
    "Brunei"
]


async def create_standard(data: Dict[str, Any], file: Optional[UploadFile] = None,
                          session: AsyncSession = None) -> Standard:
    # Make a copy of the data to avoid modifying the original
    filtered_data = {k: v for k, v in data.items() if v is not None}

    # Handle file upload if provided
    if file:
        file_path = await upload_file_to_do(file)
        filtered_data["file_path"] = file_path

    # Format dates properly
    if "effectiveDate" in filtered_data and isinstance(filtered_data["effectiveDate"], str):
        filtered_data["effectiveDate"] = datetime.strptime(filtered_data["effectiveDate"], "%Y-%m-%d").date()

    if "issueDate" in filtered_data and isinstance(filtered_data["issueDate"], str):
        filtered_data["issueDate"] = datetime.strptime(filtered_data["issueDate"], "%Y-%m-%d").date()

    # Extract revisions data before creating the standard
    revisions_data = filtered_data.pop('revisions', None)

    # Create new standard
    new_standard = Standard(**filtered_data)
    session.add(new_standard)
    await session.flush()  # Flush to get the ID without committing

    # Handle revisions if provided
    if revisions_data:
        # Import Revision model
        from app.models.standard_model import Revision  # Adjust import path as needed

        for revision_data in revisions_data:
            # Convert from Pydantic model to dict if needed
            if hasattr(revision_data, "model_dump"):
                revision_dict = revision_data.model_dump()
            else:
                revision_dict = revision_data

            # Create new revision
            new_revision = Revision(
                revision_number=revision_dict.get('revision_number'),
                revision_date=revision_dict.get('revision_date'),
                revision_description=revision_dict.get('revision_description'),
                standard_id=new_standard.id
            )
            session.add(new_revision)

    await session.commit()
    await session.refresh(new_standard)
    return new_standard

async def get_standard_by_id(standard_id: int, session: AsyncSession) -> Optional[Standard]:
    result = await session.execute(
        select(Standard)
        .options(selectinload(Standard.revisions))
        .filter(Standard.id == standard_id)
    )
    standard = result.scalar_one_or_none()

    if standard and standard.file_path:
        presigned_url = generate_presigned_url(str(standard.file_path))
        standard.presigned_url = presigned_url

    return standard


# Get all standards
async def get_all_standards(session: AsyncSession, skip: int = 0, limit: int = 100,
                            approval_status: Optional[str] = None) -> list[StandardBase]:
    query = select(Standard).options(selectinload(Standard.revisions))

    if approval_status:
        query = query.filter(Standard.approval_status == approval_status)

    result = await session.execute(
        query.offset(skip).limit(limit)
    )
    standards = result.scalars().all()

    for standard in standards:
        if standard.file_path:
            presigned_url = generate_presigned_url(str(standard.file_path))
            standard.file_path = presigned_url

    return [StandardBase.model_validate(item) for item in standards]


async def get_standards_count(session: AsyncSession, approval_status: Optional[str] = None) -> int:
    query = select(func.count(Standard.id))

    if approval_status:
        query = query.filter(Standard.approval_status == approval_status)

    result = await session.execute(query)
    return result.scalar_one()


async def update_standard_revisions(standard: Standard, revisions_data: List[Any], session: AsyncSession) -> None:
    # Import your Revision model
    from app.models.standard_model import Revision  # Adjust import path as needed

    # Create a lookup map of existing revisions
    existing_revisions = {rev.id: rev for rev in standard.revisions}
    new_revisions = []

    for revision_data in revisions_data:
        # Convert from Pydantic model to dict if needed
        if hasattr(revision_data, "model_dump"):
            revision_dict = revision_data.model_dump()
        else:
            revision_dict = revision_data

        revision_id = revision_dict.get('id')

        if revision_id and revision_id in existing_revisions:
            # Update existing revision
            revision = existing_revisions[revision_id]
            for k, v in revision_dict.items():
                if k != 'id' and hasattr(revision, k):
                    setattr(revision, k, v)
            new_revisions.append(revision)
        else:
            # Create new revision
            new_revision = Revision(
                revision_number=revision_dict.get('revision_number'),
                revision_date=revision_dict.get('revision_date'),
                revision_description=revision_dict.get('revision_description'),
                standard_id=standard.id
            )
            session.add(new_revision)
            new_revisions.append(new_revision)

    # Update the standard's revisions
    standard.revisions = new_revisions


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

    if "effectiveDate" in data and isinstance(data["effectiveDate"], str):
        data["effectiveDate"] = datetime.strptime(data["effectiveDate"], "%Y-%m-%d").date()

    if "issueDate" in data and isinstance(data["issueDate"], str):
        data["issueDate"] = datetime.strptime(data["issueDate"], "%Y-%m-%d").date()

    # Extract revisions data before updating other fields
    revisions_data = data.pop('revisions', None)

    # Update standard fields
    for key, value in data.items():
        if hasattr(standard, key):
            setattr(standard, key, value)

    # Handle revisions separately if provided
    if revisions_data is not None:
        await update_standard_revisions(standard, revisions_data, session)

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


def parse_date(date_str):
    try:
        # Try parsing the date in YYYY-MM-DD format
        return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
    except Exception as e:
        print(f'Error parsing date {date_str} {e}')
        return None


def add_standard_revisions(standard_data: Dict[str, Any]) -> Standard:
    revisions_data = standard_data.pop("revisions", [])
    new_standard = Standard(**standard_data)

    for revision in revisions_data:
        new_revision = Revision(**revision)
        new_standard.revisions.append(new_revision)

    return new_standard


async def upload_standard(file: UploadFile, session: AsyncSession, structured_response_model: Type):
    try:
        file_path = await upload_file_to_do(file)

        prompt = f'''
You will receive a Standard Name. Your task is to research and gather comprehensive information about this standard and then output a JSON object containing the fields listed below:

name: The official name of the standard.

description: A thorough description of the standard.

issuingOrganization: The organization that issues the standard.

standardNumber: The designated number or identifier of the standard.

version: The latest version of the standard.

standardOwner: The entity that owns the standard.

standardWebsite: The URL of the website providing more information about the standard.

issueDate: The issue date of the latest version (formatted as YYYY-MM-DD).

effectiveDate: The effective date of the latest version (formatted as YYYY-MM-DD).

revisions: An array with detailed information about each revision. Each revision should include:

revision_number: The revision number.

revision_date: The date of the revision (formatted as YYYY-MM-DD).

revision_description: A detailed explanation of the revision, including what changes were made, why they were implemented, and any additional relevant details.
Note: If there is more than one revision, include detailed information for all previous revisions.

generalCategories: The general categories under which the standard falls.

itCategories: The IT-specific categories associated with the standard.

additionalNotes: Any additional remarks or notes related to the standard.

For any fields where information is not available, use null as the value.

The name of the standard is provided below:

${file.filename}                    '''

        standard_data = call_openai_structured(prompt, structured_response_model)

        standard_data = json.loads(standard_data)

        standard_data["issueDate"] = parse_date(standard_data["issueDate"])
        standard_data["effectiveDate"] = parse_date(standard_data["effectiveDate"])

        standard_data["file_path"] = file_path
        standard_data["approval_status"] = "pending"

        new_standard = add_standard_revisions(standard_data)

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
You will receive a Standard Name. Your task is to research and gather comprehensive information about this standard and then output a JSON object containing the fields listed below:

name: The official name of the standard.

description: A thorough description of the standard.

issuingOrganization: The organization that issues the standard.

standardNumber: The designated number or identifier of the standard.

version: The latest version of the standard.

standardOwner: The entity that owns the standard.

standardWebsite: The URL of the website providing more information about the standard.

issueDate: The issue date of the latest version (formatted as YYYY-MM-DD).

effectiveDate: The effective date of the latest version (formatted as YYYY-MM-DD).

revisions: An array with detailed information about each revision. Each revision should include:

revision_number: The revision number.

revision_date: The date of the revision (formatted as YYYY-MM-DD).

revision_description: A detailed explanation of the revision, including what changes were made, why they were implemented, and any additional relevant details.
Note: If there is more than one revision, include detailed information for all previous revisions.

generalCategories: The general categories under which the standard falls.

itCategories: The IT-specific categories associated with the standard.

additionalNotes: Any additional remarks or notes related to the standard.

For any fields where information is not available, use null as the value.

Below are Available regions and countries:
{available_regions}
{available_countries}

The name of the standard is provided below:

{file.filename}
'''

            standard_data = call_openai_structured(prompt, structured_response_model)

            # Convert the structured response to a dictionary
            print('Standard Data', standard_data)

            standard_data = json.loads(standard_data)

            standard_data["issueDate"] = parse_date(standard_data["issueDate"])
            standard_data["effectiveDate"] = parse_date(standard_data["effectiveDate"])

            standard_data["file_path"] = file_path
            standard_data["approval_status"] = "pending"

            # Create standard with pending status
            new_standard = add_standard_revisions(standard_data)

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
            raise e
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
