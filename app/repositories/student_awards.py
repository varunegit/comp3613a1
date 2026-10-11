from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.models.student_awards import (
    Administrator,
    Award,
    Redeem,
    Student,
    Volunteer,
    VolunteerSubmission,
)


class StudentAwardsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_student_by_user_id(self, user_id: int) -> Student | None:
        statement = select(Student).where(Student.userId == user_id)
        return self.db.exec(statement).first()

    def get_student_by_id(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)

    def search_students(self, query: str, limit: int = 25) -> list[Student]:
        clean_query = query.strip()
        if not clean_query:
            return []

        name_match = func.lower(Student.fname + " " + Student.lname).contains(
            clean_query.lower()
        )
        if clean_query.isdecimal():
            statement = select(Student).where(
                (Student.studentId == int(clean_query)) | name_match
            )
        else:
            statement = select(Student).where(name_match)
        statement = statement.order_by(Student.lname, Student.fname).limit(limit)
        return self.db.exec(statement).all()

    def get_administrator_by_user_id(self, user_id: int) -> Administrator | None:
        statement = select(Administrator).where(Administrator.userId == user_id)
        return self.db.exec(statement).first()

    def get_activity_options(self) -> list[Volunteer]:
        statement = select(Volunteer).order_by(Volunteer.date.desc())
        return self.db.exec(statement).all()

    def get_activity_by_id(self, volunteer_id: int) -> Volunteer | None:
        return self.db.get(Volunteer, volunteer_id)

    def get_approved_hours(self, student_id: int) -> Decimal:
        statement = select(
            func.coalesce(func.sum(VolunteerSubmission.time), 0)
        ).where(
            VolunteerSubmission.studentId == student_id,
            VolunteerSubmission.status == "Approved",
        )
        total = self.db.exec(statement).one()
        return Decimal(total)

    def get_recent_submissions(
        self,
        student_id: int,
        limit: int = 10,
    ) -> list[tuple[VolunteerSubmission, Volunteer]]:
        statement = (
            select(VolunteerSubmission, Volunteer)
            .join(Volunteer, Volunteer.volunteerId == VolunteerSubmission.volunteerId)
            .where(VolunteerSubmission.studentId == student_id)
            .order_by(
                VolunteerSubmission.date.desc(),
                VolunteerSubmission.submissionId.desc(),
            )
            .limit(limit)
        )
        return list(self.db.exec(statement).all())

    def update_rejected_submission(
        self,
        submission: VolunteerSubmission,
        *,
        activity_id: int | None,
        activity_date: date,
        hours: Decimal,
        new_activity: Volunteer | None = None,
    ) -> None:
        try:
            if new_activity is not None:
                self.db.add(new_activity)
                self.db.flush()
                if new_activity.volunteerId is None:
                    raise RuntimeError("New volunteer activity was not assigned an ID")
                activity_id = new_activity.volunteerId
            if activity_id is None:
                raise RuntimeError("A volunteer activity is required for each submission")

            submission.volunteerId = activity_id
            submission.date = activity_date
            submission.time = hours
            submission.status = "Pending"
            submission.rejectReason = None
            submission.adminId = None
            self.db.add(submission)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def get_leaderboard(self) -> list[tuple[Student, Decimal]]:
        approved_hours = func.coalesce(func.sum(VolunteerSubmission.time), 0)
        statement = (
            select(Student, approved_hours)
            .outerjoin(
                VolunteerSubmission,
                (VolunteerSubmission.studentId == Student.studentId)
                & (VolunteerSubmission.status == "Approved"),
            )
            .group_by(Student.studentId)
            .order_by(approved_hours.desc(), Student.lname, Student.fname)
        )
        return [
            (student, Decimal(hours))
            for student, hours in self.db.exec(statement).all()
        ]

    def get_pending_submissions(
        self,
    ) -> list[tuple[VolunteerSubmission, str, str, str]]:
        statement = (
            select(
                VolunteerSubmission,
                Volunteer.name,
                Student.fname,
                Student.lname,
            )
            .join(Volunteer, Volunteer.volunteerId == VolunteerSubmission.volunteerId)
            .join(Student, Student.studentId == VolunteerSubmission.studentId)
            .where(VolunteerSubmission.status == "Pending")
            .order_by(VolunteerSubmission.date, VolunteerSubmission.submissionId)
        )
        return list(self.db.exec(statement).all())

    def get_submission_details(
        self,
        submission_id: int,
    ) -> tuple[VolunteerSubmission, Volunteer, Student] | None:
        statement = (
            select(VolunteerSubmission, Volunteer, Student)
            .join(Volunteer, Volunteer.volunteerId == VolunteerSubmission.volunteerId)
            .join(Student, Student.studentId == VolunteerSubmission.studentId)
            .where(VolunteerSubmission.submissionId == submission_id)
        )
        return self.db.exec(statement).first()

    def get_submission_by_id(
        self,
        submission_id: int,
    ) -> VolunteerSubmission | None:
        return self.db.get(VolunteerSubmission, submission_id)

    def review_submission(
        self,
        submission: VolunteerSubmission,
        *,
        admin_id: int,
        approved: bool,
        reject_reason: str | None = None,
    ) -> None:
        try:
            submission.status = "Approved" if approved else "Rejected"
            submission.rejectReason = None if approved else reject_reason
            submission.adminId = admin_id
            self.db.add(submission)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def resubmit_submission(
        self,
        submission: VolunteerSubmission,
        *,
        hours: Decimal,
        activity_date: date,
    ) -> None:
        try:
            submission.time = hours
            submission.date = activity_date
            submission.status = "Pending"
            submission.rejectReason = None
            submission.adminId = None
            self.db.add(submission)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def get_active_awards(self) -> list[Award]:
        statement = (
            select(Award)
            .where(Award.status == "Active")
            .order_by(Award.requiredHours, Award.name)
        )
        return self.db.exec(statement).all()

    def get_award_by_id(self, award_id: int) -> Award | None:
        return self.db.get(Award, award_id)

    def get_redemption_history(
        self,
        student_id: int,
    ) -> list[tuple[Redeem, str]]:
        statement = (
            select(Redeem, Award.name)
            .join(Award, Award.awardId == Redeem.awardId)
            .where(Redeem.studentId == student_id)
            .order_by(Redeem.redeemedAt.desc(), Redeem.redeemId.desc())
        )
        return list(self.db.exec(statement).all())

    def create_redemption(
        self,
        *,
        student_id: int,
        award_id: int,
    ) -> Redeem:
        try:
            redemption = Redeem(
                studentId=student_id,
                awardId=award_id,
                status="Redeemed",
            )
            self.db.add(redemption)
            self.db.commit()
            self.db.refresh(redemption)
            return redemption
        except Exception:
            self.db.rollback()
            raise

    def create_submission(
        self,
        *,
        student_id: int,
        activity_id: int | None,
        activity_date: date,
        hours: Decimal,
        new_activity: Volunteer | None = None,
    ) -> VolunteerSubmission:
        try:
            if new_activity is not None:
                self.db.add(new_activity)
                self.db.flush()
                if new_activity.volunteerId is None:
                    raise RuntimeError("New volunteer activity was not assigned an ID")
                activity_id = new_activity.volunteerId
            if activity_id is None:
                raise RuntimeError("A volunteer activity is required for each submission")
            submission = VolunteerSubmission(
                studentId=student_id,
                volunteerId=activity_id,
                time=hours,
                date=activity_date,
                status="Pending",
            )
            self.db.add(submission)
            self.db.commit()
            self.db.refresh(submission)
            return submission
        except Exception:
            self.db.rollback()
            raise