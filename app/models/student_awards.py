from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    __tablename__ = "student"

    studentId: int | None = Field(default=None, primary_key=True)
    userId: int = Field(foreign_key="user.id", unique=True, index=True)
    fname: str
    lname: str
    email: str
    degree: str
    volunteerHours: Decimal = Field(
        default=Decimal("0"),
        max_digits=8,
        decimal_places=2,
    )


class Administrator(SQLModel, table=True):
    __tablename__ = "administrator"

    adminId: int | None = Field(default=None, primary_key=True)
    userId: int = Field(foreign_key="user.id", unique=True, index=True)
    fname: str
    email: str


class Volunteer(SQLModel, table=True):
    __tablename__ = "volunteer"

    volunteerId: int | None = Field(default=None, primary_key=True)
    name: str
    description: str
    location: str
    date: date


class VolunteerSubmission(SQLModel, table=True):
    __tablename__ = "volunteer_submission"

    submissionId: int | None = Field(default=None, primary_key=True)
    studentId: int = Field(foreign_key="student.studentId", index=True)
    volunteerId: int = Field(foreign_key="volunteer.volunteerId", index=True)
    time: Decimal = Field(
        max_digits=8,
        decimal_places=2,
    )
    date: date
    status: str = Field(default="Pending", index=True)
    rejectReason: str | None = Field(default=None)
    adminId: int | None = Field(foreign_key="administrator.adminId", default=None)


class Award(SQLModel, table=True):
    __tablename__ = "award"

    awardId: int | None = Field(default=None, primary_key=True)
    name: str
    description: str
    requiredHours: int
    status: str = Field(default="Active", index=True)


class Redeem(SQLModel, table=True):
    __tablename__ = "redeem"

    redeemId: int | None = Field(default=None, primary_key=True)
    studentId: int = Field(foreign_key="student.studentId", index=True)
    awardId: int = Field(foreign_key="award.awardId", index=True)
    status: str = Field(default="Pending", index=True)
    redeemedAt: date = Field(default_factory=date.today)
