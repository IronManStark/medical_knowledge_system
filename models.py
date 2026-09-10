# -*- coding: utf-8 -*-
"""
医学知识库系统 - 数据模型层
作者：陈的斌
"""

import uuid
from datetime import datetime

import bcrypt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Department(db.Model):
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    remark = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    parent = db.relationship("Department", remote_side=[id], backref="children")
    users = db.relationship("User", backref="department", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "remark": self.remark,
        }


class Role(db.Model):
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    permissions = db.Column(db.Text, default="")
    remark = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    users = db.relationship("User", backref="role", lazy="dynamic")

    def has_permission(self, perm_code: str) -> bool:
        if not self.permissions:
            return False
        return perm_code in self.permissions.split(",")


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    real_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(20), default="")
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=True)
    status = db.Column(db.String(10), default="active")
    failed_attempts = db.Column(db.Integer, default=0)
    lock_time = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, raw: str):
        self.password_hash = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        return bcrypt.checkpw(raw.encode("utf-8"), self.password_hash.encode("utf-8"))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "real_name": self.real_name,
            "email": self.email,
            "phone": self.phone,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else "",
            "role_id": self.role_id,
            "role_name": self.role.name if self.role else "",
            "status": self.status,
            "failed_attempts": self.failed_attempts,
            "lock_time": self.lock_time.strftime("%Y-%m-%d %H:%M") if self.lock_time else "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    level = db.Column(db.Integer, default=1)
    sort_order = db.Column(db.Integer, default=0)
    description = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    parent = db.relationship("Category", remote_side=[id], backref="sub_categories")
    entries = db.relationship("KnowledgeEntry", backref="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "level": self.level,
            "sort_order": self.sort_order,
            "description": self.description,
        }


class KnowledgeEntry(db.Model):
    __tablename__ = "knowledge_entry"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    summary = db.Column(db.Text, default="")
    definition = db.Column(db.Text, default="")
    etiology = db.Column(db.Text, default="")
    clinical_manifestation = db.Column(db.Text, default="")
    diagnosis = db.Column(db.Text, default="")
    treatment = db.Column(db.Text, default="")
    prevention = db.Column(db.Text, default="")
    references = db.Column(db.Text, default="")
    tags = db.Column(db.String(300), default="")
    source = db.Column(db.String(20), default="manual")
    status = db.Column(db.String(20), default="draft")
    version = db.Column(db.Integer, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship("User", foreign_keys=[created_by], backref="authored_entries")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "summary": self.summary,
            "definition": self.definition,
            "etiology": self.etiology,
            "clinical_manifestation": self.clinical_manifestation,
            "diagnosis": self.diagnosis,
            "treatment": self.treatment,
            "prevention": self.prevention,
            "references": self.references,
            "tags": self.tags,
            "source": self.source,
            "status": self.status,
            "version": self.version,
            "created_by": self.created_by,
            "author_name": self.author.real_name if self.author else "",
            "reviewed_by": self.reviewed_by,
            "reviewer_name": self.reviewer.real_name if self.reviewer else "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else "",
            "reviewed_at": self.reviewed_at.strftime("%Y-%m-%d %H:%M") if self.reviewed_at else "",
        }


class KnowledgeTemplate(db.Model):
    __tablename__ = "knowledge_template"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    field_definitions = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class ModelConfig(db.Model):
    __tablename__ = "model_config"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    api_url = db.Column(db.String(500), nullable=False)
    api_key = db.Column(db.String(300), default="")
    model_name = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, default=0.3)
    max_tokens = db.Column(db.Integer, default=2048)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class AccessLog(db.Model):
    __tablename__ = "access_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    username = db.Column(db.String(50), default="")
    action = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(50), default="")
    target = db.Column(db.String(200), default="")
    ip_address = db.Column(db.String(50), default="")
    detail = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "module": self.module,
            "target": self.target,
            "ip_address": self.ip_address,
            "detail": self.detail,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


class SystemSetting(db.Model):
    __tablename__ = "system_setting"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, default="")
    description = db.Column(db.String(200), default="")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
