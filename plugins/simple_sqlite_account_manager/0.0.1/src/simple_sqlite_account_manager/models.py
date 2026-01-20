from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RolePermission(Base):
    __tablename__ = 'role_permissions'
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
    is_builtin = Column(Boolean, default=False)
    roles = relationship('Role', back_populates='permissions')
    permissions = relationship('Permission', back_populates='roles')

class UserRole(Base):
    __tablename__ = 'user_roles'
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    is_builtin = Column(Boolean, default=False)
    users = relationship('User', back_populates='roles')
    roles = relationship('Role', back_populates='users')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=False)
    roles = relationship('UserRole', back_populates='users')


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    is_builtin = Column(Boolean, default=False)
    users = relationship('UserRole', back_populates='roles')
    permissions = relationship('RolePermission', back_populates='roles')


class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    pack_name = Column(String(50), nullable=False)
    class_name = Column(String(50), nullable=False)
    command = Column(String(50), nullable=False)
    is_builtin = Column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint('pack_name', 'class_name', 'command', name='uix_pcc'),
    )
    roles = relationship('RolePermission', back_populates='permissions')
