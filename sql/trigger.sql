-- PostgreSQL rules adapted to the existing SQLModel structure.
-- Safe to run multiple times.
-- We keep the current Python models as the source of truth.
-- Role comparisons use lower(role::text), so they work whether PostgreSQL
-- stores enum labels as ADMIN/PROFESSOR/STUDENT or values as admin/professor/student.

DROP VIEW IF EXISTS consultation_overview;

DROP TRIGGER IF EXISTS trg_validate_user_office ON users;
DROP TRIGGER IF EXISTS trg_validate_consultation_term ON consultation_terms;
DROP TRIGGER IF EXISTS trg_validate_term_registration ON term_registrations;

DROP FUNCTION IF EXISTS validate_user_office();
DROP FUNCTION IF EXISTS validate_consultation_term();
DROP FUNCTION IF EXISTS validate_term_registration();

DROP INDEX IF EXISTS ux_term_registration_student;
ALTER TABLE term_registrations
DROP CONSTRAINT IF EXISTS unique_student_term;


CREATE OR REPLACE FUNCTION validate_user_office()
RETURNS trigger AS $$
BEGIN
    IF lower(NEW.role::text) = 'professor' AND NEW.office_id IS NULL THEN
        RAISE EXCEPTION 'Professor must have an office.';
    END IF;

    IF lower(NEW.role::text) IN ('admin', 'student') AND NEW.office_id IS NOT NULL THEN
        RAISE EXCEPTION 'Only professors can have an office.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_user_office
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION validate_user_office();


CREATE OR REPLACE FUNCTION validate_consultation_term()
RETURNS trigger AS $$
DECLARE
    professor_role text;
BEGIN
    IF NEW.start_time >= NEW.end_time THEN
        RAISE EXCEPTION 'Consultation term start_time must be before end_time.';
    END IF;

    SELECT lower(role::text)
    INTO professor_role
    FROM users
    WHERE user_id = NEW.professor_id;

    IF professor_role IS NULL THEN
        RAISE EXCEPTION 'Professor does not exist.';
    END IF;

    IF professor_role <> 'professor' THEN
        RAISE EXCEPTION 'Only professor users can own consultation terms.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_consultation_term
BEFORE INSERT OR UPDATE ON consultation_terms
FOR EACH ROW
EXECUTE FUNCTION validate_consultation_term();


CREATE UNIQUE INDEX IF NOT EXISTS ux_term_registration_student
ON term_registrations(term_id, student_id);


CREATE OR REPLACE FUNCTION validate_term_registration()
RETURNS trigger AS $$
DECLARE
    student_role text;
    office_capacity integer;
    current_count integer;
BEGIN
    SELECT lower(role::text)
    INTO student_role
    FROM users
    WHERE user_id = NEW.student_id;

    IF student_role IS NULL THEN
        RAISE EXCEPTION 'Student does not exist.';
    END IF;

    IF student_role <> 'student' THEN
        RAISE EXCEPTION 'Only student users can register for terms.';
    END IF;

    SELECT o.capacity
    INTO office_capacity
    FROM consultation_terms ct
    JOIN users professor ON professor.user_id = ct.professor_id
    JOIN offices o ON o.office_id = professor.office_id
    WHERE ct.term_id = NEW.term_id;

    IF office_capacity IS NULL THEN
        RAISE EXCEPTION 'Term capacity is not available.';
    END IF;

    SELECT COUNT(*)
    INTO current_count
    FROM term_registrations
    WHERE term_id = NEW.term_id;

    IF current_count >= office_capacity THEN
        RAISE EXCEPTION 'Consultation term is full.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_term_registration
BEFORE INSERT ON term_registrations
FOR EACH ROW
EXECUTE FUNCTION validate_term_registration();


CREATE OR REPLACE VIEW consultation_overview AS
SELECT
    ct.term_id,
    ct.professor_id,
    CONCAT(professor.first_name, ' ', professor.last_name) AS professor_name,
    ct.subject_id,
    s.name AS subject_name,
    ct.start_time,
    ct.end_time,
    o.office_id,
    o.office_name,
    o.capacity,
    COUNT(tr.registration_id)::integer AS registered_students,
    GREATEST(o.capacity - COUNT(tr.registration_id)::integer, 0) AS free_places
FROM consultation_terms ct
JOIN users professor ON professor.user_id = ct.professor_id
JOIN subjects s ON s.subject_id = ct.subject_id
JOIN offices o ON o.office_id = professor.office_id
LEFT JOIN term_registrations tr ON tr.term_id = ct.term_id
GROUP BY
    ct.term_id,
    ct.professor_id,
    professor.first_name,
    professor.last_name,
    ct.subject_id,
    s.name,
    ct.start_time,
    ct.end_time,
    o.office_id,
    o.office_name,
    o.capacity;
