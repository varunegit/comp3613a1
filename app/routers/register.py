from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError

from app.dependencies import SessionDep
from app.services.auth_service import AuthService
from app.repositories.user import UserRepository
from app.utilities.flash import flash
from . import router, templates


@router.get("/register", response_class=HTMLResponse)
async def register_view(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="register.html",
    )


@router.post("/register", response_class=HTMLResponse)
def signup_user(
    request: Request,
    db: SessionDep,
    username: str = Form(),
    email: EmailStr = Form(),
    password: str = Form(),
    fname: str = Form(),
    lname: str = Form(),
    degree: str = Form(),
):
    profile_fields = (username, fname, lname, degree)
    if any(not field.strip() for field in profile_fields):
        flash(request, "Complete every required student profile field.", "danger")
        return RedirectResponse(
            url=request.url_for("register_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    try:
        auth_service.register_user(
            username=username.strip(),
            email=str(email).strip(),
            password=password,
            fname=fname.strip(),
            lname=lname.strip(),
            degree=degree.strip(),
        )
    except IntegrityError:
        flash(request, "Username or email already exists", "danger")
        return RedirectResponse(
            url=request.url_for("register_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    flash(request, "Student account created. Sign in to continue!")
    return RedirectResponse(
        url=request.url_for("login_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
