from fastapi import APIRouter, Depends, Request, UploadFile

from app.core.rate_limit import limiter
from app.dependencies import get_current_admin, get_current_user
from app.services import storage_service

router = APIRouter(prefix="/api/upload", tags=["upload"])

EXT_MAP = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


@router.post("/image", dependencies=[Depends(get_current_user)])
@limiter.limit("30/minute")                 # FIX m3 — was missing rate limiting
async def upload_image(request: Request, file: UploadFile):
    content = await file.read()
    url = await storage_service.upload_file(
        "design-uploads", content, file.content_type, EXT_MAP.get(file.content_type, "bin")
    )
    return {"url": url}


@router.post("/design-export", dependencies=[Depends(get_current_user)])
@limiter.limit("20/minute")                 # FIX m3 — was missing rate limiting
async def upload_design_export(request: Request, mockup: UploadFile, print_file: UploadFile):
    mockup_bytes, print_bytes = await mockup.read(), await print_file.read()
    mockup_url = await storage_service.upload_file(
        "design-exports", mockup_bytes, mockup.content_type, EXT_MAP.get(mockup.content_type, "png")
    )
    print_url = await storage_service.upload_file(
        "design-exports", print_bytes, print_file.content_type, EXT_MAP.get(print_file.content_type, "png")
    )
    return {"mockup_url": mockup_url, "print_url": print_url}


# FIX M8 — Product image upload for admin (was missing entirely)
@router.post("/product-image", dependencies=[Depends(get_current_admin)])
@limiter.limit("30/minute")
async def upload_product_image(request: Request, file: UploadFile):
    content = await file.read()
    url = await storage_service.upload_file(
        "product-images", content, file.content_type, EXT_MAP.get(file.content_type, "bin")
    )
    return {"url": url}