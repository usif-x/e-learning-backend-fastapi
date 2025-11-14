# app/utils/file_upload.py

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024  # 20MB


class FileUploadService:
    """Service to handle file uploads with UUID naming and storage management."""

    def __init__(self, base_storage_path: str = "storage"):
        """
        Initialize the file upload service.

        Args:
            base_storage_path: Base directory for file storage (relative to project root)
        """
        self.base_storage_path = Path(base_storage_path)
        self._ensure_storage_directories()

    def _ensure_storage_directories(self):
        """Create storage directories if they don't exist."""
        directories = [
            self.base_storage_path / "courses",
            self.base_storage_path / "categories",
            self.base_storage_path / "users",
            self.base_storage_path / "lectures",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return Path(filename).suffix.lower()

    def _validate_image(self, file: UploadFile) -> None:
        """
        Validate uploaded image file.

        Args:
            file: The uploaded file

        Raises:
            HTTPException: If file is invalid
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        extension = self._get_file_extension(file.filename)
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
            )

    def _validate_audio(self, file: UploadFile) -> None:
        """
        Validate uploaded audio file.

        Args:
            file: The uploaded file

        Raises:
            HTTPException: If file is invalid
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        extension = self._get_file_extension(file.filename)
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio file type. Allowed types: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
            )

    def _validate_media(self, file: UploadFile, media_type: str) -> None:
        """
        Validate uploaded media file (image or audio).

        Args:
            file: The uploaded file
            media_type: Type of media ('image' or 'audio')

        Raises:
            HTTPException: If file is invalid
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        extension = self._get_file_extension(file.filename)

        if media_type == "image":
            if extension not in ALLOWED_IMAGE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
                )
        elif media_type == "audio":
            if extension not in ALLOWED_AUDIO_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid audio file type. Allowed types: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid media type. Must be 'image' or 'audio'",
            )

    async def save_image(
        self, file: UploadFile, folder: str = "courses"
    ) -> tuple[str, str]:
        """
        Save an uploaded image with UUID naming.

        Args:
            file: The uploaded file
            folder: Subfolder within storage (e.g., 'courses', 'categories')

        Returns:
            Tuple of (uuid_filename, relative_path)

        Raises:
            HTTPException: If file validation fails or save fails
        """
        # Validate the image
        self._validate_image(file)

        # Read file content
        try:
            contents = await file.read()
            file_size = len(contents)

            # Check file size
            if file_size > MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum allowed size of {MAX_IMAGE_SIZE / (1024*1024)}MB",
                )

            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file uploaded")

        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        finally:
            await file.seek(0)  # Reset file pointer

        # Generate UUID filename
        extension = self._get_file_extension(file.filename)
        uuid_filename = f"{uuid.uuid4()}{extension}"

        # Construct full path
        folder_path = self.base_storage_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        file_path = folder_path / uuid_filename

        # Save file
        try:
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

        # Return the UUID filename and relative path for database storage
        relative_path = f"{folder}/{uuid_filename}"
        return uuid_filename, relative_path

    async def save_media(
        self, file: UploadFile, media_type: str, folder: str = "posts"
    ) -> tuple[str, str]:
        """
        Save an uploaded media file (image or audio) with UUID naming.

        Args:
            file: The uploaded file
            media_type: Type of media ('image' or 'audio')
            folder: Subfolder within storage (e.g., 'posts', 'communities')

        Returns:
            Tuple of (uuid_filename, relative_path)

        Raises:
            HTTPException: If file validation fails or save fails
        """
        # Validate the media file
        self._validate_media(file, media_type)

        # Read file content
        try:
            contents = await file.read()
            file_size = len(contents)

            # Check file size based on media type
            max_size = MAX_AUDIO_SIZE if media_type == "audio" else MAX_IMAGE_SIZE
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds maximum allowed size of {max_size / (1024*1024)}MB",
                )

            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file uploaded")

        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        finally:
            await file.seek(0)  # Reset file pointer

        # Generate UUID filename
        extension = self._get_file_extension(file.filename)
        uuid_filename = f"{uuid.uuid4()}{extension}"

        # Construct full path
        folder_path = self.base_storage_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        file_path = folder_path / uuid_filename

        # Save file
        try:
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

        # Return the UUID filename and relative path for database storage
        relative_path = f"{folder}/{uuid_filename}"
        return uuid_filename, relative_path

    def delete_image(self, relative_path: str) -> bool:
        """
        Delete an image file.

        Args:
            relative_path: Relative path to the file (e.g., 'courses/uuid.jpg')

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = self.base_storage_path / relative_path
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    def get_absolute_path(self, relative_path: str) -> Optional[Path]:
        """
        Get absolute path for a stored file.

        Args:
            relative_path: Relative path to the file

        Returns:
            Absolute Path object or None if file doesn't exist
        """
        file_path = self.base_storage_path / relative_path
        return file_path if file_path.exists() else None


# Create a singleton instance
file_upload_service = FileUploadService()
