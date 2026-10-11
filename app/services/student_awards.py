from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.models.student_awards import Award, Student, Volunteer
from app.repositories.student_awards import StudentAwardsRepository
from app.services.volunteer_hours import ActionResult


class StudentAwardsService:
    def __init__(self, db: Session):
        self.repository = StudentAwardsRepository(db)

    @staticmethod
    def _level_for_hours(hours: Decimal) -> tuple[str, str | None, int]:
        if hours < Decimal("40"):
            return "Bronze", "Silver", 40
        if hours < Decimal("60"):
            return "Silver", "Gold", 60
        return "Gold", None, 60

    def get_leaderboard(self, user_id: int | None = None) -> list[dict[str, object]]:
        return [
            {
                "student": student,
                "approved_hours": hours,
                "current_level": self._level_for_hours(hours)[0],
                "rank": rank,
                "is_current_user": student.userId == user_id,
            }
            for rank, (student, hours) in enumerate(
                self.repository.get_leaderboard(),
                start=1,
            )
        ]

    def search_students(self, query: str) -> list[Student]:
        return self.repository.search_students(query)

    def get_progress(
        self,
        *,
        user_id: int,
        is_admin: bool = False,
        student_id: int | None = None,
    ) -> dict[str, object]:
        if is_admin:
            student = (
                self.repository.get_student_by_id(student_id)
                if student_id is not None
                else None
            )
        else:
            student = self.repository.get_student_by_user_id(user_id)

        if student is None or student.studentId is None:
            return {
                "student": None,
                "approved_hours": Decimal("0"),
                "current_level": None,
                "next_milestone": None,
                "milestone_target": 40,
                "next_award": None,
                "active_award_count": 0,
                "recent_submissions": [],
            }

        approved_hours = self.repository.get_approved_hours(student.studentId)
        current_level, next_milestone, milestone_target = self._level_for_hours(
            approved_hours
        )

        active_awards = self.repository.get_active_awards()
        next_award: Award | None = next(
            (
                award
                for award in active_awards
                if Decimal(award.requiredHours) > approved_hours
            ),
            None,
        )
        recent_submissions = [
            {
                "submission": submission,
                "activity": activity,
                "activity_name": activity.name,
            }
            for submission, activity in self.repository.get_recent_submissions(
                student.studentId
            )
        ]
        return {
            "student": student,
            "approved_hours": approved_hours,
            "current_level": current_level,
            "next_milestone": next_milestone,
            "milestone_target": milestone_target,
            "next_award": next_award,
            "active_award_count": len(active_awards),
            "recent_submissions": recent_submissions,
        }

    def get_activity_options(self):
        return self.repository.get_activity_options()

    def get_awards_page(self, user_id: int) -> dict[str, object]:
        student = self.repository.get_student_by_user_id(user_id)
        if student is None or student.studentId is None:
            return {
                "student": None,
                "approved_hours": Decimal("0"),
                "awards": [],
                "redemption_history": [],
            }

        approved_hours = self.repository.get_approved_hours(student.studentId)
        awards = [
            {
                "award": award,
                "eligible": approved_hours >= Decimal(award.requiredHours),
            }
            for award in self.repository.get_active_awards()
        ]
        redemption_history = [
            {
                "redemption": redemption,
                "award_name": award_name,
            }
            for redemption, award_name in self.repository.get_redemption_history(
                student.studentId
            )
        ]
        return {
            "student": student,
            "approved_hours": approved_hours,
            "awards": awards,
            "redemption_history": redemption_history,
        }

    def redeem_award(self, *, user_id: int, award_id: int) -> ActionResult:
        student = self.repository.get_student_by_user_id(user_id)
        if student is None or student.studentId is None:
            return ActionResult(
                "Your student profile is not available. Contact an administrator.",
                "danger",
            )

        award = self.repository.get_award_by_id(award_id)
        if award is None or award.status != "Active":
            return ActionResult("This award is not available.", "danger")

        approved_hours = self.repository.get_approved_hours(student.studentId)
        if approved_hours < Decimal(award.requiredHours):
            return ActionResult(
                "You do not have enough approved hours to redeem this award.",
                "warning",
            )

        self.repository.create_redemption(
            student_id=student.studentId,
            award_id=award_id,
        )
        return ActionResult(
            f"{award.name} was added to your redemption history.",
            "success",
        )

    def get_review_queue(self) -> list[dict[str, object]]:
        return [
            {
                "submission": submission,
                "activity_name": activity_name,
                "student_name": f"{first_name} {last_name}",
            }
            for submission, activity_name, first_name, last_name
            in self.repository.get_pending_submissions()
        ]

    def get_review_details(self, submission_id: int) -> dict[str, object] | None:
        details = self.repository.get_submission_details(submission_id)
        if details is None:
            return None
        submission, activity, student = details
        return {
            "submission": submission,
            "activity": activity,
            "student": student,
        }

    def review_submission(
        self,
        *,
        user_id: int,
        submission_id: int,
        approved: bool,
        reject_reason: str | None = None,
    ) -> ActionResult:
        administrator = self.repository.get_administrator_by_user_id(user_id)
        if administrator is None or administrator.adminId is None:
            return ActionResult(
                "Your administrator profile is not available.",
                "danger",
            )

        submission = self.repository.get_submission_by_id(submission_id)
        if submission is None:
            return ActionResult("The submission was not found.", "danger")
        if submission.status != "Pending":
            return ActionResult(
                "This submission has already been reviewed.",
                "warning",
            )

        reason = (reject_reason or "").strip()
        if not approved and not reason:
            return ActionResult("Enter a reason before rejecting.", "danger")
        if len(reason) > 1000:
            return ActionResult(
                "The rejection reason must be 1000 characters or fewer.",
                "danger",
            )

        self.repository.review_submission(
            submission,
            admin_id=administrator.adminId,
            approved=approved,
            reject_reason=reason or None,
        )
        message = (
            "Volunteer hours approved."
            if approved
            else "Volunteer hours rejected. The student can now correct and resubmit."
        )
        return ActionResult(message, "success")

    def resubmit_rejected_hours(
        self,
        *,
        user_id: int,
        submission_id: int,
        hours: Decimal,
        activity_date: date,
        activity_id: str | None,
        activity_name: str | None,
        description: str | None,
        location: str | None,
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

        submission = self.repository.get_submission_by_id(submission_id)
        if (
            submission is None
            or submission.studentId != student.studentId
            or submission.status != "Rejected"
        ):
            return ActionResult(
                "Only your rejected submissions can be corrected and resubmitted.",
                "danger",
            )

        selected_activity_id: int | None = None
        new_activity: Volunteer | None = None
        if activity_id:
            try:
                selected_activity_id = int(activity_id)
            except ValueError:
                return ActionResult("Select a valid volunteer activity.", "danger")
            if self.repository.get_activity_by_id(selected_activity_id) is None:
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

        self.repository.update_rejected_submission(
            submission,
            activity_id=selected_activity_id,
            hours=hours,
            activity_date=activity_date,
            new_activity=new_activity,
        )
        return ActionResult(
            "Your corrected submission has been sent for verification.",
            "success",
        )
