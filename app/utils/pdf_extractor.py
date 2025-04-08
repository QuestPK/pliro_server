import io
import PyPDF2
import re
from typing import Dict, Any, List
from fastapi import UploadFile
import datetime

async def extract_standard_info_from_pdf(file: UploadFile) -> Dict[str, Any]:
    """
    Extract standard information from a PDF file

    Args:
        file (UploadFile): The PDF file to process

    Returns:
        Dict[str, Any]: Extracted standard information
    """
    # Read the file content
    content = await file.read()
    pdf_file = io.BytesIO(content)

    # Reset file pointer for potential future use
    await file.seek(0)

    # Create a PDF reader object
    pdf_reader = PyPDF2.PdfReader(pdf_file)

    # Extract text from all pages
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()

    # Now extract information using pattern matching
    # These patterns should be refined based on the actual PDF format of standards
    name_match = re.search(r"Standard Name[:\s]+([^\n]+)", text, re.IGNORECASE)
    description_match = re.search(r"Description[:\s]+([^\n]+)", text, re.IGNORECASE)
    organization_match = re.search(r"Issuing Organization[:\s]+([^\n]+)", text, re.IGNORECASE)
    number_match = re.search(r"Standard Number[:\s]+([^\n]+)", text, re.IGNORECASE)
    version_match = re.search(r"Version[:\s]+([^\n]+)", text, re.IGNORECASE)
    owner_match = re.search(r"Standard Owner[:\s]+([^\n]+)", text, re.IGNORECASE)
    website_match = re.search(r"Website[:\s]+([^\n]+)", text, re.IGNORECASE)
    date_match = re.search(r"Issue Date[:\s]+([^\n]+)", text, re.IGNORECASE)
    effective_match = re.search(r"Effective Date[:\s]+([^\n]+)", text, re.IGNORECASE)

    # Extract categories using a more complex pattern
    # This example looks for a list following "General Categories:" until the next heading
    categories_text = re.search(r"General Categories[:\s]+(.*?)(?=\n\s*[A-Z][a-z]+\s*:)", text,
                                re.DOTALL | re.IGNORECASE)
    it_categories_text = re.search(r"IT Categories[:\s]+(.*?)(?=\n\s*[A-Z][a-z]+\s*:)", text, re.DOTALL | re.IGNORECASE)

    # Extract revisions
    revisions_text = re.search(r"Revisions[:\s]+(.*?)(?=\n\s*[A-Z][a-z]+\s*:)", text, re.DOTALL | re.IGNORECASE)

    # Parse date if found, otherwise use current date
    try:
        if date_match:
            issue_date = datetime.datetime.strptime(date_match.group(1).strip(), "%Y-%m-%d").date()
        else:
            issue_date = datetime.date.today()
    except ValueError:
        # If date format is incorrect, use today's date
        issue_date = datetime.date.today()

    # Process categories and revisions
    general_categories = []
    if categories_text:
        # Split by commas or new lines and clean up
        general_categories = [cat.strip() for cat in re.split(r',|\n', categories_text.group(1)) if cat.strip()]

    it_categories = []
    if it_categories_text:
        it_categories = [cat.strip() for cat in re.split(r',|\n', it_categories_text.group(1)) if cat.strip()]

    revisions = []
    if revisions_text:
        revisions = [rev.strip() for rev in re.split(r',|\n', revisions_text.group(1)) if rev.strip()]

    # Compile extracted data, with defaults for missing information
    standard_data = {
        "name": name_match.group(1).strip() if name_match else file.filename,
        "description": description_match.group(1).strip() if description_match else "No description extracted",
        "issuingOrganization": organization_match.group(1).strip() if organization_match else "Unknown",
        "standardNumber": number_match.group(1).strip() if number_match else "Unknown",
        "version": version_match.group(1).strip() if version_match else "1.0",
        "standardOwner": owner_match.group(1).strip() if owner_match else "Unknown",
        "standardWebsite": website_match.group(1).strip() if website_match else "https://example.com",
        "issueDate": issue_date,
        "effectiveDate": effective_match.group(1).strip() if effective_match else "Immediate",
        "revisions": revisions if revisions else ["Initial version"],
        "generalCategories": general_categories if general_categories else ["Uncategorized"],
        "itCategories": it_categories if it_categories else ["General"],
        "additionalNotes": f"Automatically extracted from {file.filename}",
        "approval_status": "pending"
    }

    return standard_data

