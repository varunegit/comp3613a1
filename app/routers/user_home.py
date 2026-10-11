from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi import status
from app.dependencies.session import SessionDep
from app.dependencies.auth import AuthDep, IsUserLoggedIn, get_current_user, is_admin
from . import router


@router.get("/app")
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    return RedirectResponse(
        url=request.url_for("log_volunteer_hours_view"),
        status_code=303,
    )