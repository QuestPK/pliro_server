from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field
from fastapi_cache.decorator import cache
from datetime import date

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


class StandardBase(BaseModel):
    name: str
    description: Optional[str]
    issuingOrganization: Optional[str]
    standardNumber: Optional[str]
    version: Optional[str]
    standardOwner: Optional[str]
    standardWebsite: Optional[str]
    issueDate: Optional[date]
    effectiveDate: Optional[date]
    revisions: List[str]
    generalCategories: List[str]
    itCategories: List[str]
    additionalNotes: Optional[str] = None

class OpenAIStandardModel(BaseModel):
    name: str
    description: Optional[str]
    issuingOrganization: Optional[str]
    standardNumber: Optional[str]
    version: Optional[str]
    standardOwner: Optional[str]
    standardWebsite: Optional[str]
    issueDate: Optional[str]
    effectiveDate: Optional[str]
    revisions: List[str]
    generalCategories: List[str]
    itCategories: List[str]
    additionalNotes: Optional[str] = None


class StandardCreateModel(StandardBase):
    pass


class StandardUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    issuingOrganization: Optional[str] = None
    standardNumber: Optional[str] = None
    version: Optional[str] = None
    standardOwner: Optional[str] = None
    standardWebsite: Optional[str] = None
    issueDate: Optional[date] = None
    effectiveDate: Optional[str] = None
    revisions: Optional[List[str]] = None
    generalCategories: Optional[List[str]] = None
    itCategories: Optional[List[str]] = None
    additionalNotes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StandardResponseModel(StandardBase):
    id: int
    file_path: Optional[str] = None
    approval_status: str

    model_config = ConfigDict(from_attributes=True)


class StandardPage(BaseModel):
    items: List[StandardResponseModel]
    total: int
    page: int
    size: int


class BulkUploadResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


router = APIRouter(
    prefix="",
    tags=["standards"],
    responses={404: {"description": "Not found"}}
)


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
        standard_data: StandardCreateModel = Depends(),
        file: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_db)
):
    standard_dict = standard_data.model_dump()
    created_standard = await create_standard(standard_dict, file, db)
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
        standard_update_data: StandardUpdateModel,
        file: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_db)
):
    update_data = standard_update_data.model_dump(exclude_unset=True)

    if not update_data and file is None:
        raise HTTPException(status_code=400, detail="No update data provided")

    updated_standard = await update_standard(standard_id, update_data, file, db)

    if updated_standard is None:
        raise HTTPException(status_code=404, detail="Standard not found")

    return updated_standard


@router.delete("/{standard_id}", status_code=204, dependencies=[Depends(ensure_cache_initialized)])
async def remove_standard(standard_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_standard(standard_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Standard not found")

    return None


@router.post("/bulk-upload", response_model=BulkUploadResponse, status_code=201)
async def bulk_upload_standard_files(
        files: List[UploadFile] = File(...),
        db: AsyncSession = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = await bulk_upload_standards(files, db, StandardBase)

    successful = sum(1 for result in results if result.get("status") == "success")
    failed = len(results) - successful

    return BulkUploadResponse(
        total_processed=len(results),
        successful=successful,
        failed=failed,
        results=results
    )

@router.post("/upload", response_model=StandardResponseModel, status_code=201)
async def upload_standard_file(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    created_standard = await upload_standard(file, db, OpenAIStandardModel)
    return created_standard

@router.post("/{standard_id}/approve", response_model=StandardResponseModel)
async def approve_pending_standard(
        standard_id: int,
        db: AsyncSession = Depends(get_db)
):
    standard = await approve_standard(standard_id, db)
    if standard is None:
        raise HTTPException(status_code=404, detail="Standard not found")
    return standard


@router.post("/{standard_id}/reject", status_code=204)
async def reject_pending_standard(
        standard_id: int,
        db: AsyncSession = Depends(get_db)
):
    rejected = await reject_standard(standard_id, db)
    if not rejected:
        raise HTTPException(status_code=404, detail="Standard not found")
    return None