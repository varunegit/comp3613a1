from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.models.student_awards import Volunteer
from app.repositories.student_awards import StudentAwardsRepository


@dataclass(frozen=True)
class ActionResult:
    message: str
    category: str


class VolunteerHoursService:
    def __init__(self, db: Session):
        self.repository = StudentAwardsRepository(db)

    def get_activity_options(self) -> list[Volunteer]:
        return self.repository.get_activity_options()

    def get_dashboard(self, user_id: int) -> dict[str, object]:
        student = self.repository.get_student_by_user_id(user_id)
        if student is None or student.studentId is None:
            return {
                "student": None,
                "approved_hours": Decimal("0"),
                "milestone_target": 30,
                "recent_submissions": [],
            }

        approved_hours = self.repository.get_approved_hours(student.studentId)
        recent_rows = self.repository.get_recent_submissions(student.studentId)
        recent_submissions = [
            {
                "submission": submission,
                "activity": activity,
                "activity_name": activity.name,
            }
            for submission, activity in recent_rows
        ]
        milestone_target = (int(approved_hours // Decimal("30")) + 1) * 30
        return {
            "student": student,
            "approved_hours": approved_hours,
            "milestone_target": milestone_target,
            "recent_submissions": recent_submissions,
        }

    def submit_volunteer_hours(
        self,
        *,
        user_id: int,
        activity_id: str | None,
        activity_name: str | None,
        description: str | None,
        location: str | None,
        activity_date: date | None,
        hours: Decimal,
    ) -> ActionResult:
        student = self.repository.get_student_by_user_id(user_id)
        if student is None or student.studentId is None:
            return ActionResult(
                "Your student profile is not available. Contact an administrator.",
                "danger",
            )
        if hours <= 0 or hours > Decimal("9999.99"):
            return ActionResult(
                "Hours must be greater than zero and no more than 9999.99.",
                "danger",
            )
        if activity_date is None:
            return ActionResult("Enter the volunteer date.", "danger")

        new_activity: Volunteer | None = None
        volunteer_id: int | None = None
        if activity_id:
            try:
                volunteer_id = int(activity_id)
            except ValueError:
                return ActionResult("Select a valid volunteer activity.", "danger")
            activity = self.repository.get_activity_by_id(volunteer_id)
            if activity is None:
                return ActionResult(
                    "The selected volunteer activity was not found.",
                    "danger",
                )
        else:
            clean_name = (activity_name or "").strip()
            clean_description = (description or "").strip()
            clean_location = (location or "").strip()
            if not clean_name or not clean_description or not clean_location:
                return ActionResult(
                    "Enter the name, description, and location for the unlisted activity.",
                    "danger",
                )
            new_activity = Volunteer(
                name=clean_name,
                description=clean_description,
                location=clean_location,
                date=activity_date,
            )

        self.repository.create_submission(
            student_id=student.studentId,
            activity_id=volunteer_id,
            activity_date=activity_date,
            hours=hours,
            new_activity=new_activity,
        )
        return ActionResult(
            "Volunteer hours submitted for administrator verification.",
            "success",
        )

    def get_activity_by_id(self, activity_id: int) -> Volunteer | None:
        return self.repository.get_activity_by_id(activity_id)
