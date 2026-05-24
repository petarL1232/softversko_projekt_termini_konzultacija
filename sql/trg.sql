
CREATE OR REPLACE FUNCTION term_creation_validation()
RETURNS TRIGGER AS $$
BEGIN

    IF (
        SELECT role
        FROM users
        WHERE user_id = NEW.professor_id
    ) <> 'professor' THEN

        RAISE EXCEPTION
            'Profesor mora napraviti termin.';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_term_creation_validation
BEFORE INSERT OR UPDATE ON consultation_terms
FOR EACH ROW
EXECUTE FUNCTION term_creation_validation();

CREATE OR REPLACE FUNCTION student_registration_validation()
RETURNS TRIGGER AS $$
BEGIN

    IF (
        SELECT role
        FROM users
        WHERE user_id = NEW.student_id
    ) <> 'student' THEN

        RAISE EXCEPTION
            'Na termin se može prijaviti samo student.';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_student_registration_validation
BEFORE INSERT OR UPDATE ON term_registrations
FOR EACH ROW
EXECUTE FUNCTION student_registration_validation();

CREATE OR REPLACE FUNCTION prevent_registration_to_past_term()
RETURNS TRIGGER AS $$
BEGIN

    IF (
        SELECT start_time
        FROM consultation_terms
        WHERE term_id = NEW.term_id
    ) < CURRENT_TIMESTAMP THEN

        RAISE EXCEPTION
            'Nije moguće prijaviti se na termin koji je već prošao.';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_past_registration
BEFORE INSERT ON term_registrations
FOR EACH ROW
EXECUTE FUNCTION prevent_registration_to_past_term();


CREATE OR REPLACE FUNCTION check_office_capacity()
RETURNS TRIGGER AS $$
BEGIN

    IF (
        SELECT COUNT(*)
        FROM term_registrations
        WHERE term_id = NEW.term_id
    ) >= (
        SELECT o.capacity
        FROM consultation_terms t INNER JOIN users u ON t.professor_id = u.user_id INNER JOIN offices o ON u.office_id = o.office_id
        WHERE t.term_id = NEW.term_id
    ) THEN

        RAISE EXCEPTION
            'Termin je popunjen.';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_office_capacity
BEFORE INSERT ON term_registrations
FOR EACH ROW
EXECUTE FUNCTION check_office_capacity();

CREATE OR REPLACE FUNCTION validate_user_office()
RETURNS TRIGGER AS $$
BEGIN

    IF NEW.role = 'professor' AND NEW.office_id IS NULL THEN
        RAISE EXCEPTION
            'Profesor mora imati ured.';
    END IF;

    IF NEW.role IN ('admin', 'student')
       AND NEW.office_id IS NOT NULL THEN
        RAISE EXCEPTION
            'Samo profesor može imati ured.';
    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_user_office
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION validate_user_office();

CREATE OR REPLACE FUNCTION get_free_places(p_term_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    max_capacity INTEGER;
    registered_count INTEGER;
BEGIN

    SELECT o.capacity
    INTO max_capacity
    FROM consultation_terms t INNER JOIN users u ON t.professor_id = u.user_id INNER JOIN offices o ON u.office_id = o.office_id
    WHERE t.term_id = p_term_id;

    SELECT COUNT(*)
    INTO registered_count
    FROM term_registrations
    WHERE term_id = p_term_id;

    RETURN max_capacity - registered_count;

END;
$$ LANGUAGE plpgsql;

DROP VIEW IF EXISTS consultation_overview;
CREATE VIEW consultation_overview AS
SELECT
    t.term_id,
    s.name AS subject,
    u.first_name || ' ' || u.last_name AS professor,
    o.office_name,
    t.start_time,
    t.end_time,
    o.capacity,
    COUNT(tr.registration_id) AS registered_students,
    o.capacity - COUNT(tr.registration_id) AS free_places
	FROM consultation_terms t INNER JOIN subjects s ON t.subject_id = s.subject_id INNER JOIN users u ON t.professor_id = u.user_id INNER JOIN offices o
	ON u.office_id = o.office_id LEFT JOIN term_registrations tr ON t.term_id = tr.term_id
GROUP BY
    t.term_id,
    s.name,
    u.first_name,
    u.last_name,
    o.office_name,
    o.capacity,
    t.start_time,
    t.end_time;

	
CREATE OR REPLACE PROCEDURE register_student(
    p_term_id INTEGER,
    p_student_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN

    INSERT INTO term_registrations(term_id, student_id)
    VALUES (p_term_id, p_student_id);

END;
$$;

CREATE OR REPLACE FUNCTION validate_professor_office()
RETURNS TRIGGER AS
$$
BEGIN

    IF NEW.office_id IS NOT NULL THEN

        IF NEW.role <> 'professor' THEN

            RAISE EXCEPTION
            'Samo profesor može imati ured';

        END IF;

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_professor_office
BEFORE INSERT OR UPDATE
ON users
FOR EACH ROW
EXECUTE FUNCTION validate_professor_office();

CREATE OR REPLACE FUNCTION validate_term_time()
RETURNS TRIGGER AS
$$
BEGIN

    IF NEW.end_time <= NEW.start_time THEN

        RAISE EXCEPTION
        'end_time must be after start_time';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_term_time
BEFORE INSERT OR UPDATE
ON consultation_terms
FOR EACH ROW
EXECUTE FUNCTION validate_term_time();

CREATE OR REPLACE FUNCTION validate_student_registration()
RETURNS TRIGGER AS
$$
DECLARE
    user_role TEXT;
BEGIN

    SELECT role
    INTO user_role
    FROM users
    WHERE user_id = NEW.student_id;

    IF user_role IS NULL THEN

        RAISE EXCEPTION
        'Student does not exist';

    END IF;

    IF user_role <> 'student' THEN

        RAISE EXCEPTION
        'Only students can register';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_student_registration
BEFORE INSERT OR UPDATE
ON term_registrations
FOR EACH ROW
EXECUTE FUNCTION validate_student_registration();

CREATE OR REPLACE FUNCTION validate_term_capacity()
RETURNS TRIGGER AS
$$
DECLARE
    office_capacity INT;
    current_registrations INT;
BEGIN

    SELECT o.capacity
    INTO office_capacity
    FROM consultation_terms ct
    JOIN users u
        ON ct.professor_id = u.user_id
    JOIN offices o
        ON u.office_id = o.office_id
    WHERE ct.term_id = NEW.term_id;

    SELECT COUNT(*)
    INTO current_registrations
    FROM term_registrations
    WHERE term_id = NEW.term_id;

    IF current_registrations >= office_capacity THEN

        RAISE EXCEPTION
        'Term is full';

    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_term_capacity
BEFORE INSERT
ON term_registrations
FOR EACH ROW
EXECUTE FUNCTION validate_term_capacity();

ALTER TABLE term_registrations
ADD CONSTRAINT unique_student_term
UNIQUE (term_id, student_id);