import os
import uuid
from typing import Optional
from fastapi import UploadFile
import aiohttp
import boto3
from botocore.exceptions import ClientError

# Configure DigitalOcean Spaces (S3-compatible)
SPACE_NAME = os.getenv("DO_SPACE_NAME", "standards-storage")
SPACE_REGION = os.getenv("DO_SPACE_REGION", "nyc3")
SPACE_ENDPOINT = os.getenv("DO_SPACE_ENDPOINT", "https://nyc3.digitaloceanspaces.com")
ACCESS_KEY = os.getenv("DO_ACCESS_KEY")
SECRET_KEY = os.getenv("DO_SECRET_KEY")

# Initialize S3 client for DigitalOcean Spaces
s3_client = boto3.client(
    's3',
    region_name=SPACE_REGION,
    endpoint_url=SPACE_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


async def upload_file_to_do(file: UploadFile) -> str:

    # Generate a unique file name
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    # Set the object path in the bucket
    object_path = f"standards/{unique_filename}"

    # Read file content
    file_content = await file.read()

    # Upload file to DigitalOcean Space
    try:
        s3_client.put_object(
            Bucket=SPACE_NAME,
            Key=object_path,
            Body=file_content,
            ACL='private',  # Use 'public-read' if you want the files to be publicly accessible
            ContentType=file.content_type
        )

        # Reset file pointer for potential future use
        await file.seek(0)

        # Return the path/URL to the file
        return f"{SPACE_ENDPOINT}/{SPACE_NAME}/{object_path}"

    except ClientError as e:
        # Handle error and raise an appropriate exception
        print('Digital Ocean Error',e)
        raise Exception(f"Failed to upload file to DigitalOcean: {str(e)}")


async def delete_file_from_do(file_path: str) -> bool:
    """
    Delete a file from DigitalOcean Spaces

    Args:
        file_path (str): The full path/URL of the file to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Extract the object key from the full URL
        # Format: https://region.digitaloceanspaces.com/bucket-name/object-key
        parts = file_path.split(f"{SPACE_ENDPOINT}/{SPACE_NAME}/")
        if len(parts) != 2:
            raise ValueError(f"Invalid file path format: {file_path}")

        object_key = parts[1]

        # Delete the object
        s3_client.delete_object(
            Bucket=SPACE_NAME,
            Key=object_key
        )

        return True

    except Exception as e:
        # Log the error and return False
        print(f"Error deleting file {file_path}: {str(e)}")
        return False


async def get_file_from_do(file_path: str) -> Optional[bytes]:
    """
    Retrieve a file from DigitalOcean Spaces

    Args:
        file_path (str): The full path/URL of the file to retrieve

    Returns:
        Optional[bytes]: The file content as bytes, or None if not found
    """
    try:
        # Extract the object key from the full URL
        parts = file_path.split(f"{SPACE_ENDPOINT}/{SPACE_NAME}/")
        if len(parts) != 2:
            raise ValueError(f"Invalid file path format: {file_path}")

        object_key = parts[1]

        # Get the object
        response = s3_client.get_object(
            Bucket=SPACE_NAME,
            Key=object_key
        )

        return response['Body'].read()

    except Exception as e:
        # Log the error and return None
        print(f"Error retrieving file {file_path}: {str(e)}")
        return None