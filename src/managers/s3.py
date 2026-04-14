"""
S3 Manager to do upload, download and delete of files and folders
"""

# pylint: disable=duplicate-code
# Reason: Connection retry logger script is the same across managers
# pylint: disable=import-error
# Reason: import has no problems in the container
import os
import time
from typing import Optional

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.exceptions import ConnectionError as BotoConnectionError
from botocore.exceptions import EndpointConnectionError

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)

logger = logging.getLogger("s3-manager")


class S3ConnectionError(Exception):
    """Raised when S3 connection fails."""


class S3OperationError(Exception):
    """Raised when an S3 operation fails."""


class S3Manager:
    """
    Utililty class to interact with Garage S3 Bucket

    :param bucket: S3 Bucket name
    :param endpoint_url: S3 Endpoint URL
    :param aws_access_key_id: AWS Access Key ID
    :param aws_secret_access_key: AWS Secret Access Key
    :param region_name: AWS Region Name
    """

    MAX_ATTEMPT = 5

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        max_retries: int = 5,
        retry_delay: int = 2,
    ):
        self.bucket = bucket
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        try:
            self.s3 = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                ),
            )
        except Exception as e:
            logger.error("Failed to initialize S3 client: %s", str(e))
            raise S3ConnectionError(f"Failed to initialize S3 client: {str(e)}") from e

    def ping(self) -> bool:
        """
        Performs a liveness check by pinging the S3 bucket.

        This method uses the S3 'HeadBucket' operation to verify that the
        bucket exists, the credentials have sufficient permissions, and
        the network connection to the S3 endpoint is active.

        :return: True if the bucket is accessible.
        :raises S3ConnectionError: If the service is unreachable or DNS fails.
        :raises S3OperationError: If the bucket does not exist or access is denied.
        """
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            logger.debug("S3 ping successful for bucket: %s", self.bucket)
            return True

        except (EndpointConnectionError, BotoConnectionError) as e:
            # Network/Infrastructure failure (e.g., S3 container is restarting)
            logger.error("S3 service unreachable during ping: %s", str(e))
            raise S3ConnectionError(f"Cannot reach S3 endpoint: {str(e)}") from e

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "404":
                logger.error("S3 ping failed: Bucket '%s' does not exist.", self.bucket)
                raise S3OperationError(f"Bucket '{self.bucket}' not found.") from e

            if error_code == "403":
                logger.error(
                    "S3 ping failed: Access Denied for bucket '%s'.", self.bucket
                )
                raise S3OperationError(
                    "S3 credentials lack permissions for HeadBucket."
                ) from e

            # Other S3 client errors
            logger.error("S3 client error during ping: %s", error_code)
            raise S3OperationError(f"S3 ping failed with error: {error_code}") from e

        except Exception as e:
            # Broad catch for unexpected system failures
            logger.critical(
                "Unexpected error during S3 ping: %s", str(e), exc_info=True
            )
            raise S3ConnectionError(f"Unexpected S3 liveness failure: {str(e)}") from e

    def _ensure_connection(self):
        """
        Verify the S3 endpoint is reachable.
        Retries every 5s until the service is back up.
        """
        retries = 0
        while retries < self.max_retries:
            try:
                self.ping()
                return
            except S3ConnectionError as e:
                retries += 1
                logger.warning(
                    "S3 Service unavailable. Attempt %d/%d. "
                    "Retrying in 5s... Error: %s",
                    retries,
                    self.max_retries,
                    str(e),
                )
                time.sleep(self.retry_delay)

        raise S3ConnectionError(
            f"S3 service unavailable after {self.max_retries} attempts."
        )

    def upload_file(
        self, file_path: str, object_name: str, content_type: Optional[str] = None
    ):
        """
        Upload a file to S3 bucket

        :param file_path: Path to the file to upload
        :param object_name: S3 object name
        :param content_type: Content type of the file (e.g., 'audio/wav')
        """

        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            # 1. Ensure the network/container is up
            self._ensure_connection()
            logger.info(
                "Uploading %s to s3://%s/%s", file_path, self.bucket, object_name
            )
            config = TransferConfig(
                multipart_threshold=1024 * 25,
                max_concurrency=10,
                multipart_chunksize=1024 * 25,
                use_threads=True,
            )
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3.upload_file(
                Filename=file_path,
                Bucket=self.bucket,
                Key=object_name,
                Config=config,
                ExtraArgs=extra_args,
            )

            logger.info(
                "Successfully uploaded %s to s3://%s/%s",
                file_path,
                self.bucket,
                object_name,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "NoSuchBucket":
                logger.error("Bucket does not exist: %s", self.bucket)
                raise S3OperationError(f"Bucket does not exist: {self.bucket}") from e
            if error_code == "AccessDenied":
                logger.error("Access denied for bucket: %s", self.bucket)
                raise S3OperationError(
                    f"Access denied. Check permissions for bucket: {self.bucket}"
                ) from e
            if error_code == "InvalidAccessKeyId":
                logger.error("Invalid AWS access key")
                raise S3OperationError("Invalid AWS access key") from e

            logger.error(
                "S3 client error during upload: %s - %s", error_code, error_message
            )
            raise S3OperationError(
                f"Failed to upload file: {error_code} - {error_message}"
            ) from e

        except EndpointConnectionError as e:
            logger.error("Cannot connect to S3 endpoint: %s", str(e))
            raise S3OperationError(f"Cannot connect to S3 endpoint: {str(e)}") from e

        except BotoConnectionError as e:
            logger.error("Connection error during upload: %s", str(e))
            raise S3OperationError(f"Connection error: {str(e)}") from e

        except BotoCoreError as e:
            logger.error("BotoCore error during upload: %s", str(e))
            raise S3OperationError(f"S3 operation failed: {str(e)}") from e

        except Exception as e:
            logger.error("Unexpected error during upload: %s", str(e))
            raise S3OperationError(f"Unexpected error during upload: {str(e)}") from e

    def download_file(self, s3_key: str, local_path: str):
        """
        Download a file from S3 bucket

        :param object_name: S3 object name
        :param file_path: Path to save the downloaded file
        """
        # Ensure directory exists
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            try:
                os.makedirs(local_dir, exist_ok=True)
                logger.info("Created directory: %s", local_dir)
            except OSError as e:
                logger.error("Failed to create directory %s: %s", local_dir, str(e))
                raise S3OperationError(
                    f"Failed to create directory {local_dir}: {str(e)}"
                ) from e
        try:
            # 1. Ensure the network/container is up
            self._ensure_connection()
            logger.info("Downloading s3://%s/%s to %s", self.bucket, s3_key, local_path)
            self.s3.download_file(
                Bucket=self.bucket,
                Key=s3_key,
                Filename=local_path,
            )
            logger.info("File downloaded successfully: %s", local_path)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code in ("404", "NoSuchKey"):
                logger.error("File not found in S3: %s", s3_key)
                raise S3OperationError(f"File not found in S3: {s3_key}") from e
            if error_code == "NoSuchBucket":
                logger.error("Bucket does not exist: %s", self.bucket)
                raise S3OperationError(f"Bucket does not exist: {self.bucket}") from e
            if error_code == "AccessDenied":
                logger.error("Access denied for file: %s", s3_key)
                raise S3OperationError(
                    f"Access denied. Check permissions for file: {s3_key}"
                ) from e

            logger.error(
                "S3 client error during download: %s - %s",
                error_code,
                error_message,
            )
            raise S3OperationError(
                f"Failed to download file: {error_code} - {error_message}"
            ) from e

        except EndpointConnectionError as e:
            logger.error("Cannot connect to S3 endpoint: %s", str(e))
            raise S3OperationError(f"Cannot connect to S3 endpoint: {str(e)}") from e

        except BotoConnectionError as e:
            logger.error("Connection error during download: %s", str(e))
            raise S3OperationError(f"Connection error: {str(e)}") from e

        except BotoCoreError as e:
            logger.error("BotoCore error during download: %s", str(e))
            raise S3OperationError(f"S3 operation failed: {str(e)}") from e

        except OSError as e:
            logger.error("File system error while saving file: %s", str(e))
            raise S3OperationError(f"Failed to save file locally: {str(e)}") from e

        except Exception as e:
            logger.error("Unexpected error during download: %s", str(e))
            raise S3OperationError(f"Unexpected error during download: {str(e)}") from e

    def delete_file(self, s3_key: str):
        """
        Deletes an object from the S3 bucket.

        Args:
            s3_key (str): The S3 object key to delete.

        Raises:
            S3OperationError: If the deletion fails due to permissions, connectivity,
                            or unexpected client errors.
        """
        try:
            self._ensure_connection()
            logger.info("Deleting s3://%s/%s", self.bucket, s3_key)
            # Note: delete_object is successful even if the key doesn't exist
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=s3_key,
            )
            logger.info("File deleted successfully from S3: %s", s3_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDenied":
                logger.error("Access denied for deleting file: %s", s3_key)
                raise S3OperationError(f"""Access denied.
                                    Check delete permissions for: {s3_key}""") from e
            logger.error(
                "S3 client error during deletion: %s - %s",
                error_code,
                error_message,
            )
            raise S3OperationError(
                f"Failed to delete file: {error_code} - {error_message}"
            ) from e

        except (EndpointConnectionError, BotoConnectionError) as e:
            logger.error("Network error connecting to S3 for deletion: %s", str(e))
            raise S3OperationError(f"Connection error: {str(e)}") from e

        except Exception as e:
            logger.error("Unexpected error during S3 deletion: %s", str(e))
            raise S3OperationError(f"Unexpected error during deletion: {str(e)}") from e

    def list_objects(self, prefix: str = ""):
        """
        Lists objects in the S3 bucket with an optional prefix.

        Args:
            prefix (str): Optional prefix to filter objects

        Returns:
            list: List of object keys
        """
        try:
            self._ensure_connection()
            logger.info("Listing objects in s3://%s with prefix '%s'", self.bucket, prefix)
            
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
                logger.info("Found %d objects in bucket %s", len(objects), self.bucket)
                return objects
            else:
                logger.info("No objects found in bucket %s with prefix '%s'", self.bucket, prefix)
                return []
                
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "NoSuchBucket":
                logger.error("Bucket does not exist: %s", self.bucket)
                raise S3OperationError(f"Bucket does not exist: {self.bucket}") from e
            if error_code == "AccessDenied":
                logger.error("Access denied for bucket: %s", self.bucket)
                raise S3OperationError(
                    f"Access denied. Check permissions for bucket: {self.bucket}"
                ) from e

            logger.error(
                "S3 client error during list_objects: %s - %s", error_code, error_message
            )
            raise S3OperationError(
                f"Failed to list objects: {error_code} - {error_message}"
            ) from e

        except (EndpointConnectionError, BotoConnectionError) as e:
            logger.error("Cannot connect to S3 endpoint: %s", str(e))
            raise S3OperationError(f"Cannot connect to S3 endpoint: {str(e)}") from e

        except Exception as e:
            logger.error("Unexpected error during S3 list_objects: %s", str(e))
            raise S3OperationError(f"Unexpected error during list_objects: {str(e)}") from e
