#!/usr/bin/env python3
"""FastStarter project CLI — stdlib argparse (no extra CLI library).

From the project root (venv active, deps installed; ``.env`` optional — falls back to ``.env.example``):

    python manage.py init
    python manage.py run
    python manage.py users
    python manage.py report --name "Student Name" --id "816000000"
    python manage.py usecase
    python manage.py skills-verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_models_loaded() -> None:
    import app.models  # noqa: F401


_DEMO_STUDENT_NAMES = (
    ("Maya", "Patel"),
    ("Ethan", "Nguyen"),
    ("Sofia", "Rodriguez"),
    ("Daniel", "Kim"),
    ("Aisha", "Mohammed"),
    ("Noah", "Williams"),
    ("Priya", "Shah"),
    ("Lucas", "Martin"),
    ("Amara", "Okafor"),
    ("Gabriel", "Santos"),
    ("Chloe", "Bennett"),
    ("Arjun", "Mehta"),
    ("Elena", "Garcia"),
    ("Marcus", "Johnson"),
    ("Leila", "Haddad"),
    ("Oliver", "Thompson"),
    ("Nia", "Campbell"),
    ("Mateo", "Rivera"),
    ("Zoe", "Wilson"),
    ("Ravi", "Desai"),
)


def cmd_init(args: argparse.Namespace) -> None:
    """Create database tables (drops existing by default) and seed demo users."""
    from app.config import get_settings
    from app.database import drop_all, ensure_db_and_tables

    _ensure_models_loaded()
    if args.drop:
        print("Dropping all tables…")
        # Drop can fail on a brand-new empty DB; create path still retries.
        try:
            drop_all()
        except Exception as exc:  # noqa: BLE001
            from app.database import is_db_not_ready_error

            if not is_db_not_ready_error(exc):
                raise
            print(f"Database not ready yet while dropping ({exc}); continuing…")
    print("Creating tables…")
    ensure_db_and_tables()
    print(f"Database ready ({get_settings().database_uri}).")
    if getattr(args, "seed", True):
        cmd_seed(args)


def cmd_seed(args: argparse.Namespace) -> None:
    """Insert demo users.

    bob / bobpass       (regular_user)
    admin / adminpass   (admin)
    """
    from datetime import date, timedelta
    from decimal import Decimal

    from app.database import ensure_db_and_tables, get_cli_session
    from app.models.student_awards import (
        Administrator,
        Award,
        Redeem,
        Student,
        Volunteer,
        VolunteerSubmission,
    )
    from app.repositories.user import UserRepository
    from app.schemas.user import AdminCreate, RegularUserCreate
    from sqlmodel import select
    from app.utilities.security import encrypt_password

    _ensure_models_loaded()
    ensure_db_and_tables()

    demo_users = [
        ("bob", "bob@example.com", "bobpass", "regular_user"),
        ("admin", "admin@example.com", "adminpass", "admin"),
    ]
    demo_users.extend(
        (
            f"student{student_number:02d}",
            f"student{student_number:02d}@example.com",
            "studentpass",
            "regular_user",
        )
        for student_number in range(1, len(_DEMO_STUDENT_NAMES) + 1)
    )

    created = 0
    skipped = 0
    with get_cli_session() as session:
        repo = UserRepository(session)
        for username, email, password, role in demo_users:
            if repo.get_by_username(username):
                print(f"  skip  {username} (already exists)")
                skipped += 1
                continue
            payload_cls = AdminCreate if role == "admin" else RegularUserCreate
            repo.create(
                payload_cls(
                    username=username,
                    email=email,
                    password=encrypt_password(password),
                    role=role,
                )
            )
            print(f"  create {username} ({role})")
            created += 1

        bob = repo.get_by_username("bob")
        admin = repo.get_by_username("admin")
        students: list[Student] = []
        for username, _, _, _ in demo_users:
            user = repo.get_by_username(username)
            if user is None or user.id is None or user.role != "regular_user":
                continue
            student = session.exec(
                select(Student).where(Student.userId == user.id)
            ).first()
            if username == "bob":
                first_name, last_name = "Bob", "Martinez"
                previous_seed_names = {
                    ("Bob", "Student"),
                    ("Robert", "Martinez"),
                }
            else:
                student_number = int(username.removeprefix("student"))
                first_name, last_name = _DEMO_STUDENT_NAMES[student_number - 1]
                previous_seed_names = {("Student", f"{student_number:02d}")}
            if student is None:
                student = Student(
                    userId=user.id,
                    fname=first_name,
                    lname=last_name,
                    email=user.email,
                    degree="General Studies",
                )
                session.add(student)
            elif (student.fname, student.lname) in previous_seed_names:
                student.fname = first_name
                student.lname = last_name
            students.append(student)

        if admin is not None and admin.id is not None:
            admin_profile = session.exec(
                select(Administrator).where(Administrator.userId == admin.id)
            ).first()
            if admin_profile is None:
                session.add(
                    Administrator(
                        userId=admin.id,
                        fname="Administrator",
                        email=admin.email,
                    )
                )

        session.flush()
        activity_specs = [
            (
                "Beach Cleanup",
                "Remove litter and debris from the shoreline.",
                "Kingston Waterfront",
                date(2026, 9, 20),
            ),
            (
                "Community Science Fair",
                "Support student science demonstrations.",
                "Campus Science Hall",
                date(2026, 9, 22),
            ),
            (
                "Campus Garden",
                "Prepare and maintain the student garden.",
                "North Campus",
                date(2026, 9, 24),
            ),
            (
                "Peer Tutoring",
                "Volunteer as a peer tutor for introductory courses.",
                "Learning Commons",
                date(2026, 10, 12),
            ),
            (
                "New Student Orientation",
                "Welcome incoming students and help them find campus services.",
                "Student Centre",
                date(2026, 10, 15),
            ),
            (
                "Campus Food Pantry",
                "Sort donations and prepare food parcels for students.",
                "Student Support Office",
                date(2026, 10, 19),
            ),
            (
                "Library Book Drive",
                "Collect, sort, and catalogue donated books for community partners.",
                "Main Library",
                date(2026, 10, 22),
            ),
            (
                "Recycling Awareness Booth",
                "Share recycling information and help students sort materials.",
                "Student Quadrangle",
                date(2026, 10, 26),
            ),
            (
                "Campus Open Day Guide",
                "Guide prospective students and families around campus.",
                "Admissions Welcome Desk",
                date(2026, 10, 29),
            ),
            (
                "Community Literacy Support",
                "Read with school-age learners at an after-school programme.",
                "Westside Community Centre",
                date(2026, 11, 2),
            ),
            (
                "Student Wellness Fair",
                "Assist exhibitors and help visitors navigate wellness resources.",
                "Health Sciences Atrium",
                date(2026, 11, 5),
            ),
            (
                "Blood Donation Drive Support",
                "Help with event registration and donor refreshments.",
                "Campus Health Clinic",
                date(2026, 11, 9),
            ),
            (
                "Community Technology Help",
                "Help community members with basic computer and phone tasks.",
                "Public Library",
                date(2026, 11, 12),
            ),
            (
                "Campus Arts Festival Crew",
                "Help prepare event spaces and welcome festival attendees.",
                "Fine Arts Courtyard",
                date(2026, 11, 16),
            ),
            (
                "Peer Note-Taking Support",
                "Prepare accessible lecture notes for students registered with support services.",
                "Academic Support Centre",
                date(2026, 11, 19),
            ),
            (
                "Coastal Wildlife Survey",
                "Record observations during a supervised local habitat survey.",
                "North Shore Field Site",
                date(2026, 11, 23),
            ),
            (
                "Sustainability Garden Workday",
                "Plant seedlings and maintain the university sustainability garden.",
                "Environmental Studies Garden",
                date(2026, 11, 26),
            ),
            (
                "Community Sports Day",
                "Help set up activities and support participants at a youth sports day.",
                "University Recreation Field",
                date(2026, 11, 30),
            ),
        ]
        activities: dict[str, Volunteer] = {}
        for name, description, location, activity_date in activity_specs:
            activity = session.exec(
                select(Volunteer).where(Volunteer.name == name)
            ).first()
            if activity is None:
                activity = Volunteer(
                    name=name,
                    description=description,
                    location=location,
                    date=activity_date,
                )
                session.add(activity)
            activities[name] = activity

        session.flush()
        bob_student = next(
            (student for student in students if student.userId == bob.id),
            None,
        )
        if bob_student is not None and bob_student.studentId is not None:
            if not session.exec(
                select(VolunteerSubmission).where(
                    VolunteerSubmission.studentId == bob_student.studentId
                )
            ).first():
                for name, hours in (
                    ("Beach Cleanup", "6.00"),
                    ("Community Science Fair", "4.00"),
                    ("Campus Garden", "14.00"),
                ):
                    activity = activities[name]
                    if activity.volunteerId is None:
                        raise RuntimeError(f"Seed activity {name!r} has no database ID")
                    session.add(
                        VolunteerSubmission(
                            studentId=bob_student.studentId,
                            volunteerId=activity.volunteerId,
                            time=Decimal(hours),
                            date=activity.date,
                            status="Approved",
                        )
                    )

            approved_hours = sum(
                session.exec(
                    select(VolunteerSubmission.time).where(
                        VolunteerSubmission.studentId == bob_student.studentId,
                        VolunteerSubmission.status == "Approved",
                    )
                ).all(),
                Decimal("0"),
            )
            if approved_hours < Decimal("30"):
                tutoring = activities["Peer Tutoring"]
                if tutoring.volunteerId is None:
                    raise RuntimeError("Seed activity 'Peer Tutoring' has no database ID")
                session.add(
                    VolunteerSubmission(
                        studentId=bob_student.studentId,
                        volunteerId=tutoring.volunteerId,
                        time=Decimal("30") - approved_hours,
                        date=tutoring.date,
                        status="Approved",
                    )
                )

        for student_number in range(1, len(_DEMO_STUDENT_NAMES) + 1):
            username = f"student{student_number:02d}"
            user = repo.get_by_username(username)
            student = next(
                (
                    profile
                    for profile in students
                    if user is not None and profile.userId == user.id
                ),
                None,
            )
            if student is None or student.studentId is None:
                continue
            if session.exec(
                select(VolunteerSubmission).where(
                    VolunteerSubmission.studentId == student.studentId
                )
            ).first():
                continue
            activity_name = activity_specs[(student_number - 1) % len(activity_specs)][0]
            activity = activities[activity_name]
            if activity.volunteerId is None:
                raise RuntimeError(
                    f"Seed activity {activity_name!r} has no database ID"
                )
            session.add(
                VolunteerSubmission(
                    studentId=student.studentId,
                    volunteerId=activity.volunteerId,
                    time=Decimal(5 + student_number * 2),
                    date=activity.date,
                    status="Approved",
                )
            )

        session.flush()
        existing_submissions = session.exec(select(VolunteerSubmission)).all()
        existing_submission_keys = {
            (submission.studentId, submission.volunteerId, submission.date)
            for submission in existing_submissions
        }

        gold_user = repo.get_by_username("student20")
        gold_student = next(
            (
                student
                for student in students
                if gold_user is not None and student.userId == gold_user.id
            ),
            None,
        )
        if gold_student is not None and gold_student.studentId is not None:
            gold_hours = sum(
                session.exec(
                    select(VolunteerSubmission.time).where(
                        VolunteerSubmission.studentId == gold_student.studentId,
                        VolunteerSubmission.status == "Approved",
                    )
                ).all(),
                Decimal("0"),
            )
            if gold_hours < Decimal("60"):
                gold_activity = activities["Community Sports Day"]
                if gold_activity.volunteerId is None:
                    raise RuntimeError(
                        "Seed activity 'Community Sports Day' has no database ID"
                    )
                gold_date = gold_activity.date
                while (
                    gold_student.studentId,
                    gold_activity.volunteerId,
                    gold_date,
                ) in existing_submission_keys:
                    gold_date += timedelta(days=1)
                session.add(
                    VolunteerSubmission(
                        studentId=gold_student.studentId,
                        volunteerId=gold_activity.volunteerId,
                        time=Decimal("60") - gold_hours,
                        date=gold_date,
                        status="Approved",
                    )
                )
                existing_submission_keys.add(
                    (
                        gold_student.studentId,
                        gold_activity.volunteerId,
                        gold_date,
                    )
                )

        if bob_student is not None and bob_student.studentId is not None:
            bob_submissions = session.exec(
                select(VolunteerSubmission).where(
                    VolunteerSubmission.studentId == bob_student.studentId
                )
            ).all()
            rejected_submissions = [
                submission
                for submission in bob_submissions
                if submission.status == "Rejected"
            ]
            rejection_reasons = (
                "Demo rejection: include confirmation from the activity supervisor.",
                "Demo rejection: correct the activity date to match the event record.",
            )
            for index, submission in enumerate(rejected_submissions):
                if not submission.rejectReason:
                    submission.rejectReason = rejection_reasons[
                        index % len(rejection_reasons)
                    ]

            for target_status, target_count in (("Rejected", 2), ("Pending", 2)):
                current_count = sum(
                    submission.status == target_status
                    for submission in bob_submissions
                )
                for index in range(current_count, target_count):
                    activity_name = (
                        "Beach Cleanup"
                        if target_status == "Rejected" and index == 0
                        else "Community Science Fair"
                        if target_status == "Rejected"
                        else "Campus Garden"
                        if index == 0
                        else "Peer Tutoring"
                    )
                    activity = activities[activity_name]
                    if activity.volunteerId is None:
                        raise RuntimeError(
                            f"Seed activity {activity_name!r} has no database ID"
                        )
                    submission_date = date.today()
                    while (
                        bob_student.studentId,
                        activity.volunteerId,
                        submission_date,
                    ) in existing_submission_keys:
                        submission_date -= timedelta(days=1)
                    submission = VolunteerSubmission(
                        studentId=bob_student.studentId,
                        volunteerId=activity.volunteerId,
                        time=Decimal("2.00") + Decimal(index),
                        date=submission_date,
                        status=target_status,
                        rejectReason=(
                            rejection_reasons[index % len(rejection_reasons)]
                            if target_status == "Rejected"
                            else None
                        ),
                    )
                    session.add(submission)
                    bob_submissions.append(submission)
                    existing_submission_keys.add(
                        (
                            bob_student.studentId,
                            activity.volunteerId,
                            submission_date,
                        )
                    )

        session.flush()
        existing_submissions = session.exec(select(VolunteerSubmission)).all()
        existing_submission_keys = {
            (submission.studentId, submission.volunteerId, submission.date)
            for submission in existing_submissions
        }
        pending_count = sum(
            submission.status == "Pending"
            for submission in existing_submissions
        )
        for activity in activities.values():
            if activity.date > date.today():
                continue
            if activity.volunteerId is None:
                raise RuntimeError(
                    f"Seed activity {activity.name!r} has no database ID"
                )
            for student_index, student in enumerate(students):
                if pending_count >= 10:
                    break
                if student.studentId is None:
                    continue
                submission_date = activity.date
                submission_key = (
                    student.studentId,
                    activity.volunteerId,
                    submission_date,
                )
                if submission_key in existing_submission_keys:
                    continue
                session.add(
                    VolunteerSubmission(
                        studentId=student.studentId,
                        volunteerId=activity.volunteerId,
                        time=Decimal("2.00") + Decimal(student_index % 3),
                        date=submission_date,
                        status="Pending",
                    )
                )
                existing_submission_keys.add(submission_key)
                pending_count += 1
            if pending_count >= 10:
                break

        if pending_count < 10:
            raise RuntimeError(
                "Unable to seed ten distinct pending volunteer submissions."
            )

        award_specs = [
            ("Service Starter Certificate", "Recognition for 10 approved service hours.", 10),
            ("Campus Helper Badge", "A badge for supporting campus activities.", 15),
            ("Science Fair Volunteer Award", "Recognition for event support.", 20),
            ("Student Awards Gift Voucher", "A small voucher earned through service.", 25),
            ("Community Builder Certificate", "For sustained community contribution.", 30),
            ("Garden Champion Award", "Recognition for helping campus green spaces.", 35),
            ("Bookstore Gift Voucher", "A bookstore voucher for service milestones.", 40),
            ("Peer Support Certificate", "For service that supports fellow students.", 45),
            ("Volunteer Excellence Trophy", "A trophy recognizing outstanding service.", 50),
            ("Campus Spirit Prize", "A prize for contributing to campus life.", 60),
            ("Leadership in Service Award", "Recognition of service leadership.", 70),
            ("Faculty Recognition Certificate", "Faculty recognition for volunteer service.", 80),
            ("Community Impact Prize", "A prize recognizing community impact.", 90),
            ("Principal's Service Award", "A major award for sustained service.", 100),
            ("Distinguished Volunteer Medal", "The highest student volunteer distinction.", 120),
        ]
        for name, description, required_hours in award_specs:
            award = session.exec(
                select(Award).where(Award.name == name)
            ).first()
            if award is None:
                session.add(
                    Award(
                        name=name,
                        description=description,
                        requiredHours=required_hours,
                        status="Active",
                    )
                )

        session.flush()
        if bob_student is not None and bob_student.studentId is not None:
            existing_redemptions = session.exec(
                select(Redeem).where(Redeem.studentId == bob_student.studentId)
            ).all()
            existing_award_ids = {
                redemption.awardId for redemption in existing_redemptions
            }
            redemption_count = len(existing_redemptions)
            active_awards = session.exec(
                select(Award)
                .where(
                    Award.status == "Active",
                    Award.requiredHours <= 30,
                )
                .order_by(Award.requiredHours, Award.name)
            ).all()
            for index, award in enumerate(active_awards, start=1):
                if redemption_count >= 5:
                    break
                if award.awardId is None or award.awardId in existing_award_ids:
                    continue
                session.add(
                    Redeem(
                        studentId=bob_student.studentId,
                        awardId=award.awardId,
                        status="Redeemed",
                        redeemedAt=date.today() - timedelta(days=index),
                    )
                )
                existing_award_ids.add(award.awardId)
                redemption_count += 1
            if redemption_count < 5:
                raise RuntimeError(
                    "The demo student needs five active awards eligible at 30 approved hours."
                )
        session.commit()

    print(f"Seed done — created {created}, skipped {skipped}.")
    print("Login with bob/bobpass, admin/adminpass, or student01 through student20 (password studentpass).")


def cmd_run(args: argparse.Namespace) -> None:
    """Start the FastAPI app with Uvicorn."""
    import uvicorn

    from app.config import get_settings

    settings = get_settings()
    bind_host = args.host or settings.app_host
    bind_port = args.port or settings.app_port
    if args.reload is None:
        use_reload = settings.env.lower() != "production"
    else:
        use_reload = args.reload
    print(f"Starting FastStarter on http://{bind_host}:{bind_port} (reload={use_reload})")
    uvicorn.run(
        "app.main:app",
        host=bind_host,
        port=bind_port,
        reload=use_reload,
    )


def cmd_report(args: argparse.Namespace) -> None:
    """Build the submission package: merge judge, package transcripts, write PDF.

    Guide must (1) write ``docs/judge.md`` and (2) pull every Guide chat into
    ``docs/transcripts/*.md`` before this command. Report only packages those files.
    """
    from app.report_pdf import export_report
    from app.skill_integrity import format_report, verify

    result = export_report(
        name=args.name,
        student_id=args.student_id,
        source=None if args.src is None else Path(args.src),
        output=None if args.output is None else Path(args.output),
    )
    print()
    print("Report package:")
    print(
        f"  Judge:       {'merged docs/judge.md' if result.judge_merged else 'MISSING - Guide must run student-judge first'}"
    )
    print(
        f"  Transcripts: {result.transcript_count} chat(s) in docs/transcripts/"
        + (
            ""
            if result.transcript_count
            else " (EMPTY - Guide must pull Copilot/Cursor/OpenCode chats first)"
        )
    )
    if result.transcript_zip:
        print(f"  Zip:         {result.transcript_zip.as_posix()}")
    print(f"  PDF:         {result.pdf_path.as_posix()}")
    print(format_report(verify()))


def cmd_transcripts(args: argparse.Namespace) -> None:
    """Package agent-written markdown under docs/transcripts/ (+ zip)."""
    from app.transcript_export import package_transcripts

    result = package_transcripts(make_zip=not args.no_zip)
    if result.found == 0:
        print(
            "Warning: no chat markdown in docs/transcripts/. "
            "The Guide agent must pull every Guide chat for this project "
            "(Copilot Agent, Cursor, or OpenCode) into docs/transcripts/<slug>.md first."
        )
        raise SystemExit(2)
    print(f"Submission package ready: {result.out_dir}")
    if result.zip_path:
        print(f"Zip for submission: {result.zip_path}")


def cmd_skills_verify(args: argparse.Namespace) -> None:
    """Check course skill files against .agents/skills.lock.json."""
    from app.skill_integrity import format_report, verify

    result = verify()
    print(format_report(result))
    if not result.ok:
        raise SystemExit(1)


def cmd_usecase(args: argparse.Namespace) -> None:
    """Render docs/diagrams/use-case.json to a UML use-case PNG."""
    from app.usecase_diagram import render_usecase_png

    dest = render_usecase_png(
        spec_path=None if args.spec is None else Path(args.spec),
        output=None if args.output is None else Path(args.output),
    )
    print(f"Wrote {dest}")


def cmd_skills_lock(args: argparse.Namespace) -> None:
    """Rewrite the skill lockfile (course authors only)."""
    from app.skill_integrity import write_lock

    dest = write_lock()
    print(f"Wrote {dest}")


def cmd_users(args: argparse.Namespace) -> None:
    """List users currently in the database."""
    from sqlmodel import select

    from app.database import get_cli_session
    from app.models.user import User

    _ensure_models_loaded()
    with get_cli_session() as session:
        users = session.exec(select(User)).all()
        if not users:
            print("No users found. Run: python manage.py init")
            return
        for user in users:
            print(
                f"  id={user.id}  username={user.username}  "
                f"role={user.role}  email={user.email}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python manage.py",
        description="FastStarter Python CLI — init database, seed demo data, run the app.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help="Create DB tables and seed demo users (drops existing tables by default)",
    )
    p_init.add_argument(
        "--no-drop",
        dest="drop",
        action="store_false",
        help="Create tables without dropping existing ones",
    )
    p_init.add_argument(
        "--no-seed",
        dest="seed",
        action="store_false",
        help="Skip demo user seed after creating tables",
    )
    p_init.set_defaults(drop=True, seed=True, func=cmd_init)

    p_seed = sub.add_parser(
        "seed",
        help="Insert demo users only (idempotent; also runs as part of init)",
    )
    p_seed.set_defaults(func=cmd_seed)

    p_run = sub.add_parser("run", help="Start the web app (uvicorn)")
    p_run.add_argument("--host", default=None, help="Bind host")
    p_run.add_argument("--port", type=int, default=None, help="Bind port")
    reload_group = p_run.add_mutually_exclusive_group()
    reload_group.add_argument(
        "--reload", dest="reload", action="store_true", default=None, help="Enable auto-reload"
    )
    reload_group.add_argument(
        "--no-reload", dest="reload", action="store_false", help="Disable auto-reload"
    )
    p_run.set_defaults(func=cmd_run, reload=None)

    p_users = sub.add_parser("users", help="List users in the database")
    p_users.set_defaults(func=cmd_users)

    p_report = sub.add_parser(
        "report",
        help=(
            "Build submission package: merge docs/judge.md, package docs/transcripts/, "
            "write docs/report.pdf (Guide pulls chats + runs student-judge first)"
        ),
    )
    p_report.add_argument("--name", required=True, help="Student name (printed on the PDF cover)")
    p_report.add_argument("--id", dest="student_id", required=True, help="Student ID (PDF only)")
    p_report.add_argument("--src", default=None, help="Markdown path (default: docs/report.md)")
    p_report.add_argument("--output", default=None, help="PDF path (default: docs/report.pdf)")
    p_report.set_defaults(func=cmd_report)

    p_transcripts = sub.add_parser(
        "transcripts",
        help="Package agent-written docs/transcripts/*.md into INDEX + zip (no IDE scrape)",
    )
    p_transcripts.add_argument(
        "--no-zip",
        action="store_true",
        help="Skip writing docs/transcripts.zip",
    )
    p_transcripts.set_defaults(func=cmd_transcripts)

    p_usecase = sub.add_parser(
        "usecase",
        help="Render docs/diagrams/use-case.json to a UML use-case PNG",
    )
    p_usecase.add_argument("--spec", default=None, help="JSON spec (default: docs/diagrams/use-case.json)")
    p_usecase.add_argument("--output", default=None, help="PNG path (default: docs/diagrams/use-case.png)")
    p_usecase.set_defaults(func=cmd_usecase)

    p_skills_verify = sub.add_parser(
        "skills-verify",
        help="Check course skills against .agents/skills.lock.json",
    )
    p_skills_verify.set_defaults(func=cmd_skills_verify)

    p_skills_lock = sub.add_parser(
        "skills-lock",
        help="Rewrite .agents/skills.lock.json (course authors; needs FASTSTARTER_SKILLS_LOCK=1)",
    )
    p_skills_lock.set_defaults(func=cmd_skills_lock)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
