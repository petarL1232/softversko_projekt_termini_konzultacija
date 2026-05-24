from datetime import datetime, timedelta

from sqlmodel import Session, SQLModel, select

from app.database import engine
from app.models import ConsultationTerm, Office, Subject, User, UserRole

DEFAULT_PASSWORD_HASH = "seed-only-password-hash-not-for-production"


PROFESSORS = [
    {
        "first_name": "Juraj",
        "last_name": "Benić",
        "email": "jbenic@mathos.hr",
        "office_name": "soba 8 (prizemlje)",
        "capacity": 6,
    },
    {
        "first_name": "Luka",
        "last_name": "Borozan",
        "email": "lborozan@mathos.hr",
        "office_name": "soba 5 (prizemlje)",
        "capacity": 5,
    },
    {
        "first_name": "Krešimir",
        "last_name": "Burazin",
        "email": "kburazin@mathos.hr",
        "office_name": "soba 35 (prvi kat)",
        "capacity": 7,
    },
    {
        "first_name": "Rebeka",
        "last_name": "Čorić",
        "email": "rcoric@mathos.hr",
        "office_name": "soba 7 (prizemlje)",
        "capacity": 6,
    },
    {
        "first_name": "Mateja",
        "last_name": "Đumić",
        "email": "mdjumic@mathos.hr",
        "office_name": "soba 7 (prizemlje)",
        "capacity": 6,
    },
    {
        "first_name": "Dragana",
        "last_name": "Jankov Maširević",
        "email": "djankov@mathos.hr",
        "office_name": "soba 30 (prizemlje)",
        "capacity": 6,
    },
    {
        "first_name": "Mirela",
        "last_name": "Jukić Bokun",
        "email": "mirela@mathos.hr",
        "office_name": "soba 19 (prvi kat)",
        "capacity": 7,
    },
    {
        "first_name": "Tomislav",
        "last_name": "Marošević",
        "email": "tmarosev@mathos.hr",
        "office_name": "soba 25 (prvi kat)",
        "capacity": 5,
    },
    {
        "first_name": "Ivan",
        "last_name": "Matić",
        "email": "imatic@mathos.hr",
        "office_name": "soba 12 (prizemlje)",
        "capacity": 5,
    },
    {
        "first_name": "Domagoj",
        "last_name": "Matijević",
        "email": "domagoj@mathos.hr",
        "office_name": "soba 9 (prizemlje)",
        "capacity": 5,
    },
    {
        "first_name": "Jurica",
        "last_name": "Maltar",
        "email": "jmaltar@mathos.hr",
        "office_name": "soba 6 (prizemlje)",
        "capacity": 5,
    },
    {
        "first_name": "Ivan",
        "last_name": "Papić",
        "email": "ipapic@mathos.hr",
        "office_name": "soba 14 (prvi kat)",
        "capacity": 6,
    },
    {
        "first_name": "Kristian",
        "last_name": "Sabo",
        "email": "ksabo@mathos.hr",
        "office_name": "soba 18 (prizemlje)",
        "capacity": 6,
    },
    {
        "first_name": "Domagoj",
        "last_name": "Ševerdija",
        "email": "dseverdi@mathos.hr",
        "office_name": "soba 8 (prizemlje)",
        "capacity": 6,
    },
    {
        "first_name": "Ivan",
        "last_name": "Soldo",
        "email": "isoldo@mathos.hr",
        "office_name": "soba 19 (prvi kat)",
        "capacity": 7,
    },
    {
        "first_name": "Nenad",
        "last_name": "Šuvak",
        "email": "nsuvak@mathos.hr",
        "office_name": "soba 18 (prvi kat)",
        "capacity": 7,
    },
    {
        "first_name": "Zoran",
        "last_name": "Tomljanović",
        "email": "ztomljan@mathos.hr",
        "office_name": "soba 18 (prizemlje)",
        "capacity": 6,
    },
]


SUBJECTS = [
    {
        "code": "I044",
        "name": "Funkcijsko programiranje",
        "year": "I. godina",
        "semester": "zimski semestar",
        "professor_emails": ["dseverdi@mathos.hr", "lborozan@mathos.hr"],
        "professor_names": "Domagoj Ševerdija, Luka Borozan",
    },
    {
        "code": "M084",
        "name": "Diferencijalni račun",
        "year": "I. godina",
        "semester": "zimski semestar",
        "professor_emails": ["isoldo@mathos.hr"],
        "professor_names": "Ivan Soldo",
    },
    {
        "code": "M086",
        "name": "Linearna algebra I",
        "year": "I. godina",
        "semester": "zimski semestar",
        "professor_emails": ["ztomljan@mathos.hr"],
        "professor_names": "Zoran Tomljanović",
    },
    {
        "code": "I056",
        "name": "Uvod u računalnu znanost",
        "year": "I. godina",
        "semester": "zimski semestar",
        "professor_emails": ["domagoj@mathos.hr"],
        "professor_names": "Domagoj Matijević",
    },
    {
        "code": "I048",
        "name": "Objektno orijentirano programiranje",
        "year": "I. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["domagoj@mathos.hr"],
        "professor_names": "Domagoj Matijević",
    },
    {
        "code": "M088",
        "name": "Matematička logika u računalnoj znanosti",
        "year": "I. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["domagoj@mathos.hr", "lborozan@mathos.hr"],
        "professor_names": "Domagoj Matijević, Luka Borozan",
    },
    {
        "code": "M085",
        "name": "Integralni račun",
        "year": "I. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["isoldo@mathos.hr"],
        "professor_names": "Ivan Soldo",
    },
    {
        "code": "M087",
        "name": "Linearna algebra II",
        "year": "I. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["djankov@mathos.hr"],
        "professor_names": "Dragana Jankov Maširević",
    },
    {
        "code": "M091",
        "name": "Primijenjena matematika za računalnu znanost",
        "year": "II. godina",
        "semester": "zimski semestar",
        "professor_emails": ["djankov@mathos.hr", "mirela@mathos.hr"],
        "professor_names": "Dragana Jankov Maširević, Mirela Jukić Bokun",
    },
    {
        "code": "I053",
        "name": "Strukture podataka i algoritmi I",
        "year": "II. godina",
        "semester": "zimski semestar",
        "professor_emails": ["mdjumic@mathos.hr"],
        "professor_names": "Mateja Đumić",
    },
    {
        "code": "I045",
        "name": "Moderni računalni sustavi",
        "year": "II. godina",
        "semester": "zimski semestar",
        "professor_emails": ["domagoj@mathos.hr", "lborozan@mathos.hr"],
        "professor_names": "Domagoj Matijević, Luka Borozan",
    },
    {
        "code": "I046",
        "name": "Moderni sustavi baza podataka",
        "year": "II. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["mdjumic@mathos.hr"],
        "professor_names": "Mateja Đumić",
    },
    {
        "code": "I054",
        "name": "Strukture podataka i algoritmi II",
        "year": "II. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["dseverdi@mathos.hr"],
        "professor_names": "Domagoj Ševerdija",
    },
    {
        "code": "M097",
        "name": "Teorijske osnove računalne znanosti",
        "year": "II. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["rcoric@mathos.hr"],
        "professor_names": "Rebeka Čorić",
    },
    {
        "code": "I055",
        "name": "Ugrađeni sustavi",
        "year": "II./III. godina izborni",
        "semester": "zimski semestar",
        "professor_emails": ["jbenic@mathos.hr"],
        "professor_names": "Juraj Benić",
    },
    {
        "code": "M099",
        "name": "Vektorski prostori",
        "year": "II. godina izborni",
        "semester": "zimski semestar",
        "professor_emails": ["imatic@mathos.hr"],
        "professor_names": "Ivan Matić",
    },
    {
        "code": "I051",
        "name": "Računalno jezikoslovlje",
        "year": "II./III. godina izborni",
        "semester": "zimski semestar",
        "professor_emails": ["dseverdi@mathos.hr"],
        "professor_names": "Domagoj Ševerdija",
    },
    {
        "code": "I059",
        "name": "3D računalna grafika",
        "year": "II./III. godina izborni",
        "semester": "ljetni semestar",
        "professor_emails": ["dseverdi@mathos.hr"],
        "professor_names": "Domagoj Ševerdija",
    },
    {
        "code": "M062",
        "name": "Primjene diferencijalnog i integralnog računa I",
        "year": "II. godina izborni",
        "semester": "ljetni semestar",
        "professor_emails": ["tmarosev@mathos.hr"],
        "professor_names": "Tomislav Marošević",
    },
    {
        "code": "I057",
        "name": "Web programiranje",
        "year": "III. godina",
        "semester": "zimski semestar",
        "professor_emails": ["ztomljan@mathos.hr", "jmaltar@mathos.hr"],
        "professor_names": "Zoran Tomljanović, Jurica Maltar",
    },
    {
        "code": "M089",
        "name": "Numerička matematika",
        "year": "III. godina",
        "semester": "zimski semestar",
        "professor_emails": ["ksabo@mathos.hr"],
        "professor_names": "Kristian Sabo",
    },
    {
        "code": "M090",
        "name": "Obične diferencijalne jednadžbe",
        "year": "III. godina",
        "semester": "zimski semestar",
        "professor_emails": ["kburazin@mathos.hr"],
        "professor_names": "Krešimir Burazin",
    },
    {
        "code": "I058",
        "name": "Završni praktični projekt",
        "year": "III. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["domagoj@mathos.hr"],
        "professor_names": "Domagoj Matijević",
    },
    {
        "code": "M096",
        "name": "Strojno učenje",
        "year": "III. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["domagoj@mathos.hr", "ksabo@mathos.hr"],
        "professor_names": "Domagoj Matijević, Kristian Sabo",
    },
    {
        "code": "I052",
        "name": "Softversko inženjerstvo",
        "year": "III. godina",
        "semester": "ljetni semestar",
        "professor_emails": ["domagoj@mathos.hr"],
        "professor_names": "Domagoj Matijević",
    },
    {
        "code": "M094",
        "name": "Realna analiza",
        "year": "III. godina izborni",
        "semester": "zimski semestar",
        "professor_emails": ["djankov@mathos.hr"],
        "professor_names": "Dragana Jankov Maširević",
    },
    {
        "code": "Z013",
        "name": "Stručna praksa",
        "year": "III. godina izborni",
        "semester": "zimski semestar",
        "professor_emails": ["domagoj@mathos.hr", "nsuvak@mathos.hr"],
        "professor_names": "Domagoj Matijević, Nenad Šuvak",
    },
    {
        "code": "M083",
        "name": "Algebra",
        "year": "III. godina izborni",
        "semester": "ljetni semestar",
        "professor_emails": ["imatic@mathos.hr"],
        "professor_names": "Ivan Matić",
    },
    {
        "code": "M095",
        "name": "Statistički praktikum",
        "year": "III. godina izborni",
        "semester": "ljetni semestar",
        "professor_emails": ["ipapic@mathos.hr"],
        "professor_names": "Ivan Papić",
    },
    {
        "code": "M092",
        "name": "Osnove teorije upravljanja s primjenama",
        "year": "III. godina izborni",
        "semester": "ljetni semestar",
        "professor_emails": ["ztomljan@mathos.hr"],
        "professor_names": "Zoran Tomljanović",
    },
]


def build_subject_description(subject_data: dict) -> str:
    return (
        f"{subject_data['code']} | {subject_data['year']} | "
        f"{subject_data['semester']} | Nastavnici: "
        f"{subject_data['professor_names']}"
    )


def get_or_create_office(session: Session, office_name: str, capacity: int) -> Office:
    office = session.exec(
        select(Office).where(Office.office_name == office_name)
    ).first()

    if office is not None:
        return office

    office = Office(office_name=office_name, capacity=capacity)
    session.add(office)
    session.commit()
    session.refresh(office)
    return office


def get_or_create_professor(
    session: Session,
    first_name: str,
    last_name: str,
    email: str,
    office: Office,
) -> User:
    professor = session.exec(select(User).where(User.email == email)).first()

    if professor is not None:
        professor.role = UserRole.PROFESSOR
        professor.office_id = office.office_id
        session.add(professor)
        session.commit()
        session.refresh(professor)
        return professor

    professor = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=DEFAULT_PASSWORD_HASH,
        role=UserRole.PROFESSOR,
        office_id=office.office_id,
    )
    session.add(professor)
    session.commit()
    session.refresh(professor)
    return professor


def get_or_create_subject(session: Session, name: str, description: str) -> Subject:
    subject = session.exec(select(Subject).where(Subject.name == name)).first()

    if subject is not None:
        subject.description = description
        session.add(subject)
        session.commit()
        session.refresh(subject)
        return subject

    subject = Subject(name=name, description=description)
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def seed_professors_and_offices(session: Session) -> None:
    for professor_data in PROFESSORS:
        office = get_or_create_office(
            session=session,
            office_name=professor_data["office_name"],
            capacity=professor_data["capacity"],
        )
        get_or_create_professor(
            session=session,
            first_name=professor_data["first_name"],
            last_name=professor_data["last_name"],
            email=professor_data["email"],
            office=office,
        )


def seed_subjects(session: Session) -> None:
    for subject_data in SUBJECTS:
        get_or_create_subject(
            session=session,
            name=subject_data["name"],
            description=build_subject_description(subject_data),
        )


def consultation_start_time(slot_index: int) -> datetime:
    """Return deterministic, readable test times for generated terms."""

    base_start = datetime(2026, 6, 2, 9, 0)
    day_offset = slot_index // 4
    hour_offset = (slot_index % 4) * 2
    return base_start + timedelta(days=day_offset, hours=hour_offset)


def seed_consultation_terms(session: Session) -> None:
    slot_index = 0

    for subject_data in SUBJECTS:
        subject = session.exec(
            select(Subject).where(Subject.name == subject_data["name"])
        ).first()

        if subject is None or subject.subject_id is None:
            continue

        for professor_email in subject_data["professor_emails"]:
            professor = session.exec(
                select(User).where(User.email == professor_email)
            ).first()

            if professor is None or professor.user_id is None:
                continue

            existing_term = session.exec(
                select(ConsultationTerm).where(
                    ConsultationTerm.professor_id == professor.user_id,
                    ConsultationTerm.subject_id == subject.subject_id,
                )
            ).first()

            if existing_term is not None:
                continue

            start_time = consultation_start_time(slot_index)
            end_time = start_time + timedelta(hours=1)

            session.add(
                ConsultationTerm(
                    professor_id=professor.user_id,
                    subject_id=subject.subject_id,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
            slot_index += 1

    session.commit()


def seed_mathos_full_data() -> None:
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_professors_and_offices(session)
        seed_subjects(session)
        seed_consultation_terms(session)

    print("MATHOS seed finished.")
    print(f"Professors: {len(PROFESSORS)}")
    print(f"Seeded subjects: {len(SUBJECTS)}")


if __name__ == "__main__":
    seed_mathos_full_data()