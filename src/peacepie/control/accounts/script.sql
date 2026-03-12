
CREATE TABLE packs (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO packs (name, builtin) VALUES ("*", TRUE);

CREATE TRIGGER prevent_pack_builtin_delete
BEFORE DELETE ON packs
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_pack_builtin_update
BEFORE UPDATE ON packs
FOR EACH ROW
WHEN OLD.builtin = TRUE AND (
    NEW.id != OLD.id OR
    NEW.builtin != OLD.builtin
)
BEGIN
    SELECT RAISE(ABORT, 'Protected fields cannot be modified in builtin records');
END;



CREATE TABLE classes (
    id INTEGER PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES packs(id) ON DELETE CASCADE,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO classes (pack_id, name, builtin) VALUES (1, "*", TRUE);

CREATE TRIGGER prevent_class_builtin_delete
BEFORE DELETE ON classes
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_class_builtin_update
BEFORE UPDATE ON classes
FOR EACH ROW
WHEN OLD.builtin = TRUE AND (
    NEW.id != OLD.id OR
    NEW.builtin != OLD.builtin
)
BEGIN
    SELECT RAISE(ABORT, 'Protected fields cannot be modified in builtin records');
END;

CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO commands (class_id, name, builtin) VALUES (1, "*", TRUE);

CREATE TRIGGER prevent_command_builtin_delete
BEFORE DELETE ON commands
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_command_builtin_update
BEFORE UPDATE ON commands
FOR EACH ROW
WHEN OLD.builtin = TRUE AND (
    NEW.id != OLD.id OR
    NEW.builtin != OLD.builtin
)
BEGIN
    SELECT RAISE(ABORT, 'Protected fields cannot be modified in builtin records');
END;



CREATE TABLE roles (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO roles (name, builtin) VALUES ("system", TRUE);

CREATE TRIGGER prevent_role_builtin_delete
BEFORE DELETE ON roles
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_role_builtin_update
BEFORE UPDATE ON roles
FOR EACH ROW
WHEN OLD.builtin = TRUE AND (
    NEW.id != OLD.id OR
    NEW.builtin != OLD.builtin
)
BEGIN
    SELECT RAISE(ABORT, 'Protected fields cannot be modified in builtin records');
END;



CREATE TABLE role_commands (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    command_id INTEGER NOT NULL REFERENCES commands(id) ON DELETE CASCADE,
    builtin BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(role_id, command_id)
);

INSERT INTO role_commands (role_id, command_id, builtin) VALUES (1, 1, TRUE);

CREATE TRIGGER prevent_role_command_builtin_delete
BEFORE DELETE ON role_commands
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_role_command_builtin_update
BEFORE UPDATE ON role_commands
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot update built-in records');
END;



CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE,
    pass_hash TEXT,
    salt TEXT,
    iterations INTEGER,
    algorithm TEXT
);

CREATE TRIGGER prevent_user_builtin_delete
BEFORE DELETE ON users
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_user_builtin_update
BEFORE UPDATE ON users
FOR EACH ROW
WHEN OLD.builtin = TRUE AND (
    NEW.id != OLD.id OR
    NEW.name != OLD.name OR
    NEW.builtin != OLD.builtin
)
BEGIN
    SELECT RAISE(ABORT, 'Protected fields cannot be modified in builtin records');
END;



CREATE TABLE user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    builtin BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(user_id, role_id)
);

CREATE TRIGGER prevent_user_role_builtin_delete
BEFORE DELETE ON user_roles
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER prevent_user_role_builtin_update
BEFORE UPDATE ON user_roles
FOR EACH ROW
WHEN OLD.builtin = 1
BEGIN
    SELECT RAISE(ABORT, 'Cannot update built-in records');
END;
