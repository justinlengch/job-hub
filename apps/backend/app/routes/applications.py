from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.core.auth import get_current_user
from app.services.base_service import ServiceOperationError
from app.services.supabase.application_source_service import application_source_service

router = APIRouter(prefix="/api", tags=["applications"])


@router.post("/linkedin/import")
async def import_linkedin_history(
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user),
):
    try:
        payload = await file.read()
        rows, errors = application_source_service.parse_upload_rows(
            file.filename or "linkedin-upload.csv", payload
        )
        result = await application_source_service.import_linkedin_rows(
            current_user_id, rows
        )
        if errors:
            result["errors"] = [*result.get("errors", []), *errors]
            result["summary"]["failed_rows"] += len(errors)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/applications/review-queue")
async def get_review_queue(current_user_id: str = Depends(get_current_user)):
    try:
        return await application_source_service.get_review_queue(current_user_id)
    except ServiceOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/applications/review-queue/{source_id}/confirm")
async def confirm_review_queue_item(
    source_id: str, current_user_id: str = Depends(get_current_user)
):
    try:
        return await application_source_service.confirm_review_queue_item(
            current_user_id, source_id
        )
    except ServiceOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/applications/review-queue/{source_id}/separate")
async def separate_review_queue_item(
    source_id: str, current_user_id: str = Depends(get_current_user)
):
    try:
        return await application_source_service.separate_review_queue_item(
            current_user_id, source_id
        )
    except ServiceOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/sankey")
async def get_sankey_data(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    company: Optional[str] = Query(default=None),
    current_user_id: str = Depends(get_current_user),
):
    try:
        return await application_source_service.get_sankey_data(
            current_user_id,
            start_date=start_date,
            end_date=end_date,
            source_type=source_type,
            company=company,
        )
    except ServiceOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/applications/{application_id}/final-round")
async def mark_final_round(
    application_id: str, current_user_id: str = Depends(get_current_user)
):
    try:
        return await application_source_service.toggle_final_round(
            current_user_id, application_id, True
        )
    except ServiceOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/applications/{application_id}/final-round")
async def clear_final_round(
    application_id: str, current_user_id: str = Depends(get_current_user)
):
    try:
        return await application_source_service.toggle_final_round(
            current_user_id, application_id, False
        )
    except ServiceOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
