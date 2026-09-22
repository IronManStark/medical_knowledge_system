from datetime import datetime

import bcrypt
from flask_sqlalchemy import SQLAlchemy

shujuku = SQLAlchemy()

class Department(shujuku.Model):
    __tablename__ = "department"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    name = shujuku.Column(shujuku.String(80), nullable=False)
    code = shujuku.Column(shujuku.String(30), unique=True, nullable=False)
    parent_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("department.id"), nullable=True)
    sort_order = shujuku.Column(shujuku.Integer, default=0)
    remark = shujuku.Column(shujuku.String(200), default="")
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    parent = shujuku.relationship("Department", remote_side=[id], backref="children")
    users = shujuku.relationship("User", backref="department", lazy="dynamic")

    def dao_zidian(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "remark": self.remark,
        }

class Role(shujuku.Model):
    __tablename__ = "role"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    name = shujuku.Column(shujuku.String(50), unique=True, nullable=False)
    code = shujuku.Column(shujuku.String(30), unique=True, nullable=False)
    permissions = shujuku.Column(shujuku.Text, default="")
    remark = shujuku.Column(shujuku.String(200), default="")
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    users = shujuku.relationship("User", backref="role", lazy="dynamic")

    def shifou_youquan(self, quanxian_ma):
        if not self.permissions:
            return False
        yongyou = self.permissions.split(",")
        return quanxian_ma in yongyou

class User(shujuku.Model):
    __tablename__ = "user"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    username = shujuku.Column(shujuku.String(50), unique=True, nullable=False)
    real_name = shujuku.Column(shujuku.String(50), nullable=False)
    password_hash = shujuku.Column(shujuku.String(256), nullable=False)
    email = shujuku.Column(shujuku.String(120), default="")
    phone = shujuku.Column(shujuku.String(20), default="")
    department_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("department.id"), nullable=True)
    role_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("role.id"), nullable=True)
    status = shujuku.Column(shujuku.String(10), default="active")
    failed_attempts = shujuku.Column(shujuku.Integer, default=0)
    lock_time = shujuku.Column(shujuku.DateTime, nullable=True)
    last_login = shujuku.Column(shujuku.DateTime, nullable=True)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    def shezhi_mima(self, mingwen):
        yan = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(mingwen.encode("utf-8"), yan).decode("utf-8")

    def yanzheng_mima(self, mingwen):
        try:
            return bcrypt.checkpw(mingwen.encode("utf-8"), self.password_hash.encode("utf-8"))
        except Exception:
            return False

    def shifou_suoding(self):
        if not self.lock_time:
            return False
        return datetime.now() < self.lock_time

    def dao_chu(self):
        jie = {}
        jie["id"] = self.id
        jie["username"] = self.username
        jie["real_name"] = self.real_name
        jie["email"] = self.email
        jie["phone"] = self.phone
        jie["department_id"] = self.department_id
        jie["department_name"] = self.department.name if self.department else ""
        jie["role_id"] = self.role_id
        jie["role_name"] = self.role.name if self.role else ""
        jie["status"] = self.status
        jie["failed_attempts"] = self.failed_attempts
        jie["lock_time"] = self.lock_time.strftime("%Y-%m-%d %H:%M") if self.lock_time else ""
        jie["created_at"] = self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        return jie

class Category(shujuku.Model):
    __tablename__ = "category"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    name = shujuku.Column(shujuku.String(80), nullable=False)
    code = shujuku.Column(shujuku.String(30), unique=True, nullable=False)
    parent_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("category.id"), nullable=True)
    level = shujuku.Column(shujuku.Integer, default=1)
    sort_order = shujuku.Column(shujuku.Integer, default=0)
    description = shujuku.Column(shujuku.String(300), default="")
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    parent = shujuku.relationship("Category", remote_side=[id], backref="sub_categories")
    entries = shujuku.relationship("KnowledgeEntry", backref="category", lazy="dynamic")

    def zhuan_zidian(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "level": self.level,
            "sort_order": self.sort_order,
            "description": self.description,
        }

class KnowledgeEntry(shujuku.Model):
    __tablename__ = "knowledge_entry"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    title = shujuku.Column(shujuku.String(200), nullable=False)
    category_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("category.id"), nullable=True)
    summary = shujuku.Column(shujuku.Text, default="")
    definition = shujuku.Column(shujuku.Text, default="")
    etiology = shujuku.Column(shujuku.Text, default="")
    clinical_manifestation = shujuku.Column(shujuku.Text, default="")
    diagnosis = shujuku.Column(shujuku.Text, default="")
    treatment = shujuku.Column(shujuku.Text, default="")
    prevention = shujuku.Column(shujuku.Text, default="")
    references = shujuku.Column(shujuku.Text, default="")
    tags = shujuku.Column(shujuku.String(300), default="")
    source = shujuku.Column(shujuku.String(20), default="manual")
    status = shujuku.Column(shujuku.String(20), default="draft")
    version = shujuku.Column(shujuku.Integer, default=1)
    created_by = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("user.id"), nullable=True)
    reviewed_by = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("user.id"), nullable=True)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)
    updated_at = shujuku.Column(shujuku.DateTime, default=datetime.now, onupdate=datetime.now)
    reviewed_at = shujuku.Column(shujuku.DateTime, nullable=True)
    bohui_liyou = shujuku.Column(shujuku.Text, default="")
    yi_tingyong = shujuku.Column(shujuku.Boolean, default=False)
    icd_code = shujuku.Column(shujuku.String(30), default="")
    evidence_level = shujuku.Column(shujuku.String(20), default="")

    author = shujuku.relationship("User", foreign_keys=[created_by], backref="authored_entries")
    reviewer = shujuku.relationship("User", foreign_keys=[reviewed_by])

    def zuo_zidian(self):
        z = {}
        z["id"] = self.id
        z["title"] = self.title
        z["category_id"] = self.category_id
        z["category_name"] = self.category.name if self.category else ""
        z["summary"] = self.summary
        z["definition"] = self.definition
        z["etiology"] = self.etiology
        z["clinical_manifestation"] = self.clinical_manifestation
        z["diagnosis"] = self.diagnosis
        z["treatment"] = self.treatment
        z["prevention"] = self.prevention
        z["references"] = self.references
        z["tags"] = self.tags
        z["source"] = self.source
        z["status"] = self.status
        z["version"] = self.version
        z["created_by"] = self.created_by
        z["author_name"] = self.author.real_name if self.author else ""
        z["reviewed_by"] = self.reviewed_by
        z["reviewer_name"] = self.reviewer.real_name if self.reviewer else ""
        z["created_at"] = self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        z["updated_at"] = self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else ""
        z["reviewed_at"] = self.reviewed_at.strftime("%Y-%m-%d %H:%M") if self.reviewed_at else ""
        z["bohui_liyou"] = self.bohui_liyou or ""
        z["icd_code"] = self.icd_code or ""
        z["evidence_level"] = self.evidence_level or ""
        return z

    files = shujuku.relationship(
        "KnowledgeFile", backref="entry", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    aliases = shujuku.relationship(
        "KnowledgeAlias", backref="entry", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    out_links = shujuku.relationship(
        "KnowledgeLink", foreign_keys="KnowledgeLink.source_entry_id",
        backref="source", lazy="dynamic", cascade="all, delete-orphan",
    )
    in_links = shujuku.relationship(
        "KnowledgeLink", foreign_keys="KnowledgeLink.target_entry_id",
        backref="target", lazy="dynamic",
    )

class KnowledgeFile(shujuku.Model):
    __tablename__ = "knowledge_file"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    entry_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("knowledge_entry.id"), nullable=True, index=True)
    original_name = shujuku.Column(shujuku.String(255), nullable=False)
    object_name = shujuku.Column(shujuku.String(500), nullable=False)
    content_type = shujuku.Column(shujuku.String(120), default="application/octet-stream")
    file_size = shujuku.Column(shujuku.Integer, default=0)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    def leixing_qianzhui(self):
        return (self.content_type or "").split("/")[0].lower()

    def shi_tupian(self):
        return self.leixing_qianzhui() == "image"

    def shi_pdf(self):
        return (self.content_type or "").lower() == "application/pdf" or self.original_name.lower().endswith(".pdf")

    def shi_word(self):
        m = (self.original_name or "").lower()
        return m.endswith(".doc") or m.endswith(".docx")

class KnowledgeTemplate(shujuku.Model):
    __tablename__ = "knowledge_template"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    name = shujuku.Column(shujuku.String(80), nullable=False)
    field_definitions = shujuku.Column(shujuku.Text, nullable=False)
    is_default = shujuku.Column(shujuku.Boolean, default=False)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

class ModelConfig(shujuku.Model):
    __tablename__ = "model_config"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    name = shujuku.Column(shujuku.String(80), nullable=False)
    api_url = shujuku.Column(shujuku.String(500), nullable=False)
    api_key = shujuku.Column(shujuku.String(300), default="")
    model_name = shujuku.Column(shujuku.String(100), nullable=False)
    temperature = shujuku.Column(shujuku.Float, default=0.3)
    max_tokens = shujuku.Column(shujuku.Integer, default=2048)
    si_kao_mo_shi = shujuku.Column(shujuku.Boolean, default=False)
    ti_shi_ci = shujuku.Column(shujuku.Text, default="")
    is_active = shujuku.Column(shujuku.Boolean, default=False)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

class AccessLog(shujuku.Model):
    __tablename__ = "access_log"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    user_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("user.id"), nullable=True)
    username = shujuku.Column(shujuku.String(50), default="")
    action = shujuku.Column(shujuku.String(50), nullable=False)
    module = shujuku.Column(shujuku.String(50), default="")
    target = shujuku.Column(shujuku.String(200), default="")
    ip_address = shujuku.Column(shujuku.String(50), default="")
    detail = shujuku.Column(shujuku.Text, default="")
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    def cdb_lie_yi_xia(self):
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

class SystemSetting(shujuku.Model):
    __tablename__ = "system_setting"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    key = shujuku.Column(shujuku.String(80), unique=True, nullable=False)
    value = shujuku.Column(shujuku.Text, default="")
    description = shujuku.Column(shujuku.String(200), default="")
    updated_at = shujuku.Column(shujuku.DateTime, default=datetime.now, onupdate=datetime.now)

class KnowledgeAlias(shujuku.Model):
    __tablename__ = "knowledge_alias"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    entry_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("knowledge_entry.id"), nullable=False, index=True)
    alias_name = shujuku.Column(shujuku.String(100), nullable=False, index=True)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

class KnowledgeLink(shujuku.Model):
    __tablename__ = "knowledge_link"

    id = shujuku.Column(shujuku.Integer, primary_key=True, autoincrement=True)
    source_entry_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("knowledge_entry.id"), nullable=False, index=True)
    target_entry_id = shujuku.Column(shujuku.Integer, shujuku.ForeignKey("knowledge_entry.id"), nullable=False, index=True)
    link_type = shujuku.Column(shujuku.String(30), default="关联")
    strength = shujuku.Column(shujuku.Float, default=0.3)
    is_explicit = shujuku.Column(shujuku.Boolean, default=False)
    created_at = shujuku.Column(shujuku.DateTime, default=datetime.now)

    def zuo_zidian(self):
        return {
            "id": self.id,
            "source": self.source.title if self.source else "",
            "target": self.target.title if self.target else "",
            "source_id": self.source_entry_id,
            "target_id": self.target_entry_id,
            "link_type": self.link_type,
            "strength": round(self.strength or 0.01, 2),
            "is_explicit": self.is_explicit,
        }
