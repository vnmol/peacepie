import os
from pathlib import Path

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simple_sqlite_account_manager.models import Base, Permission, Role, RolePermission, User, UserRole


class DatabaseManager:

    def __init__(self, database_path):
        self.db_dir = Path(database_path)
        self.db_dir.mkdir(exist_ok=True)
        self.db_path = self.db_dir / 'users.db'
        self.engine = self.create_engine()

    def create_engine(self):
        db_exists = os.path.exists(self.db_path)
        engine = create_engine( f'sqlite:///{self.db_path}',connect_args={"check_same_thread": False}, echo=False)
        if not db_exists:
            db_init(engine)
        return engine


def db_init(engine):
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(
        username='admin',
        password_hash=bcrypt.hashpw('admin'.encode(), bcrypt.gensalt()).decode(),
        is_builtin=True
    )
    role = Role(
        name='system',
        is_builtin=True
    )
    permission = Permission(
        pack_name = '*',
        class_name = '*',
        command = '*',
        is_builtin=True
    )
    user_role = UserRole(users=user, roles=role, is_builtin=True)
    role_permission = RolePermission(roles=role, permissions=permission, is_builtin=True)
    session.add_all([user, role, permission, user_role, role_permission])
    session.commit()
    session.close()
