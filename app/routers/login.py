from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, status, Form
from app.dependencies import SessionDep
from . import router, templates
from app.services.auth_service import AuthService
from app.repositories.user import UserRepository
from app.repositories.student_awards import StudentAwardsRepository
from app.utilities.flash import flash
from app.utilities.security import access_token_cookie_kwargs


@router.get("/login", response_class=HTMLResponse)
async def login_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
    )


@router.post("/login", response_class=HTMLResponse)
async def login_action_ajax(
    db: SessionDep,
    request: Request,
    username: str = Form(),
    password: str = Form(),
):
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    access_token = auth_service.authenticate_user(username, password)
    if not access_token:
        flash(request, "Incorrect username or password", "danger")
        return RedirectResponse(
            url=request.url_for("login_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = user_repo.get_by_username(username)
    if user is None or user.id is None:
        flash(
            request,
            "This account is not configured for Student Awards access.",
            "danger",
        )
        return RedirectResponse(
            url=request.url_for("login_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    profiles = StudentAwardsRepository(db)
    if user.role == "admin":
        profile = profiles.get_administrator_by_user_id(user.id)
        dest = "admin_home_view"
    elif user.role == "regular_user":
        profile = profiles.get_student_by_user_id(user.id)
        dest = "user_home_view"
    else:
        flash(
            request,
            "This account role is not configured for Student Awards access.",
            "danger",
        )
        return RedirectResponse(
            url=request.url_for("login_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if profile is None:
        flash(
            request,
            "Your account is missing its linked Student Awards profile. Contact an administrator.",
            "danger",
        )
        return RedirectResponse(
            url=request.url_for("login_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    response = RedirectResponse(
        url=request.url_for(dest),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        **access_token_cookie_kwargs(),
    )
    return response
