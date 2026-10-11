from datetime import date
from decimal import Decimal

from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.services.volunteer_hours import VolunteerHoursService
from app.utilities.flash import flash
from . import router, templates


@router.get("/app/volunteer-hours", response_class=HTMLResponse)
async def log_volunteer_hours_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = VolunteerHoursService(db)
    activities = service.get_activity_options()
    dashboard = service.get_dashboard(user.id)
    return templates.TemplateResponse(
        request=request,
        name="volunteer_hours.html",
        context={
            "user": user,
            "activities": activities,
            **dashboard,
        },
    )


@router.post("/app/volunteer-hours")
async def submit_volunteer_hours(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    activity_id: str | None = Form(default=None),
    activity_name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    location: str | None = Form(default=None),
    activity_date: date | None = Form(default=None),
    hours: Decimal = Form(),
):
    service = VolunteerHoursService(db)
    result = service.submit_volunteer_hours(
        user_id=user.id,
        activity_id=activity_id,
        activity_name=activity_name,
        description=description,
        location=location,
        activity_date=activity_date,
        hours=hours,
    )
    flash(request, result.message, result.category)
    return RedirectResponse(
        url=request.url_for("log_volunteer_hours_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
