"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.user import User
from app.models.student_awards import (
    Administrator,
    Award,
    Redeem,
    Student,
    Volunteer,
    VolunteerSubmission,
)

__all__ = [
    "Administrator",
    "Award",
    "Redeem",
    "Student",
    "User",
    "Volunteer",
    "VolunteerSubmission",
]
