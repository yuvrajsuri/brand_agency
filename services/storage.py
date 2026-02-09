"""
Cloudflare R2 Storage Service
Handles image uploads to R2 bucket
"""

import boto3
from botocore.config import Config
from pathlib import Path
import os
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class R2Storage:
    """Cloudflare R2 storage client for image uploads"""
    
    def __init__(self):
        # Load R2 credentials from environment
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "brand-agency-creatives")
        self.public_domain = os.getenv("R2_PUBLIC_DOMAIN")  # Custom domain or R2.dev URL
        
        # Validate credentials - if not all present, use local storage
        if not all([self.account_id, self.access_key_id, self.secret_access_key]) or \
           self.account_id == "your_account_id_here":
            logger.warning("R2 credentials not configured - using local storage")
            self.client = None
            
            # Use environment variable for local storage, default to Docker-friendly path or Downloads
            default_path = Path("/app/data/posters") if os.getenv("DOCKER_ENV") else Path.home() / "Downloads" / "brandbot-posters"
            self.local_storage_dir = Path(os.getenv("LOCAL_STORAGE_DIR", default_path))
            self.local_storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage directory: {self.local_storage_dir}")
            return
        
        # Initialize R2 client (S3-compatible)
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        
        logger.info(f"R2 storage initialized: bucket={self.bucket_name}")
    
    async def upload_image(self, file_path: Path, folder: str = "overlays") -> str:
        """
        Upload image to R2 bucket or save locally
        
        Args:
            file_path: Local path to image file
            folder: Folder structure in R2 (e.g., "overlays", "campaigns/diwali")
        
        Returns:
            Public URL of uploaded image or local file path
        """
        
        if not self.client:
            # Local storage: copy to static/generated folder for HTTP serving
            import shutil
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = file_path.suffix
            filename = f"{timestamp}_{os.urandom(4).hex()}{file_ext}"
            
            # Save to static/generated folder so it can be served via HTTP
            static_dir = Path(__file__).parent.parent / "static" / "generated"
            static_dir.mkdir(parents=True, exist_ok=True)
            
            destination = static_dir / filename
            shutil.copy2(file_path, destination)
            
            # Also save to Downloads for user's reference
            downloads_dir = self.local_storage_dir / filename
            shutil.copy2(file_path, downloads_dir)
            
            logger.info(f"Image saved locally: {destination}")
            logger.info(f"Also saved to Downloads: {downloads_dir}")
            
            # Return HTTP URL that browser can access
            return f"/static/generated/{filename}"
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = file_path.suffix
            filename = f"{timestamp}_{os.urandom(4).hex()}{file_ext}"
            
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
            else:
                # Use default R2.dev URL
                public_url = f"https://{self.bucket_name}.{self.account_id}.r2.dev/{s3_key}"
            
            logger.info(f"Image uploaded to R2: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload to R2: {str(e)}", exc_info=True)
            raise
    
    def delete_image(self, s3_key: str) -> bool:
        """Delete image from R2 bucket"""
        
        if not self.client:
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
        
        if not self.client:
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