DROP TABLE IF EXISTS offices CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS consultation_terms CASCADE;
DROP TABLE IF EXISTS term_registrations CASCADE;

CREATE TABLE offices (
    office_id SERIAL PRIMARY KEY,
    office_name VARCHAR(50) NOT NULL UNIQUE,
    capacity INTEGER NOT NULL CHECK (capacity > 0)
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'professor', 'student')),
	office_id INTEGER REFERENCES offices(office_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subjects (
    subject_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);


CREATE TABLE consultation_terms (
    term_id SERIAL PRIMARY KEY,
    professor_id INTEGER NOT NULL REFERENCES users(user_id),
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, CHECK (end_time > start_time)
);

CREATE TABLE term_registrations (
    registration_id SERIAL PRIMARY KEY,
    term_id INTEGER NOT NULL REFERENCES consultation_terms(term_id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(term_id, student_id)
);

INSERT INTO offices (
    office_name,
    capacity
)
VALUES
('ured1', 5),
('ured2', 5),
('ured3', 5),
('ured4', 5),
('ured5', 5);

INSERT INTO users (
    first_name,
    last_name,
    email,
    password_hash,
    role,
    office_id
)
VALUES
('ime1', 'prezime1', 'ime1.prezime1@mail.com', '12345678', 'admin', NULL),
('ime2', 'prezime2', 'ime2.prezime2@mail.com', '12345678', 'professor', 1),
('ime3', 'prezime3', 'ime3.prezime3@mail.com', '12345678', 'professor', 2),
('ime4', 'prezime4', 'ime4.prezime4@mail.com', '12345678', 'professor', 3),
('ime5', 'prezime5', 'ime5.prezime5@mail.com', '12345678', 'professor', 4),
('ime6', 'prezime6', 'ime6.prezime6@mail.com', '12345678', 'professor', 5),
('ime7', 'prezime7', 'ime7.prezime7@mail.com', '12345678', 'student', NULL),
('ime8', 'prezime8', 'ime8.prezime8@mail.com', '12345678', 'student', NULL),
('ime9', 'prezime9', 'ime9.prezime9@mail.com', '12345678', 'student', NULL),
('ime10', 'prezime10', 'ime10.prezime10@mail.com', '12345678', 'student', NULL),
('ime11', 'prezime11', 'ime11.prezime11@mail.com', '12345678', 'student', NULL),
('ime12', 'prezime12', 'ime12.prezime12@mail.com', '12345678', 'student', NULL),
('ime13', 'prezime13', 'ime13.prezime13@mail.com', '12345678', 'student', NULL),
('ime14', 'prezime14', 'ime14.prezime14@mail.com', '12345678', 'student', NULL),
('ime15', 'prezime15', 'ime15.prezime15@mail.com', '12345678', 'student', NULL),
('ime16', 'prezime16', 'ime16.prezime16@mail.com', '12345678', 'student', NULL);

INSERT INTO subjects (
    name,
    description
)
VALUES
('predmet1', 'predmet1'),
('predmet2', 'predmet2'),
('predmet3', 'predmet3'),
('predmet4', 'predmet4'),
('predmet5', 'predmet5');

INSERT INTO consultation_terms (
    professor_id,
    subject_id,
    start_time,
    end_time
)
VALUES
(2, 1, '2026-01-01 09:00:00', '2026-01-01 10:00:00'),
(3, 2, '2026-01-02 09:00:00', '2026-01-02 10:00:00'),
(4, 3, '2026-01-03 09:00:00', '2026-01-03 10:00:00'),
(5, 4, '2026-01-04 09:00:00', '2026-01-04 10:00:00'),
(6, 5, '2026-01-05 09:00:00', '2026-01-05 10:00:00');

INSERT INTO term_registrations (
    term_id,
    student_id
)
VALUES
(1, 7),
(1, 8),
(1, 9),

(2, 10),
(2, 11),

(3, 12),
(3, 13),

(4, 14),

(5, 15),
(5, 16);


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



