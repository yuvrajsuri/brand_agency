"""
Cloudflare R2 Storage Service
Handles image uploads to R2 bucket with local fallback
"""

import boto3
from botocore.config import Config
from pathlib import Path
import os
from typing import Optional
import logging
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class R2Storage:
    """Cloudflare R2 storage client for image uploads with local fallback"""
    
    def __init__(self):
        # Load R2 credentials from environment (support both naming conventions)
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME") or os.getenv("R2_BUCKET", "brand-agency-creatives")
        self.endpoint_url = os.getenv("R2_ENDPOINT")
        self.public_domain = os.getenv("R2_PUBLIC_DOMAIN")
        
        # Extract account ID from endpoint if possible
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        if not self.account_id and self.endpoint_url:
            try:
                # Format: https://<account_id>.r2.cloudflarestorage.com
                if ".r2.cloudflarestorage.com" in self.endpoint_url:
                    self.account_id = self.endpoint_url.split("://")[1].split(".")[0]
            except Exception:
                pass
        
        # Determine if R2 is usable
        self.use_r2 = False
        self.client = None
        
        if self.access_key_id and self.secret_access_key and (self.endpoint_url or self.account_id):
            try:
                # Construct endpoint if not provided
                if not self.endpoint_url:
                    self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
                
                # Initialize R2 client
                self.client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    config=Config(signature_version='s3v4'),
                    region_name='auto'
                )
                self.use_r2 = True
                logger.info(f"R2 storage initialized: bucket={self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize R2 client: {str(e)}")
        
        if not self.use_r2:
            logger.warning("R2 credentials not fully configured - using local storage fallback")
            
        # Setup local storage path for fallback
        # Stored in static/overlays to be served publicly
        self.local_storage_dir = Path(__file__).parent.parent / "static" / "overlays"
        self.local_storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_image(self, file_path: Path, folder: str = "overlays") -> str:
        """
        Upload image to R2 bucket or fallback to local storage
        
        Args:
            file_path: Local path to image file
            folder: Folder structure in R2
        
        Returns:
            Public URL of uploaded image
        """
        
        if self.use_r2 and self.client:
            try:
                return await self._upload_to_r2(file_path, folder)
            except Exception as e:
                logger.error(f"R2 upload failed, falling back to local: {str(e)}")
                return await self._upload_local(file_path)
        else:
            return await self._upload_local(file_path)
            
    async def _upload_to_r2(self, file_path: Path, folder: str) -> str:
        """Internal method to upload to R2"""
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{os.urandom(4).hex()}{file_path.suffix}"
        
        # S3 key (path in bucket)
        s3_key = f"{folder}/{filename}"
        
        # Upload file
        with open(file_path, 'rb') as f:
            self.client.upload_fileobj(
                f,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/png',
                    'CacheControl': 'public, max-age=31536000',  # 1 year cache
                }
            )
        
        # Generate public URL
        if self.public_domain:
            public_url = f"https://{self.public_domain}/{s3_key}"
        elif self.account_id:
            # Use R2.dev URL if account ID is available
            public_url = f"https://{self.bucket_name}.{self.account_id}.r2.dev/{s3_key}"
        else:
            # Last resort
            public_url = f"{self.endpoint_url}/{self.bucket_name}/{s3_key}"
            
        logger.info(f"Image uploaded to R2: {public_url}")
        return public_url
        
    async def _upload_local(self, file_path: Path) -> str:
        """Internal method to save locally (fallback)"""
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{os.urandom(4).hex()}{file_path.suffix}"
        
        target_path = self.local_storage_dir / filename
        
        # Copy file
        shutil.copy2(file_path, target_path)
        
        # Return relative URL (served via /static mount)
        public_url = f"/static/overlays/{filename}"
        logger.info(f"Image saved locally (fallback): {target_path}")
        
        return public_url
    
    def delete_image(self, s3_key: str) -> bool:
        """Delete image from R2 bucket"""
        
        if not self.use_r2 or not self.client:
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Image deleted from R2: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from R2: {str(e)}")
            return False
    
    def list_images(self, prefix: str = "", max_keys: int = 100) -> list:
        """List images in R2 bucket with given prefix"""
        
        if not self.use_r2 or not self.client:
            return []
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            logger.error(f"Failed to list R2 objects: {str(e)}")
            return []

