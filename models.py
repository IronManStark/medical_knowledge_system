# -*- coding: utf-8 -*-
"""
医学知识库系统 - 数据模型层
定义用户、科室、权限、知识条目、分类、日志等核心实体结构
作者：陈的斌
"""

import hashlib
import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _hash_password(raw: str) -> str:
    """使用 SHA-256 加盐哈希存储口令"""
    salt = "mks_salt_2024"
    return hashlib.sha256((raw + salt).encode("utf-8")).hexdigest()


class Department(db.Model):
    """科室信息表"""

    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False, comment="科室名称")
    code = db.Column(db.String(30), unique=True, nullable=False, comment="科室编码")
    parent_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True, comment="上级科室")
    sort_order = db.Column(db.Integer, default=0, comment="排列序号")
    remark = db.Column(db.String(200), default="", comment="备注")
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
    """角色与权限定义表"""

    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False, comment="角色名称")
    code = db.Column(db.String(30), unique=True, nullable=False, comment="角色编码")
    permissions = db.Column(db.Text, default="", comment="权限列表，逗号分隔")
    remark = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    users = db.relationship("User", backref="role", lazy="dynamic")

    def has_permission(self, perm_code: str) -> bool:
        if not self.permissions:
            return False
        return perm_code in self.permissions.split(",")


class User(db.Model):
    """系统用户表"""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, comment="登录账号")
    real_name = db.Column(db.String(50), nullable=False, comment="真实姓名")
    password_hash = db.Column(db.String(128), nullable=False, comment="口令哈希")
    email = db.Column(db.String(120), default="", comment="电子邮箱")
    phone = db.Column(db.String(20), default="", comment="联系电话")
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=True)
    status = db.Column(db.String(10), default="active", comment="active/disabled")
    failed_attempts = db.Column(db.Integer, default=0, comment="密码错误次数")
    lock_time = db.Column(db.DateTime, nullable=True, comment="账号锁定时间")
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, raw: str):
        self.password_hash = _hash_password(raw)

    def check_password(self, raw: str) -> bool:
        return self.password_hash == _hash_password(raw)

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
    """知识分类体系表（支持树形结构）"""

    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False, comment="分类名称")
    code = db.Column(db.String(30), unique=True, nullable=False, comment="分类编码")
    parent_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True, comment="上级分类")
    level = db.Column(db.Integer, default=1, comment="层级")
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
    """医学知识条目主表"""

    __tablename__ = "knowledge_entry"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False, comment="知识标题/名称")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    summary = db.Column(db.Text, default="", comment="摘要")
    definition = db.Column(db.Text, default="", comment="定义")
    etiology = db.Column(db.Text, default="", comment="病因")
    clinical_manifestation = db.Column(db.Text, default="", comment="临床表现")
    diagnosis = db.Column(db.Text, default="", comment="诊断标准")
    treatment = db.Column(db.Text, default="", comment="治疗方案")
    prevention = db.Column(db.Text, default="", comment="预防措施")
    references = db.Column(db.Text, default="", comment="参考文献")
    tags = db.Column(db.String(300), default="", comment="标签，逗号分隔")
    source = db.Column(db.String(20), default="manual", comment="manual/generated")
    status = db.Column(db.String(20), default="draft", comment="draft/pending/published/rejected")
    version = db.Column(db.Integer, default=1, comment="版本号")
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
    """知识录入模板表，定义各字段名称与顺序"""

    __tablename__ = "knowledge_template"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False, comment="模板名称")
    field_definitions = db.Column(db.Text, nullable=False, comment="JSON格式字段定义")
    is_default = db.Column(db.Boolean, default=False, comment="是否默认模板")
    created_at = db.Column(db.DateTime, default=datetime.now)


class ModelConfig(db.Model):
    """模型接口配置表，支持运行期动态配置"""

    __tablename__ = "model_config"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False, comment="配置名称")
    api_url = db.Column(db.String(500), nullable=False, comment="接口地址")
    api_key = db.Column(db.String(300), default="", comment="密钥")
    model_name = db.Column(db.String(100), nullable=False, comment="模型标识")
    temperature = db.Column(db.Float, default=0.3, comment="生成温度")
    max_tokens = db.Column(db.Integer, default=2048, comment="最大返回token")
    is_active = db.Column(db.Boolean, default=False, comment="当前是否启用")
    created_at = db.Column(db.DateTime, default=datetime.now)


class AccessLog(db.Model):
    """用户访问操作日志表"""

    __tablename__ = "access_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    username = db.Column(db.String(50), default="", comment="操作人账号")
    action = db.Column(db.String(50), nullable=False, comment="操作类型")
    module = db.Column(db.String(50), default="", comment="功能模块")
    target = db.Column(db.String(200), default="", comment="操作对象")
    ip_address = db.Column(db.String(50), default="")
    detail = db.Column(db.Text, default="", comment="详情")
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
    """系统参数键值对存储"""

    __tablename__ = "system_setting"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, default="")
    description = db.Column(db.String(200), default="")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
