"""
Video management API endpoints with device compatibility support.
Provides enhanced video operations including device filtering and sync data management.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.models.video import EnhancedVideo, DeviceCapability, EffectComplexity, SyncData
from app.services.video_service import VideoService
from app.services.device_service import DeviceService
from app.config.settings import Settings

# Pydantic models for request/response
class VideoCompatibilityRequest(BaseModel):
    """Request model for video compatibility check"""
    video_id: str
    device_capabilities: List[str]  # List of capability strings

class VideoSearchRequest(BaseModel):
    """Request model for video search"""
    query: Optional[str] = ""
    categories: Optional[List[str]] = None
    max_complexity: Optional[str] = None  # "low", "medium", "high"
    device_capabilities: Optional[List[str]] = None

class VideoCompatibilityResponse(BaseModel):
    """Response model for video compatibility check"""
    compatible: bool
    video_id: str
    video_title: str
    missing_capabilities: List[str]
    supported_effects: List[str]
    effect_complexity: str
    duration: float

class VideoSearchResponse(BaseModel):
    """Response model for video search results"""
    videos: List[Dict[str, Any]]
    total_count: int
    filters_applied: Dict[str, Any]

# Create router
router = APIRouter(prefix="/api/videos", tags=["Video Management"])

# Dependencies
def get_video_service() -> VideoService:
    """Dependency to get VideoService instance"""
    settings = Settings()
    return VideoService(settings)

def get_device_service() -> DeviceService:
    """Dependency to get DeviceService instance"""
    return DeviceService()

# API Endpoints

@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_videos(video_service: VideoService = Depends(get_video_service)):
    """Get all available enhanced videos"""
    try:
        videos = video_service.get_all_enhanced_videos()
        return [video.dict() for video in videos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving videos: {str(e)}")

@router.get("/{video_id}", response_model=Dict[str, Any])
async def get_video_by_id(video_id: str, video_service: VideoService = Depends(get_video_service)):
    """Get specific video by ID"""
    try:
        video = video_service.get_enhanced_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
        return video.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving video: {str(e)}")

@router.get("/{video_id}/sync-data", response_model=Dict[str, Any])
async def get_video_sync_data(video_id: str, video_service: VideoService = Depends(get_video_service)):
    """Get sync pattern data for a specific video"""
    try:
        sync_data = video_service.get_video_sync_data(video_id)
        if not sync_data:
            raise HTTPException(status_code=404, detail=f"Sync data not found for video: {video_id}")
        return sync_data.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sync data: {str(e)}")

@router.post("/compatibility-check", response_model=VideoCompatibilityResponse)
async def check_video_compatibility(
    request: VideoCompatibilityRequest,
    video_service: VideoService = Depends(get_video_service)
):
    """Check if a video is compatible with device capabilities"""
    try:
        # Convert string capabilities to DeviceCapability enum
        device_capabilities = []
        for cap_str in request.device_capabilities:
            try:
                device_capabilities.append(DeviceCapability(cap_str))
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid device capability: {cap_str}"
                )
        
        result = video_service.validate_video_compatibility(
            request.video_id, 
            device_capabilities
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return VideoCompatibilityResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking compatibility: {str(e)}")

@router.get("/by-device/{token}", response_model=List[Dict[str, Any]])
async def get_compatible_videos_for_device(
    token: str,
    device_service: DeviceService = Depends(get_device_service),
    video_service: VideoService = Depends(get_video_service)
):
    """Get videos compatible with a registered device"""
    try:
        # Get device info using token
        device_info = device_service.get_device_by_token(token)
        if not device_info:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Get device capabilities from product code
        product_info = device_service.get_product_info(device_info.product_code)
        if not product_info:
            raise HTTPException(status_code=400, detail="Invalid product code")
        
        # Convert capabilities to DeviceCapability enum
        device_capabilities = []
        for cap_str in product_info.capabilities:
            try:
                device_capabilities.append(DeviceCapability(cap_str))
            except ValueError:
                continue  # Skip invalid capabilities
        
        # Get compatible videos
        compatible_videos = video_service.get_compatible_videos(device_capabilities)
        return [video.dict() for video in compatible_videos]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting compatible videos: {str(e)}")

@router.get("/by-complexity/{complexity}", response_model=List[Dict[str, Any]])
async def get_videos_by_complexity(
    complexity: str,
    video_service: VideoService = Depends(get_video_service)
):
    """Get videos filtered by maximum effect complexity"""
    try:
        # Validate complexity level
        try:
            max_complexity = EffectComplexity(complexity)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid complexity level. Use: {[c.value for c in EffectComplexity]}"
            )
        
        videos = video_service.get_videos_by_complexity(max_complexity)
        return [video.dict() for video in videos]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering by complexity: {str(e)}")

@router.get("/by-category/{category}", response_model=List[Dict[str, Any]])
async def get_videos_by_category(
    category: str,
    video_service: VideoService = Depends(get_video_service)
):
    """Get videos filtered by category"""
    try:
        videos = video_service.get_videos_by_category(category)
        return [video.dict() for video in videos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering by category: {str(e)}")

@router.post("/search", response_model=VideoSearchResponse)
async def search_videos(
    request: VideoSearchRequest,
    video_service: VideoService = Depends(get_video_service)
):
    """Search videos with multiple filters"""
    try:
        # Convert complexity string to enum
        max_complexity = None
        if request.max_complexity:
            try:
                max_complexity = EffectComplexity(request.max_complexity)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid complexity level: {request.max_complexity}"
                )
        
        # Convert device capabilities
        device_capabilities = None
        if request.device_capabilities:
            device_capabilities = []
            for cap_str in request.device_capabilities:
                try:
                    device_capabilities.append(DeviceCapability(cap_str))
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid device capability: {cap_str}"
                    )
        
        # Perform search
        videos = video_service.search_videos(
            query=request.query or "",
            categories=request.categories,
            max_complexity=max_complexity,
            device_capabilities=device_capabilities
        )
        
        # Prepare response
        return VideoSearchResponse(
            videos=[video.dict() for video in videos],
            total_count=len(videos),
            filters_applied={
                "query": request.query,
                "categories": request.categories,
                "max_complexity": request.max_complexity,
                "device_capabilities": request.device_capabilities
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching videos: {str(e)}")

@router.get("/statistics", response_model=Dict[str, Any])
async def get_video_statistics(video_service: VideoService = Depends(get_video_service)):
    """Get comprehensive statistics about available videos"""
    try:
        return video_service.get_video_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

# Legacy compatibility endpoints
@router.get("/legacy/list", response_model=List[Dict[str, Any]])
async def get_legacy_video_list(video_service: VideoService = Depends(get_video_service)):
    """Get video list in legacy format for backwards compatibility"""
    try:
        legacy_videos = video_service.get_available_videos()
        return [video.dict() for video in legacy_videos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving legacy video list: {str(e)}")

@router.get("/legacy/{video_id}/sync", response_model=Dict[str, Any])
async def get_legacy_sync_data(
    video_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """Get sync data in legacy format for backwards compatibility"""
    try:
        # Use legacy method
        sync_data = video_service.get_sync_data(video_id)
        if not sync_data:
            raise HTTPException(status_code=404, detail=f"Sync data not found for video: {video_id}")
        return sync_data.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving legacy sync data: {str(e)}")

# Health check endpoint
@router.get("/health", response_model=Dict[str, str])
async def video_management_health():
    """Health check for video management service"""
    return {
        "status": "healthy",
        "service": "video_management",
        "version": "2.0.0"
    }