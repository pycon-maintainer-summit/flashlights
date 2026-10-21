"""Demo preset: the PyCon US Maintainer Summit, from its public site
(https://pycon-maintainer-summit.github.io/): editions 2019 to 2027, the
2026 program in Room 201A, its organizers and speakers, invented volunteers,
and a few registrations imported from a PyCon US-style CSV. In person, the
team records, no community chat. People's emails are invented (example.org).

Loaded by ``manage.py load_preset``; kept out of the Flashlights repository
because it is a real community's data. All passwords: password123.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils import timezone

from affiliations.models import Affiliation, AffiliationKind
from portal.models import ChatPlatform, Conference, Venue
from portal_account.handles import adopt_role_handles
from portal_account.models import PortalProfile
from speakers.checklists import complete_item
from speakers.constants import (
    OPEN_ITEM_STATUSES,
    Delivery,
    EventFormat,
    Recordings,
    RoomKind,
)
from speakers.lifecycle import confirm_session_if_ready
from speakers.models import (
    Handbook,
    Presenter,
    PublishedSlot,
    Room,
    ScheduleSlot,
    Session,
    SessionPresenter,
    SessionType,
    SpeakerSettings,
)
from speakers.program_types import presenter_role, seed_program_types, session_type
from speakers.seeds import seed_checklists, seed_new_edition
from speakers.services import accept_invitation, send_invitation
from ticketing.models import TicketingSettings
from ticketing.sync import import_csv
from volunteer.constants import ApplicationStatus, Region
from volunteer.models import Team, VolunteerProfile
from volunteer.permission_presets import ORGANIZERS as ORGANIZERS_TEAM
from volunteer.permission_presets import PRESETS, permissions_for

PASSWORD = "password123"
SITE = "https://pycon-maintainer-summit.github.io"
PACIFIC = ZoneInfo("America/Los_Angeles")


def add_summit_types(edition):
    """The summit's own types, next to the defaults: the BoF and the
    roundtables."""
    moderator = presenter_role(edition, "MODERATOR")
    host = presenter_role(edition, "HOST")
    for code, name, content, minutes, role_rows, order in (
        ("BOF", "Birds of a feather", True, 60, [moderator, host], 45),
        ("ROUNDTABLE", "Roundtable discussions", False, 75, [host], 115),
    ):
        row, created = SessionType.objects.get_or_create(
            conference=edition,
            code=code,
            defaults={
                "name": name,
                "is_content": content,
                "default_duration_minutes": minutes,
                "default_delivery": Delivery.LIVE,
                "spans_all_rooms": not content,
                "sort_order": order,
                "default_role": role_rows[0],
            },
        )
        if created:
            row.roles.set(role_rows)


def run(stdout):
    def print(*parts):
        stdout.write(" ".join(str(p) for p in parts))

    Site.objects.update_or_create(
        pk=1,
        defaults={"domain": "127.0.0.1:8002", "name": "PyCon US Maintainer Summit"},
    )

    # ---------------------------------------------------------------- editions
    EDITIONS = [
        # year, slug, conference date, end date, banner
        (2019, "2019-pycon-us", date(2019, 5, 4), None),
        (2021, "2021-pycon-us", date(2021, 5, 12), date(2021, 5, 13)),
        (2022, "2022-pycon-us", date(2022, 4, 29), None),
        (2023, "2023-pycon-us", date(2023, 4, 21), None),
        (2024, "2024-pycon-us", date(2024, 5, 17), None),
        (2025, "2025-pycon-us", date(2025, 5, 16), None),
        (2026, "2026-pycon-us", date(2026, 5, 16), None),
        (2027, "2027-pycon-us", None, None),
    ]
    editions = {}
    for year, slug, day, end in EDITIONS:
        editions[year] = Conference.objects.create(
            year=year,
            name=f"PyCon US Maintainer Summit {year}",
            slug=slug,
            is_active=False,
            conference_date=day,
            start_date=day,
            end_date=end or day,
            coc_url=f"{SITE}/docs/code-of-conduct/",
            schedule_url=f"{SITE}/events/{slug}/topics" if day else None,
            volunteer_application_open=False,
            sponsorship_open=False,
            accepting_donations=False,
        )
    summit = editions[2026]
    summit.is_active = True
    summit.volunteer_application_open = True
    summit.save()

    # ------------------------------------------------------------------ people
    def make_user(username, first, last, email, staff=False, superuser=False):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first,
                "last_name": last,
                "email": email,
                "is_staff": staff,
                "is_superuser": superuser,
            },
        )
        user.set_password(PASSWORD)
        user.save()
        PortalProfile.objects.get_or_create(
            user=user, defaults={"coc_agreement": True, "tos_agreement": True}
        )
        return user

    ORGANIZERS = [
        # username, first, last, superuser, affiliations [(kind, name, url)]
        (
            "mariatta",
            "Mariatta",
            "Wijaya",
            True,
            [
                (
                    AffiliationKind.PROJECT,
                    "CPython",
                    "https://github.com/python/cpython",
                ),
                (AffiliationKind.COMMUNITY, "PyLadies Vancouver", ""),
            ],
        ),
        (
            "inessa",
            "Inessa",
            "Pawson",
            False,
            [
                (AffiliationKind.PROJECT, "NumPy", "https://numpy.org"),
                (AffiliationKind.WORKPLACE, "OpenTeams", "https://openteams.com"),
            ],
        ),
        (
            "elaine",
            "Elaine",
            "Wong",
            False,
            [
                (AffiliationKind.COMMUNITY, "PyLadies Toronto", ""),
                (AffiliationKind.COMMUNITY, "Python Software Foundation board", ""),
                (AffiliationKind.PROJECT, "csvconf", ""),
            ],
        ),
        (
            "leah",
            "Leah",
            "Wasser",
            False,
            [
                (AffiliationKind.COMMUNITY, "pyOpenSci", "https://www.pyopensci.org"),
                (AffiliationKind.PROJECT, "all-contributors", ""),
                (AffiliationKind.PROJECT, "stravalib", ""),
            ],
        ),
    ]
    organizers = {}
    for username, first, last, superuser, rows in ORGANIZERS:
        user = make_user(
            username,
            first,
            last,
            f"{username}@example.org",
            staff=True,
            superuser=superuser,
        )
        for order, (kind, name, url) in enumerate(rows):
            Affiliation.objects.get_or_create(
                user=user, kind=kind, name=name, defaults={"url": url, "order": order}
            )
        organizers[username] = user

    # --------------------------------------------------------------- volunteers
    TEAMS = [
        (
            "Program",
            "Reviews proposals and builds the day's schedule",
            True,
            ["inessa"],
        ),
        (
            "Roundtables",
            "Chooses the roundtable topics and facilitates them",
            True,
            ["leah"],
        ),
        (
            "Communications",
            "Website, social media and the attendee emails",
            True,
            ["elaine"],
        ),
        (
            "Day-of logistics",
            "Room, signage, registration and timekeeping",
            False,
            ["mariatta"],
        ),
    ]
    # Team leads are volunteer profiles: the organizers have approved ones.
    lead_profiles = {}
    for username, user in organizers.items():
        lead_profiles[username], _ = VolunteerProfile.objects.get_or_create(
            user=user,
            conference=summit,
            defaults={
                "application_status": ApplicationStatus.APPROVED,
                "region": Region.NORTH_AMERICA,
                "availability_hours_per_week": 6,
                "github_username": username,
                "discord_username": username,
            },
        )
    teams = {}
    for name, description, open_, leads in TEAMS:
        team, _ = Team.objects.get_or_create(
            conference=summit,
            short_name=name,
            defaults={"description": description, "open_to_new_members": open_},
        )
        team.team_leads.set([lead_profiles[u] for u in leads])
        for username in leads:
            lead_profiles[username].teams.add(team)
        teams[name] = team

    VOLUNTEERS = [
        # username, first, last, status, region, hours, teams, github
        (
            "priya_n",
            "Priya",
            "Natarajan",
            ApplicationStatus.APPROVED,
            Region.NORTH_AMERICA,
            4,
            ["Program"],
            "priya-n",
        ),
        (
            "tomas_k",
            "Tomas",
            "Kowalski",
            ApplicationStatus.APPROVED,
            Region.EUROPE,
            3,
            ["Roundtables"],
            "tomask",
        ),
        (
            "yuki_o",
            "Yuki",
            "Okada",
            ApplicationStatus.APPROVED,
            Region.ASIA,
            2,
            ["Communications"],
            "yukio",
        ),
        (
            "dani_r",
            "Dani",
            "Reyes",
            ApplicationStatus.PENDING,
            Region.NORTH_AMERICA,
            5,
            [],
            "danireyes",
        ),
        (
            "amara_o",
            "Amara",
            "Okafor",
            ApplicationStatus.PENDING,
            Region.AFRICA,
            2,
            [],
            "",
        ),
        (
            "jonas_b",
            "Jonas",
            "Berg",
            ApplicationStatus.WAITLISTED,
            Region.EUROPE,
            1,
            [],
            "jberg",
        ),
        (
            "noor_h",
            "Noor",
            "Haddad",
            ApplicationStatus.APPROVED,
            Region.NORTH_AMERICA,
            3,
            ["Day-of logistics"],
            "noorh",
        ),
    ]
    for (
        username,
        first,
        last,
        status,
        region,
        hours,
        team_names,
        gh,
    ) in VOLUNTEERS:
        user = make_user(username, first, last, f"{username}@example.org")
        profile, _ = VolunteerProfile.objects.get_or_create(
            user=user,
            conference=summit,
            defaults={
                "application_status": status,
                "region": region,
                "availability_hours_per_week": hours,
                "github_username": gh,
                "discord_username": username,
            },
        )
        profile.teams.set([teams[t] for t in team_names])

    # ---------------------------------------------------------- speaker module
    # In person from the first save, which seeds the session types: an
    # in-person edition gets no pre-recorded performance.
    settings_row, _ = SpeakerSettings.objects.get_or_create(
        conference=summit,
        defaults={
            "event_format": EventFormat.IN_PERSON,
            "recordings": Recordings.TEAM,
        },
    )
    settings_row.speaker_module_enabled = True
    settings_row.conference_timezone = "America/Los_Angeles"
    # The summit has only its Google Group: replies go there through the
    # edition's reply-to address, so the speaker team address stays blank.
    settings_row.organizers_email = ""
    settings_row.proposals_open = False
    settings_row.media_for_speakers = False
    settings_row.auto_transcribe = False
    settings_row.proposals_intro_md = (
        "The summit is an afternoon-to-evening program of talks, lightning talks "
        "and roundtables for people who maintain open source Python projects. "
        f"Read the [call for proposals guide]({SITE}/docs/cfp-guide/) before you "
        "submit. The 2027 call opens on November 16."
    )
    settings_row.save()
    seed_program_types(summit)
    seed_checklists(summit)

    # Two types of the summit's own: the BoF and the roundtables.
    add_summit_types(summit)

    for key, title, path in (
        ("speaker", "Call for proposals guide", "docs/cfp-guide/"),
        ("attendee", "Attendee guide", "docs/attendee-guide/"),
    ):
        if Handbook.current(summit, key) is None:
            Handbook.objects.create(
                conference=summit,
                key=key,
                title=title,
                url=f"{SITE}/{path}",
                version=Handbook.next_version(summit, key),
            ).publish()

    room, _ = Room.objects.get_or_create(
        conference=summit,
        name="Room 201A",
        defaults={
            "kind": RoomKind.STAGE,
            "url": "https://us.pycon.org/2026/events/maintainers-summit/",
        },
    )

    # ----------------------------------------------------------------- program
    # title, type code, start (Pacific, h:mm), minutes, summary, presenters
    # [(name, role code)]
    PROGRAM = [
        (
            "Opening remarks",
            "OPENING",
            "10:30",
            5,
            "Welcome and the shape of the day from the summit organizers.",
            [
                ("Inessa Pawson", "HOST"),
                ("Leah Wasser", "HOST"),
                ("Mariatta Wijaya", "HOST"),
            ],
        ),
        (
            "Beyond Rebranding: Sustaining the Nebari Community through Strategic "
            "Pivots and an AI Evolution",
            "TALK",
            "10:35",
            20,
            "Lessons from sustaining the Nebari community through strategic "
            "pivots and the rise of AI.",
            [("Dharhas Pothina", "PRESENTER")],
        ),
        (
            "Excited Developer Syndrome",
            "TALK",
            "10:55",
            20,
            "Strategies for maximizing impact through systems thinking.",
            [("Evan Kohilas", "PRESENTER")],
        ),
        (
            "GenAI in Open Source: Tool, Threat, or Turning Point?",
            "BOF",
            "11:15",
            60,
            "An open discussion on how generative AI is changing open source "
            "maintenance, for better and for worse.",
            [("Mariatta Wijaya", "MODERATOR")],
        ),
        ("Lunch", "BREAK", "12:15", 75, "", []),
        (
            "And Now for Something Completely Legitimate",
            "TALK",
            "13:30",
            20,
            "The legitimacy and trust questions facing open source today, seen "
            "from PyPI.",
            [("Mike Fiedler", "PRESENTER")],
        ),
        (
            "Building Compatible Systems: When You Don't Own Your APIs",
            "TALK",
            "13:50",
            20,
            "Strategies for building and maintaining libraries that depend on "
            "APIs you do not control.",
            [("Holden Karau", "PRESENTER"), ("Devin Petersohn", "PRESENTER")],
        ),
        (
            "How Translations Work",
            "TALK",
            "14:10",
            20,
            "An inside look at translation workflows for Python open source "
            "projects.",
            [("Felipe Moreno", "PRESENTER")],
        ),
        (
            "Tools Track",
            "LIGHTNING",
            "14:30",
            75,
            "A series of lightning talks on tools that help maintainers do their "
            "work.",
            [
                ("Sarah Kaiser", "PRESENTER"),
                ("Avik Basu", "PRESENTER"),
                ("Leah Wasser", "PRESENTER"),
                ("Zanie Blue", "PRESENTER"),
                ("Cameron Riddell", "PRESENTER"),
                ("Peyton Murray", "PRESENTER"),
                ("Cary Hawkins", "PRESENTER"),
            ],
        ),
        ("Afternoon break", "BREAK", "15:45", 30, "", []),
        (
            "Roundtable discussions",
            "ROUNDTABLE",
            "16:15",
            75,
            "Small-group discussions on topics chosen by the people in the room.",
            [("Leah Wasser", "HOST"), ("Inessa Pawson", "HOST")],
        ),
        (
            "Closing remarks",
            "CLOSING",
            "17:30",
            15,
            "Wrap-up and reflections on the day.",
            [("Mariatta Wijaya", "HOST")],
        ),
    ]

    # Speakers as the site lists them: affiliations where it gives one, the
    # rest a one-liner. Emails are invented.
    SPEAKERS = {
        "Avik Basu": ("", "Lightning talk speaker on the Tools Track."),
        "Cameron Riddell": ("", "Lightning talk speaker on the Tools Track."),
        "Cary Hawkins": ("", "Lightning talk speaker on the Tools Track."),
        "Devin Petersohn": ("", "Co-presenter on building compatible systems."),
        "Dharhas Pothina": ("Nebari", "Speaker on sustaining the Nebari community."),
        "Evan Kohilas": ("", "Contributor experience."),
        "Felipe Moreno": ("", "Speaker on translation tooling and processes."),
        "Holden Karau": (
            "",
            "Open source contributor and speaker on building compatible systems.",
        ),
        "Inessa Pawson": (
            "NumPy, OpenTeams",
            "Co-organizer of the PyCon US Maintainer Summit. Contributor to NumPy "
            "and team member at OpenTeams.",
        ),
        "Leah Wasser": (
            "pyOpenSci",
            "Co-organizer of the PyCon US Maintainer Summit. Founder of pyOpenSci.",
        ),
        "Mariatta Wijaya": (
            "PyLadies, CPython",
            "Co-organizer of the PyCon US Maintainer Summit. CPython core "
            "developer and PyLadies organizer.",
        ),
        "Mike Fiedler": ("PyPI", "PyPI safety and security."),
        "Peyton Murray": ("", "Lightning talk speaker on the Tools Track."),
        "Sarah Kaiser": ("", "Lightning talk speaker on the Tools Track."),
        "Zanie Blue": ("", "Lightning talk speaker on the Tools Track."),
    }
    ORGANIZER_USERS = {
        "Inessa Pawson": "inessa",
        "Leah Wasser": "leah",
        "Mariatta Wijaya": "mariatta",
    }

    def email_for(name):
        return name.lower().replace(" ", ".") + "@example.org"

    presenters = {}
    for name, (affiliation, bio) in SPEAKERS.items():
        username = ORGANIZER_USERS.get(name)
        presenter, _ = Presenter.objects.get_or_create(
            conference=summit,
            email=email_for(name),
            defaults={
                "display_name": name,
                "timezone": "America/Los_Angeles",
                "bio_md": bio + (f"\n\n{affiliation}" if affiliation else ""),
                "location": affiliation,
                "liaison": organizers["inessa"],
                "user": organizers[username] if username else None,
                "is_public": True,
            },
        )
        presenters[name] = presenter

    sessions = {}
    for title, code, start, minutes, summary, links in PROGRAM:
        session, _ = Session.objects.get_or_create(
            conference=summit,
            title=title,
            defaults={
                "kind": session_type(summit, code),
                "delivery": Delivery.LIVE,
                "summary_md": summary,
                "language": "en",
                "duration_minutes": minutes,
            },
        )
        for order, (name, role_code) in enumerate(links):
            SessionPresenter.objects.get_or_create(
                session=session,
                presenter=presenters[name],
                defaults={"role": presenter_role(summit, role_code), "order": order},
            )
        sessions[title] = session

    # Every speaker was invited and accepted; the required items are done.
    for name, presenter in presenters.items():
        invitation = presenter.invitations.first()
        if invitation is None:
            invitation = presenter.invitations.create(
                message_md=(
                    "We would love to have you at the PyCon US Maintainer Summit "
                    "on Saturday, May 16 in Long Beach."
                ),
                invited_by=organizers["inessa"],
            )
            send_invitation(invitation, actor=organizers["inessa"])
        if invitation.accepted_at is None:
            accept_invitation(invitation)
            presenter.refresh_from_db()
        if presenter.user_id and not presenter.user.has_usable_password():
            presenter.user.set_password(PASSWORD)
            presenter.user.save()
        PortalProfile.objects.get_or_create(
            user=presenter.user, defaults={"coc_agreement": True, "tos_agreement": True}
        )
        blocking = presenter.checklist_items.filter(
            is_required=True,
            status__in=OPEN_ITEM_STATUSES,
            auto_complete_rule="",
            is_waiting=False,
        )
        for item in blocking:
            complete_item(item, actor=presenter.user)
        for session in Session.objects.filter(session_presenters__presenter=presenter):
            confirm_session_if_ready(session)

    for title, session in sessions.items():
        session.refresh_from_db()
        if session.status == "DRAFT" and not session.is_content:
            session.confirm()

    # The schedule, published: Pacific time on the day.
    for title, code, start, minutes, summary, links in PROGRAM:
        session = sessions[title]
        session.refresh_from_db()
        hour, minute = (int(part) for part in start.split(":"))
        start_utc = datetime(2026, 5, 16, hour, minute, tzinfo=PACIFIC).astimezone(
            ZoneInfo("UTC")
        )
        slot, _ = ScheduleSlot.objects.get_or_create(
            session=session,
            defaults={
                "room": None if session.kind.spans_all_rooms else room,
                "start_utc": start_utc,
                "end_utc": start_utc + timedelta(minutes=minutes),
            },
        )
        PublishedSlot.objects.get_or_create(
            session=session,
            defaults={
                "room": slot.room,
                "start_utc": slot.start_utc,
                "end_utc": slot.end_utc,
                "published_at": timezone.now(),
            },
        )
        session.refresh_from_db()
        if session.status == "CONFIRMED":
            session.schedule()
        if session.status == "SCHEDULED":
            session.publish()

    print("Sessions:")
    for session in Session.objects.filter(conference=summit).order_by(
        "published_slot__start_utc"
    ):
        print(f"  {session.status:10} {session.title}")
    print("Sign in with password", PASSWORD)
    for username in ("mariatta", "inessa", "elaine", "leah", "priya_n", "dani_r"):
        print(" ", username)
    print(
        "  speakers: username is the email's local part, e.g.",
        User.objects.get(email=email_for("Mike Fiedler")).username,
    )

    # ------------------------------------------- decisions 0012 and 0013 since

    center, _ = Venue.objects.update_or_create(
        name="Long Beach Convention & Entertainment Center",
        defaults={
            "address": "300 E Ocean Blvd\nLong Beach, CA 90802",
            "url": "https://www.longbeachcc.com/",
        },
    )
    for year in (2026, 2027):
        edition = editions[year]
        # The rooms already made are the center's, so picking the venue
        # below adopts them rather than adding a lane named after it.
        Room.objects.filter(conference=edition, venue=None).update(venue=center)
        edition.venue = center
        edition.chat_platform = ChatPlatform.NONE
        edition.reply_to_email = "maintainer-pyconus@googlegroups.com"
        edition.save()
        # Format and recordings on creation: the row's first save seeds the
        # edition's session types, and an in-person edition has no
        # pre-recorded ones.
        row, _ = SpeakerSettings.objects.get_or_create(
            conference=edition,
            defaults={
                "event_format": EventFormat.IN_PERSON,
                "recordings": Recordings.TEAM,
            },
        )
        row.event_format = EventFormat.IN_PERSON
        row.recordings = Recordings.TEAM
        row.conference_timezone = "America/Los_Angeles"
        row.save()
    add_summit_types(editions[2027])
    SpeakerSettings.objects.filter(conference=summit).update(
        program_visibility="PUBLISHED"
    )
    ticketing, _ = TicketingSettings.objects.update_or_create(
        conference=summit,
        defaults={
            "provider": "CSV",
            "api_token": "",
            # PyCon US exports the name in two columns.
            "csv_columns": {"email": "Email", "name": "First Name + Last Name"},
        },
    )
    registrants = """First Name,Last Name,Email,Affiliation
    Mike,Fiedler,mike.fiedler@example.org,PyPI
    Holden,Karau,holden.karau@example.org,
    Dharhas,Pothina,dharhas.pothina@example.org,Nebari
    Priya,Natarajan,priya_n@example.org,
    """
    result = import_csv(ticketing, registrants)
    print(f"Imported {result.imported} registrant(s) from a PyCon US-style CSV.")

    # ------------------------------------------------------- 2027, the active one
    # 2026 has happened; 2027 is the edition being prepared, with its call
    # for proposals not open yet. Its speaker module is on, so it has the
    # default checklists, the summit's types and its intro.
    upcoming = editions[2027]
    upcoming.is_active = True
    upcoming.banner_text = "The 2027 call for proposals opens November 16."
    upcoming.save()
    SpeakerSettings.objects.filter(conference=upcoming).update(
        speaker_module_enabled=True,
        proposals_open=False,
        organizers_email="",
        proposals_intro_md=settings_row.proposals_intro_md,
    )
    seed_new_edition(upcoming)

    # Access comes from the active edition's teams (decision 0014): the four
    # organizers run 2027 through the Organizers team, Mariatta leading and
    # the only superuser; Priya reviews proposals without running the rest.
    def preset_team(name, open_=False):
        team, created = Team.objects.get_or_create(
            conference=upcoming,
            short_name=name,
            defaults={"description": name, "open_to_new_members": open_},
        )
        if created:
            team.permissions.set(permissions_for(PRESETS[name].members))
            team.lead_permissions.set(permissions_for(PRESETS[name].leads))
        return team

    def approved_2027(user):
        profile, _ = VolunteerProfile.objects.get_or_create(
            user=user,
            conference=upcoming,
            defaults={
                "application_status": ApplicationStatus.APPROVED,
                "availability_hours_per_week": 4,
                "discord_username": user.username,
            },
        )
        return profile

    organizers_team = preset_team(ORGANIZERS_TEAM)
    for username, user in organizers.items():
        profile = approved_2027(user)
        profile.teams.add(organizers_team)
        if user.is_superuser:
            organizers_team.team_leads.add(profile)
    reviewers = preset_team("Proposal reviewers", open_=True)
    approved_2027(User.objects.get(username="priya_n")).teams.add(reviewers)
    # Noor films the day and publishes the videos without running the
    # program: the Published video card on each session page is theirs.
    recordings_team = preset_team("Recordings")
    approved_2027(User.objects.get(username="noor_h")).teams.add(recordings_team)
    print("Active edition:", upcoming.name)
    print("  Organizers team:", ", ".join(sorted(organizers)))
    print("  Proposal reviewers team: priya_n")
    print("  Recordings team: noor_h")

    # The handles typed on the rows above become each person's own record
    # (portal_account.Handle), as the migration does for a live database.
    for user in User.objects.all():
        adopt_role_handles(user)
