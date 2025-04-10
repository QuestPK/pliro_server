from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field
from datetime import date


class RevisionBase(BaseModel):
    id: int
    revision_number: str
    revision_date: str
    revision_description: str

    model_config = {
        "from_attributes": True
    }

class   StandardBase(BaseModel):
    id: int
    name: str
    description: Optional[str]
    issuingOrganization: Optional[str]
    standardNumber: Optional[str]
    version: Optional[str]
    standardOwner: Optional[str]
    standardWebsite: Optional[str]
    issueDate: Optional[date]
    effectiveDate: Optional[date]
    revisions: List[RevisionBase]
    generalCategories: List[str]
    itCategories: List[str]
    additionalNotes: Optional[str] = None
    regions: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    file_path: Optional[str] = None
    approval_status: Optional[str] = "approved"

    model_config = {
        "from_attributes": True
    }

class OpenAIRevisionModel(BaseModel):
    revision_number: str
    revision_date: str
    revision_description: str

    model_config = {
        "from_attributes": True
    }


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
    revisions: List[OpenAIRevisionModel]
    generalCategories: List[str]
    itCategories: List[str]
    additionalNotes: Optional[str] = None
    regions: Optional[List[str]] = None
    countries: Optional[List[str]] = None


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
    regions: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    file_path: Optional[str] = None
    approval_status: Optional[str] = None


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

