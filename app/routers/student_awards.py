from datetime import date
from decimal import Decimal

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AdminDep, AuthDep
from app.dependencies.session import SessionDep
from app.services.student_awards import StudentAwardsService
from app.utilities.flash import flash
from . import router, templates


@router.get("/app/leaderboard", response_class=HTMLResponse)
async def leaderboard_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = StudentAwardsService(db)
    leaderboard = service.get_leaderboard(user_id=user.id)
    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={
            "user": user,
            "is_admin": user.role == "admin",
            "leaderboard": leaderboard,
            "your_rank": next(
                (row for row in leaderboard if row["is_current_user"]),
                None,
            ),
        },
    )


@router.get("/app/progress", response_class=HTMLResponse)
async def volunteer_progress_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    student_id: int | None = None,
    search: str = "",
):
    is_admin = user.role == "admin"
    service = StudentAwardsService(db)
    dashboard = service.get_progress(
        user_id=user.id,
        is_admin=is_admin,
        student_id=student_id,
    )
    if is_admin and student_id is not None and dashboard["student"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="progress.html",
        context={
            "user": user,
            "is_admin": is_admin,
            "activities": service.get_activity_options(),
            "search_query": search.strip(),
            "search_results": (
                service.search_students(search)
                if is_admin and search.strip()
                else []
            ),
            **dashboard,
        },
    )


@router.get("/app/progress/students")
async def student_search_suggestions(
    user: AdminDep,
    db: SessionDep,
    search: str = "",
):
    students = StudentAwardsService(db).search_students(search)
    return [
        {
            "student_id": student.studentId,
            "name": f"{student.fname} {student.lname}",
        }
        for student in students
        if student.studentId is not None
    ]


@router.post("/app/progress/{submission_id}/resubmit")
async def resubmit_rejected_hours(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    submission_id: int,
    hours: Decimal = Form(),
    activity_date: date = Form(),
    activity_id: str | None = Form(default=None),
    activity_name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    location: str | None = Form(default=None),
):
    result = StudentAwardsService(db).resubmit_rejected_hours(
        user_id=user.id,
        submission_id=submission_id,
        hours=hours,
        activity_date=activity_date,
        activity_id=activity_id,
        activity_name=activity_name,
        description=description,
        location=location,
    )
    flash(request, result.message, result.category)
    return RedirectResponse(
        url=request.url_for("volunteer_progress_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/awards", response_class=HTMLResponse)
async def awards_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    page = StudentAwardsService(db).get_awards_page(user.id)
    return templates.TemplateResponse(
        request=request,
        name="awards.html",
        context={
            "user": user,
            **page,
        },
    )


@router.post("/app/awards/{award_id}/redeem")
async def redeem_award(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    award_id: int,
):
    result = StudentAwardsService(db).redeem_award(
        user_id=user.id,
        award_id=award_id,
    )
    flash(request, result.message, result.category)
    return RedirectResponse(
        url=request.url_for("awards_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/admin/volunteer-hours", response_class=HTMLResponse)
async def verify_volunteer_hours_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    return templates.TemplateResponse(
        request=request,
        name="verify_hours.html",
        context={
            "user": user,
            "pending_submissions": StudentAwardsService(db).get_review_queue(),
            "selected": None,
        },
    )


@router.get(
    "/admin/volunteer-hours/{submission_id}",
    response_class=HTMLResponse,
)
async def review_volunteer_hours_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    submission_id: int,
):
    service = StudentAwardsService(db)
    details = service.get_review_details(submission_id)
    if details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="verify_hours.html",
        context={
            "user": user,
            "pending_submissions": service.get_review_queue(),
            "selected": details,
        },
    )


@router.post("/admin/volunteer-hours/{submission_id}/approve")
async def approve_volunteer_hours(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    submission_id: int,
):
    result = StudentAwardsService(db).review_submission(
        user_id=user.id,
        submission_id=submission_id,
        approved=True,
    )
    flash(request, result.message, result.category)
    return RedirectResponse(
        url=request.url_for("verify_volunteer_hours_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/volunteer-hours/{submission_id}/reject")
async def reject_volunteer_hours(
    request: Request,
    user: AdminDep,
    db: SessionDep,
    submission_id: int,
    reject_reason: str = Form(),
):
    result = StudentAwardsService(db).review_submission(
        user_id=user.id,
        submission_id=submission_id,
        approved=False,
        reject_reason=reject_reason,
    )
    flash(request, result.message, result.category)
    return RedirectResponse(
        url=request.url_for("verify_volunteer_hours_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
