from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.application.dto.feedback_dto import SubmitFeedbackRequest
from app.application.use_cases.feedback.submit_feedback import SubmitFeedbackUseCase
from app.presentation.api.dependencies import get_current_user_id, get_submit_feedback_use_case

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: SubmitFeedbackRequest,
    use_case: Annotated[SubmitFeedbackUseCase, Depends(get_submit_feedback_use_case)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    feedback = await use_case.execute(
        itinerary_id=UUID(payload.itinerary_id),
        user_id=user_id,
        rating=payload.rating,
        liked_activity_titles=payload.liked_activity_titles,
        comment=payload.comment,
    )
    return {"id": str(feedback.id), "status": "received"}
