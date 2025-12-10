from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.schemas.scan_schemas import ScanCreate, ScanResponse
from app.services.scan_service import ScanService
from app.controllers.scans import ScanController
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_in: ScanCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new scan for the given URL.
    """
    service = ScanService(db)
    scan = await service.perform_scan(user_id=current_user.id, url_in=str(scan_in.url))
    return scan


@router.get("/", response_model=list[ScanResponse])
async def get_scans(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    search: str = None,
) -> Any:
    """
    Get all scans for the current user.
    """
    controller = ScanController(db)
    scans = controller.get_scans(user_id=current_user.id, search=search)
    return scans

@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get a specific scan by ID.
    """
    controller = ScanController(db)
    scan = controller.get_scan(user_id=current_user.id, scan_id=scan_id)
    return scan


