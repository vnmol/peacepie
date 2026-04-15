
CREATE TABLE packs (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO packs (name, builtin) VALUES ("*", TRUE);
INSERT INTO packs (name) VALUES ("peacepie.control.head_prime_admin");
INSERT INTO packs (name) VALUES ("peacepie.control.prime_admin");
INSERT INTO packs (name) VALUES ("peacepie.control.admin");
INSERT INTO packs (name) VALUES ("peacepie.control.accounts.account_admin");

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
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO classes (name, builtin) VALUES ("*", TRUE);
INSERT INTO classes (name) VALUES ("HeadPrimeAdmin");
INSERT INTO classes (name) VALUES ("PrimeAdmin");
INSERT INTO classes (name) VALUES ("Admin");
INSERT INTO classes (name) VALUES ("AccountAdmin");

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




CREATE TABLE pack_classes (
    id INTEGER PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES packs(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    UNIQUE (pack_id, class_id)
);

INSERT INTO pack_classes (pack_id, class_id) VALUES (1, 1);
INSERT INTO pack_classes (pack_id, class_id) VALUES (2, 2);
INSERT INTO pack_classes (pack_id, class_id) VALUES (3, 3);
INSERT INTO pack_classes (pack_id, class_id) VALUES (4, 4);
INSERT INTO pack_classes (pack_id, class_id) VALUES (5, 5);

CREATE TRIGGER prevent_pack_class_builtin_delete
BEFORE DELETE ON pack_classes
FOR EACH ROW
WHEN
    EXISTS (
        SELECT 1
        FROM packs
        WHERE id = OLD.pack_id AND builtin = 1
    )
    AND EXISTS (
        SELECT 1
        FROM classes
        WHERE id = OLD.class_id AND builtin = 1
    )
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER no_update_pack_classes
BEFORE UPDATE ON pack_classes
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'UPDATE is not allowed on pack_classes');
END;




CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO commands (name, builtin) VALUES ("*", TRUE);
INSERT INTO commands (name) VALUES ("get_members");
INSERT INTO commands (name) VALUES ("get_packs");
INSERT INTO commands (name) VALUES ("create_pack");
INSERT INTO commands (name) VALUES ("update_pack");
INSERT INTO commands (name) VALUES ("delete_pack");
INSERT INTO commands (name) VALUES ("get_classes");
INSERT INTO commands (name) VALUES ("create_class");
INSERT INTO commands (name) VALUES ("update_class");
INSERT INTO commands (name) VALUES ("delete_class");
INSERT INTO commands (name) VALUES ("get_pack_classes");
INSERT INTO commands (name) VALUES ("create_pack_class");
INSERT INTO commands (name) VALUES ("delete_pack_class");
INSERT INTO commands (name) VALUES ("get_commands");
INSERT INTO commands (name) VALUES ("create_command");
INSERT INTO commands (name) VALUES ("update_command");
INSERT INTO commands (name) VALUES ("delete_command");
INSERT INTO commands (name) VALUES ("get_roles");
INSERT INTO commands (name) VALUES ("create_role");
INSERT INTO commands (name) VALUES ("update_role");
INSERT INTO commands (name) VALUES ("delete_role");
INSERT INTO commands (name) VALUES ("get_role_commands");
INSERT INTO commands (name) VALUES ("create_role_command");
INSERT INTO commands (name) VALUES ("delete_role_command");
INSERT INTO commands (name) VALUES ("get_users");
INSERT INTO commands (name) VALUES ("create_user");
INSERT INTO commands (name) VALUES ("update_user");
INSERT INTO commands (name) VALUES ("delete_user");
INSERT INTO commands (name) VALUES ("get_user_roles");
INSERT INTO commands (name) VALUES ("create_user_role");
INSERT INTO commands (name) VALUES ("delete_user_role");

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




CREATE TABLE class_commands (
    id INTEGER PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES pack_classes(id) ON DELETE CASCADE,
    command_id INTEGER NOT NULL REFERENCES commands(id) ON DELETE CASCADE,
    UNIQUE(class_id, command_id)
);

INSERT INTO class_commands (class_id, command_id) VALUES (1, 1);
INSERT INTO class_commands (class_id, command_id) VALUES (2, 2);
INSERT INTO class_commands (class_id, command_id) VALUES (3, 2);
INSERT INTO class_commands (class_id, command_id) VALUES (4, 2);
INSERT INTO class_commands (class_id, command_id) SELECT 5, c.id FROM commands c WHERE c.id > 2;

CREATE TRIGGER prevent_class_command_builtin_delete
BEFORE DELETE ON class_commands
FOR EACH ROW
WHEN
    EXISTS (
        SELECT 1
        FROM pack_classes pc
        JOIN packs p ON pc.pack_id = p.id
        JOIN classes c ON pc.class_id = c.id
        WHERE pc.id = OLD.class_id and p.builtin = 1 and c.builtin = 1
    )
    AND EXISTS (
        SELECT 1
        FROM commands
        WHERE id = OLD.command_id AND builtin = 1
    )
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER no_update_class_commands
BEFORE UPDATE ON class_commands
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'UPDATE is not allowed on class_commands');
END;




CREATE TABLE roles (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    builtin BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO roles (name, builtin) VALUES ("system", TRUE);
INSERT INTO roles (name) VALUES ("member_viewer");
INSERT INTO roles (name) VALUES ("account_admin");

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
    id INTEGER PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    class_command_id INTEGER NOT NULL REFERENCES class_commands(id) ON DELETE CASCADE,
    UNIQUE(role_id, class_command_id)
);

INSERT INTO role_commands (role_id, class_command_id) VALUES (1, 1);
INSERT INTO role_commands (role_id, class_command_id) VALUES (2, 2);
INSERT INTO role_commands (role_id, class_command_id) VALUES (2, 3);
INSERT INTO role_commands (role_id, class_command_id) VALUES (2, 4);
INSERT INTO role_commands (role_id, class_command_id) SELECT 3, cc.id FROM class_commands cc WHERE cc.id > 4;

CREATE TRIGGER prevent_role_command_builtin_delete
BEFORE DELETE ON role_commands
FOR EACH ROW
WHEN
    EXISTS (
        SELECT 1
        FROM roles
        WHERE id = OLD.role_id AND builtin = 1
    )
    AND EXISTS (
        SELECT 1
        FROM class_commands cc
        JOIN commands com ON cc.command_id = com.id
        JOIN pack_classes pc ON cc.class_id = pc.id
        JOIN classes c ON pc.class_id = c.id
        JOIN packs p ON pc.pack_id = p.id
        WHERE cc.id = OLD.class_command_id and com.builtin = 1 and c.builtin = 1 and p.builtin = 1
    )
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER no_update_role_commands
BEFORE UPDATE ON role_commands
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'UPDATE is not allowed on role_commands');
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
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    UNIQUE(user_id, role_id)
);

CREATE TRIGGER prevent_user_role_builtin_delete
BEFORE DELETE ON user_roles
FOR EACH ROW
WHEN
    EXISTS (
        SELECT 1
        FROM users
        WHERE id = OLD.user_id AND builtin = 1
    )
    AND EXISTS (
        SELECT 1
        FROM roles
        WHERE id = OLD.role_id AND builtin = 1
    )
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete built-in records');
END;

CREATE TRIGGER no_update_user_roles
BEFORE UPDATE ON user_roles
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'UPDATE is not allowed on user_roles');
END;
