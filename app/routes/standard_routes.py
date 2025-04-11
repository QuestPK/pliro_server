import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache.decorator import cache

from app.extensions import get_db, ensure_cache_initialized
from app.services.standard_service import (
    create_standard,
    get_standard_by_id,
    get_all_standards,
    get_standards_count,
    update_standard,
    delete_standard,
    bulk_upload_standards,
    approve_standard,
    reject_standard, upload_standard
)
from app.types.standard_types import StandardPage, StandardResponseModel, StandardCreateModel, StandardUpdateModel, \
    BulkUploadResponse, OpenAIStandardModel, RevisionBase
from app.utils.cache_utils import (
    invalidate_standards_list_cache,
    invalidate_standard_detail_cache
)

router = APIRouter(
    prefix="",
    tags=["standards"],
    responses={404: {"description": "Not found"}}
)


async def parse_standard_form_data(
        name: str = Form(None),
        description: str = Form(None),
        issuingOrganization: str = Form(None),
        standardNumber: str = Form(None),
        version: str = Form(None),
        standardOwner: str = Form(None),
        effectiveDate: str = Form(None),
        issueDate: str = Form(None),
        standardWebsite: str = Form(None),
        generalCategories: str = Form(None),
        itCategories: str = Form(None),
        additionalNotes: str = Form(None),
        selectRegions: str = Form(None),
        selectCountries: str = Form(None),
        revisions: str = Form(None),
) -> Dict[str, Any]:
    raw_data = {
        "name": name,
        "description": description,
        "issuingOrganization": issuingOrganization,
        "standardNumber": standardNumber,
        "version": version,
        "standardOwner": standardOwner,
        "effectiveDate": effectiveDate,
        "issueDate": issueDate,
        "standardWebsite": standardWebsite,
        "generalCategories": generalCategories,
        "itCategories": itCategories,
        "additionalNotes": additionalNotes,
        "regions": selectRegions,
        "countries": selectCountries,
        "revisions": revisions,
    }

    data = {}
    for key, value in raw_data.items():
        if value is not None:
            if key == "revisions":
                try:
                    revisions_data = json.loads(value)
                    # Process each revision to ensure it has the required fields and correct types
                    processed_revisions = []
                    for rev in revisions_data:
                        # Add id if missing
                        if 'id' not in rev:
                            rev['id'] = None  # Use None for new revisions

                        # Ensure revision_number is a string
                        if 'revision_number' in rev and not isinstance(rev['revision_number'], str):
                            rev['revision_number'] = str(rev['revision_number'])

                        processed_revisions.append(rev)

                    # Create a list of RevisionBase objects with the processed data
                    data[key] = [RevisionBase(**rev) for rev in processed_revisions]
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON in field: {key}")
            elif key in {"generalCategories", "itCategories", "regions", "countries"}:
                try:
                    data[key] = json.loads(value)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON in field: {key}")
            else:
                data[key] = value

    return data


@router.get("", response_model=StandardPage, dependencies=[Depends(ensure_cache_initialized)])
@cache(expire=60)
async def list_standards(
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0, alias="page", description="Page number (0-indexed)"),
        limit: int = Query(100, ge=1, le=500, alias="pageSize", description="Number of items per page"),
        approval_status: Optional[str] = Query(None, description="Filter by approval status (pending, approved)")
):
    page_number = skip
    offset = page_number * limit

    total_standards = await get_standards_count(db, approval_status)
    standards = await get_all_standards(db, skip=offset, limit=limit, approval_status=approval_status)

    return StandardPage(
        items=standards,
        total=total_standards,
        page=page_number,
        size=limit
    )


@router.post("", response_model=StandardResponseModel, status_code=201,
             dependencies=[Depends(ensure_cache_initialized)])
async def create_new_standard(
        file: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_db),
        form_data: Dict[str, Any] = Depends(parse_standard_form_data)
):
    if not form_data and file is None:
        raise HTTPException(status_code=400, detail="No data provided")

    standard_create_data = StandardCreateModel(**form_data)
    standard_dict = standard_create_data.model_dump()

    created_standard = await create_standard(standard_dict, file, db)

    # Invalidate list cache after creating a new standard
    await invalidate_standards_list_cache()

    return created_standard


@router.get("/{standard_id}", response_model=StandardResponseModel, dependencies=[Depends(ensure_cache_initialized)])
@cache(expire=60)
async def get_standard(standard_id: int, db: AsyncSession = Depends(get_db)):
    standard = await get_standard_by_id(standard_id, db)
    if standard is None:
        raise HTTPException(status_code=404, detail="Standard not found")
    return standard


@router.put("/{standard_id}", response_model=StandardResponseModel, dependencies=[Depends(ensure_cache_initialized)])
async def update_existing_standard(
        standard_id: int,
        file: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_db),
        form_data: Dict[str, Any] = Depends(parse_standard_form_data)
):
    if not form_data and file is None:
        raise HTTPException(status_code=400, detail="No update data provided")

    standard_update_data = StandardUpdateModel(**form_data)
    update_data = standard_update_data.model_dump(exclude_unset=True)

    print('update standard,',standard_id, 'Update data',update_data)

    updated_standard = await update_standard(standard_id, update_data, file, db)

    if updated_standard is None:
        raise HTTPException(status_code=404, detail="Standard not found")

    await invalidate_standards_list_cache()
    await invalidate_standard_detail_cache(standard_id)

    return updated_standard


@router.delete("/{standard_id}", status_code=204, dependencies=[Depends(ensure_cache_initialized)])
async def remove_standard(standard_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_standard(standard_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Standard not found")

    # Invalidate both the list cache and this specific standard's detail cache
    await invalidate_standards_list_cache()
    await invalidate_standard_detail_cache(standard_id)

    return None


@router.post("/bulk-upload", response_model=BulkUploadResponse, status_code=201)
async def bulk_upload_standard_files(
        files: List[UploadFile] = File(...),
        db: AsyncSession = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = await bulk_upload_standards(files, db, OpenAIStandardModel)

    # Invalidate standards list cache after bulk upload
    await invalidate_standards_list_cache()

    successful = sum(1 for result in results if result.get("status") == "success")
    failed = len(results) - successful

    return BulkUploadResponse(
        total_processed=len(results),
        successful=successful,
        failed=failed,
        results=results
    )


@router.post("/bulk-delete", status_code=204)
async def bulk_delete_standard_files(
        standard_ids: List[int] = Form(...),
        db: AsyncSession = Depends(get_db)
):
    if not standard_ids:
        raise HTTPException(status_code=400, detail="No standard IDs provided")

    for standard_id in standard_ids:
        deleted = await delete_standard(standard_id, db)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Standard with ID {standard_id} not found")

        # Invalidate the detail cache for each deleted standard
        await invalidate_standard_detail_cache(standard_id)

    # Invalidate standards list cache after bulk delete
    await invalidate_standards_list_cache()

    return None


@router.post("/upload", response_model=StandardResponseModel, status_code=201)
async def upload_standard_file(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    created_standard = await upload_standard(file, db, OpenAIStandardModel)

    # Invalidate standards list cache after upload
    await invalidate_standards_list_cache()

    return created_standard


@router.post("/{standard_id}/approve", response_model=StandardResponseModel)
async def approve_pending_standard(
        standard_id: int,
        db: AsyncSession = Depends(get_db)
):
    standard = await approve_standard(standard_id, db)
    if standard is None:
        raise HTTPException(status_code=404, detail="Standard not found")

    # Invalidate both the list cache and this specific standard's detail cache
    await invalidate_standards_list_cache()
    await invalidate_standard_detail_cache(standard_id)

    return standard


@router.post("/bulk-approve", status_code=204)
async def bulk_approve_standards(
        standard_ids: List[int] = Form(...),
        db: AsyncSession = Depends(get_db)
):
    if not standard_ids:
        raise HTTPException(status_code=400, detail="No standard IDs provided")

    for standard_id in standard_ids:
        approved_standard = await approve_standard(standard_id, db)
        if approved_standard is None:
            raise HTTPException(status_code=404, detail=f"Standard with ID {standard_id} not found")

        # Invalidate the detail cache for each approved standard
        await invalidate_standard_detail_cache(standard_id)

    # Invalidate standards list cache after bulk approve
    await invalidate_standards_list_cache()

    return None


@router.post("/{standard_id}/reject", status_code=204)
async def reject_pending_standard(
        standard_id: int,
        db: AsyncSession = Depends(get_db)
):
    rejected = await reject_standard(standard_id, db)
    if not rejected:
        raise HTTPException(status_code=404, detail="Standard not found")

    # Invalidate both the list cache and this specific standard's detail cache
    await invalidate_standards_list_cache()
    await invalidate_standard_detail_cache(standard_id)

    return None