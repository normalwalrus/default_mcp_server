"""
S3 Tools for MCP Server
Provides tools to interact with S3/MinIO storage
"""

import os
import tempfile
import base64
from pathlib import Path
from typing import Optional

from managers.s3 import S3Manager


def get_s3_manager():
    """
    Create and return an S3Manager instance using environment variables
    """
    bucket = os.getenv("S3_BUCKET", "mcp-storage")
    endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    return S3Manager(
        bucket=bucket,
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )


def upload_file_to_s3(file_content: str, object_name: str, content_type: Optional[str] = None) -> str:
    """
    Upload a file to S3/MinIO
    
    Args:
        file_content: Base64 encoded file content or plain text
        object_name: Name of the object in S3
        content_type: Optional content type (e.g., 'image/jpeg', 'text/plain')
        
    Returns:
        Success message with object name
    """
    s3_manager = get_s3_manager()
    
    # Create a temporary file to upload
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name
    
    try:
        # Upload the file
        s3_manager.upload_file(temp_file_path, object_name, content_type)
        os.unlink(temp_file_path)  # Clean up temp file
        return f"Successfully uploaded {object_name} to S3 bucket {s3_manager.bucket}"
    except Exception as e:
        os.unlink(temp_file_path)  # Clean up temp file even if upload fails
        raise e


def upload_base64_image_to_s3(base64_image: str, object_name: str) -> str:
    """
    Upload a base64-encoded image to S3/MinIO
    
    Args:
        base64_image: Base64 encoded image string (with or without data URI prefix)
        object_name: Name of the object in S3 (should include extension)
        
    Returns:
        Success message with object name
    """
    s3_manager = get_s3_manager()
    
    # Handle potential data URI prefix
    if base64_image.startswith('data:'):
        # Extract the actual base64 content
        header, base64_content = base64_image.split(',', 1)
        # Determine content type from header
        content_type = header.split(';')[0].split(':')[1]
    else:
        base64_content = base64_image
        content_type = "image/jpeg"  # default
    
    # Decode the base64 content
    image_data = base64.b64decode(base64_content)
    
    # Create a temporary file to upload
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(image_data)
        temp_file_path = temp_file.name
    
    try:
        # Determine content type based on file extension if not provided
        if content_type == "image/jpeg" and (object_name.endswith('.png') or object_name.endswith('.gif')):
            content_type = f"image/{object_name.split('.')[-1]}"
        
        # Upload the file
        s3_manager.upload_file(temp_file_path, object_name, content_type)
        os.unlink(temp_file_path)  # Clean up temp file
        return f"Successfully uploaded image {object_name} to S3 bucket {s3_manager.bucket}"
    except Exception as e:
        os.unlink(temp_file_path)  # Clean up temp file even if upload fails
        raise e


def download_file_from_s3(object_name: str) -> str:
    """
    Download a file from S3/MinIO
    
    Args:
        object_name: Name of the object in S3
        
    Returns:
        Content of the downloaded file as string
    """
    s3_manager = get_s3_manager()
    
    # Create a temporary file to download to
    with tempfile.NamedTemporaryFile(mode='r+', delete=False) as temp_file:
        temp_file_path = temp_file.name
    
    try:
        # Download the file
        s3_manager.download_file(object_name, temp_file_path)
        
        # Read the content
        with open(temp_file_path, 'r') as f:
            content = f.read()
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return content
    except Exception as e:
        # Clean up temp file even if download fails
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise e


def download_image_from_s3_as_base64(object_name: str) -> str:
    """
    Download an image from S3/MinIO and return as base64 string
    
    Args:
        object_name: Name of the image object in S3
        
    Returns:
        Base64 encoded image string
    """
    s3_manager = get_s3_manager()
    
    # Create a temporary file to download to
    with tempfile.NamedTemporaryFile(mode='rb', delete=False) as temp_file:
        temp_file_path = temp_file.name
    
    try:
        # Download the file
        s3_manager.download_file(object_name, temp_file_path)
        
        # Read the binary content and encode as base64
        with open(temp_file_path, 'rb') as f:
            image_data = f.read()
        
        base64_string = base64.b64encode(image_data).decode('utf-8')
        
        # Determine the file extension to set proper content type
        ext = Path(object_name).suffix.lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return f"data:{mime_type};base64,{base64_string}"
    except Exception as e:
        # Clean up temp file even if download fails
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise e


def delete_file_from_s3(object_name: str) -> str:
    """
    Delete a file from S3/MinIO
    
    Args:
        object_name: Name of the object in S3 to delete
        
    Returns:
        Success message
    """
    s3_manager = get_s3_manager()
    
    try:
        s3_manager.delete_file(object_name)
        return f"Successfully deleted {object_name} from S3 bucket {s3_manager.bucket}"
    except Exception as e:
        raise e


def list_s3_objects(prefix: Optional[str] = "") -> list[str]:
    """
    List objects in the S3 bucket with an optional prefix
    
    Args:
        prefix: Optional prefix to filter objects
        
    Returns:
        List of object names
    """
    s3_manager = get_s3_manager()
    
    try:
        objects = s3_manager.list_objects(prefix)
        return objects
    except Exception as e:
        raise e