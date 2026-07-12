# -*- coding: utf-8 -*-
"""
医学知识库系统 - 主应用入口
基于 Flask 框架实现，包含认证、用户管理、知识管理、
分类查阅、日志统计等完整功能模块
作者：陈的斌
"""

import json
import os
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, redirect, url_for, request, session,
    flash, jsonify, abort, g, send_file,
)
from PIL import Image, ImageDraw, ImageFont
from flask_wtf.csrf import CSRFProtect

from config import CONFIG_MAP
from models import (
    db, Department, Role, User, Category, KnowledgeEntry,
    KnowledgeTemplate, ModelConfig, AccessLog, SystemSetting,
)
from forms import (
    LoginForm, UserForm, DepartmentForm, RoleForm, CategoryForm,
    KnowledgeForm, ModelConfigForm, KnowledgeGenerateForm,
)
from utils import log_access
from utils.model_client import call_model

# --------------------------------------------------------------------------- #
# 应用工厂
# --------------------------------------------------------------------------- #

def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP[env])

    os.makedirs(os.path.join(app.config.get("UPLOAD_FOLDER", "data/uploads")), exist_ok=True)
    db_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(db_dir, exist_ok=True)

    db.init_app(app)
    csrf = CSRFProtect(app)

    register_before_handlers(app)
    register_auth_routes(app)
    register_dashboard(app)
    register_user_routes(app)
    register_department_routes(app)
    register_role_routes(app)
    register_category_routes(app)
    register_knowledge_routes(app)
    register_model_routes(app)
    register_auxiliary_routes(app)
    register_template_helpers(app)

    with app.app_context():
        db.create_all()
        seed_default_data(app)

    return app


# --------------------------------------------------------------------------- #
# 请求前处理与上下文
# --------------------------------------------------------------------------- #

def register_before_handlers(app: Flask):
    @app.before_request
    def _load_current_user():
        uid = session.get("uid")
        g.current_user = None
        if uid:
            g.current_user = User.query.get(uid)

    @app.context_processor
    def _inject_globals():
        return {
            "current_user": g.current_user,
            "current_year": datetime.now().year,
        }


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not g.current_user:
            flash("请先登录系统", "warning")
            return redirect(url_for("login", next=request.full_path))
        return func(*args, **kwargs)
    return wrapper


def permission_required(perm_code: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = g.current_user
            if not user or not user.role:
                abort(403)
            if not user.role.has_permission(perm_code) and user.role.code != "admin":
                flash("您没有该功能的操作权限", "danger")
                return redirect(url_for("dashboard"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


# --------------------------------------------------------------------------- #
# 认证路由
# --------------------------------------------------------------------------- #

def _generate_captcha() -> tuple:
    chars = string.digits + string.ascii_uppercase
    code = "".join(random.sample(chars, 4))
    img = Image.new("RGB", (120, 40), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 30)
    except:
        font = ImageFont.load_default()
    for i, c in enumerate(code):
        draw.text((10 + i * 28, 5), c, font=font, fill=(random.randint(0, 150), random.randint(0, 150), random.randint(0, 150)))
    for _ in range(5):
        draw.line([(random.randint(0, 120), random.randint(0, 40)), (random.randint(0, 120), random.randint(0, 40))], fill=(200, 200, 200), width=1)
    for _ in range(20):
        draw.point((random.randint(0, 120), random.randint(0, 40)), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    buf = BytesIO()
    img.save(buf, "JPEG")
    buf.seek(0)
    return code, buf


def register_auth_routes(app: Flask):
    @app.route("/", methods=["GET"])
    def index():
        if g.current_user:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/captcha")
    def captcha():
        code, buf = _generate_captcha()
        session["captcha"] = code
        return send_file(buf, mimetype="image/jpeg")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.current_user:
            return redirect(url_for("dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            captcha_input = form.captcha.data.upper()
            session_captcha = session.get("captcha", "").upper()
            if captcha_input != session_captcha:
                flash("验证码不正确", "danger")
                session.pop("captcha", None)
                return render_template("login.html", form=form)

            user = User.query.filter_by(username=form.username.data).first()
            if not user:
                flash("账号或口令不正确", "danger")
                session.pop("captcha", None)
                return render_template("login.html", form=form)

            if user.lock_time and datetime.now() < user.lock_time:
                remaining = (user.lock_time - datetime.now()).total_seconds() // 60
                flash(f"账号已被锁定，请{int(remaining)}分钟后重试", "danger")
                session.pop("captcha", None)
                return render_template("login.html", form=form)

            if user.status != "active":
                flash("该账号已被停用，请联系管理员", "danger")
                session.pop("captcha", None)
                return render_template("login.html", form=form)

            if not user.check_password(form.password.data):
                user.failed_attempts += 1
                if user.failed_attempts >= 5:
                    user.lock_time = datetime.now() + timedelta(minutes=15)
                    user.failed_attempts = 0
                    db.session.commit()
                    flash("连续5次密码错误，账号已被锁定，15分钟后自动解锁", "danger")
                else:
                    db.session.commit()
                    flash(f"账号或口令不正确，密码已错误{user.failed_attempts}次，连续错误5次需要15分钟后重试", "danger")
                session.pop("captcha", None)
                return render_template("login.html", form=form)

            user.failed_attempts = 0
            user.lock_time = None
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=app.config["SESSION_LIFETIME_HOURS"])
            session["uid"] = user.id
            user.last_login = datetime.now()
            db.session.commit()
            log_access(user, "login", "认证", "用户登录")
            flash("登录成功，欢迎回来", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        return render_template("login.html", form=form)

    @app.route("/logout")
    def logout():
        user = g.current_user
        if user:
            log_access(user, "logout", "认证", "用户退出")
        session.clear()
        flash("您已安全退出系统", "info")
        return redirect(url_for("login"))

    @app.route("/change-password", methods=["POST"])
    @login_required
    def change_password():
        user = g.current_user
        old_password = request.form.get("old_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not user.check_password(old_password):
            flash("原密码不正确", "danger")
            return redirect(request.referrer or url_for("dashboard"))

        if len(new_password) < 6:
            flash("新密码长度至少6位", "danger")
            return redirect(request.referrer or url_for("dashboard"))

        if new_password != confirm_password:
            flash("两次输入的新密码不一致", "danger")
            return redirect(request.referrer or url_for("dashboard"))

        user.set_password(new_password)
        db.session.commit()
        log_access(user, "update", "用户管理", "修改密码")
        flash("密码修改成功，请重新登录", "success")
        session.clear()
        return redirect(url_for("login"))


# --------------------------------------------------------------------------- #
# 仪表盘
# --------------------------------------------------------------------------- #

def register_dashboard(app: Flask):
    @app.route("/dashboard")
    @login_required
    def dashboard():
        total_users = User.query.count()
        total_entries = KnowledgeEntry.query.count()
        published = KnowledgeEntry.query.filter_by(status="published").count()
        pending = KnowledgeEntry.query.filter_by(status="pending").count()
        total_categories = Category.query.count()
        today_logs = AccessLog.query.filter(
            AccessLog.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()

        stats = {
            "users": total_users,
            "entries": total_entries,
            "published": published,
            "pending": pending,
            "categories": total_categories,
            "today_logs": today_logs,
        }
        return render_template("dashboard.html", stats=stats)


# --------------------------------------------------------------------------- #
# 用户管理（人员维护）
# --------------------------------------------------------------------------- #

def register_user_routes(app: Flask):
    @app.route("/users")
    @login_required
    @permission_required("user_manage")
    def user_list():
        keyword = request.args.get("keyword", "").strip()
        dept_id = request.args.get("dept", 0, type=int)
        page = request.args.get("page", 1, type=int)

        query = User.query
        if keyword:
            query = query.filter(
                db.or_(User.username.contains(keyword), User.real_name.contains(keyword))
            )
        if dept_id:
            query = query.filter_by(department_id=dept_id)
        pagination = query.order_by(User.id.desc()).paginate(
            page=page, per_page=app.config["PER_PAGE"], error_out=False
        )
        departments = Department.query.order_by(Department.sort_order).all()
        return render_template(
            "users/list.html",
            users=pagination.items, pagination=pagination,
            keyword=keyword, dept_id=dept_id, departments=departments,
        )

    @app.route("/users/create", methods=["GET", "POST"])
    @login_required
    @permission_required("user_manage")
    def user_create():
        form = UserForm()
        _populate_user_choices(form)
        if form.validate_on_submit():
            if User.query.filter_by(username=form.username.data).first():
                flash("该登录账号已存在", "danger")
                return render_template("users/edit.html", form=form, mode="create")
            user = User(
                username=form.username.data,
                real_name=form.real_name.data,
                email=form.email.data,
                phone=form.phone.data,
                department_id=form.department_id.data or None,
                role_id=form.role_id.data or None,
                status=form.status.data,
            )
            user.set_password(form.password.data or "123456")
            db.session.add(user)
            db.session.commit()
            log_access(g.current_user, "create", "用户管理", "新增用户: " + user.username)
            flash("用户创建成功", "success")
            return redirect(url_for("user_list"))
        return render_template("users/edit.html", form=form, mode="create")

    @app.route("/users/<int:uid>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("user_manage")
    def user_edit(uid):
        user = User.query.get_or_404(uid)
        form = UserForm(obj=user)
        _populate_user_choices(form)
        if form.validate_on_submit():
            user.real_name = form.real_name.data
            user.email = form.email.data
            user.phone = form.phone.data
            user.department_id = form.department_id.data or None
            user.role_id = form.role_id.data or None
            user.status = form.status.data
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            log_access(g.current_user, "update", "用户管理", "编辑用户: " + user.username)
            flash("用户信息已更新", "success")
            return redirect(url_for("user_list"))
        form.password.data = ""
        return render_template("users/edit.html", form=form, mode="edit", user=user)

    @app.route("/users/<int:uid>/delete", methods=["POST"])
    @login_required
    @permission_required("user_manage")
    def user_delete(uid):
        user = User.query.get_or_404(uid)
        if user.id == g.current_user.id:
            flash("不能删除当前登录账号", "danger")
            return redirect(url_for("user_list"))
        uname = user.username
        db.session.delete(user)
        db.session.commit()
        log_access(g.current_user, "delete", "用户管理", "删除用户: " + uname)
        flash("用户已删除", "info")
        return redirect(url_for("user_list"))


def _populate_user_choices(form: UserForm):
    form.department_id.choices = [(0, "— 请选择 —")] + [
        (d.id, d.name) for d in Department.query.order_by(Department.sort_order).all()
    ]
    form.role_id.choices = [(0, "— 请选择 —")] + [
        (r.id, r.name) for r in Role.query.order_by(Role.id).all()
    ]


# --------------------------------------------------------------------------- #
# 科室维护
# --------------------------------------------------------------------------- #

def register_department_routes(app: Flask):
    @app.route("/departments")
    @login_required
    @permission_required("dept_manage")
    def dept_list():
        departments = Department.query.order_by(Department.sort_order, Department.id).all()
        return render_template("users/departments.html", departments=departments)

    @app.route("/departments/create", methods=["GET", "POST"])
    @login_required
    @permission_required("dept_manage")
    def dept_create():
        form = DepartmentForm()
        _populate_dept_choices(form)
        if form.validate_on_submit():
            if Department.query.filter_by(code=form.code.data).first():
                flash("科室编码已存在", "danger")
                return render_template("users/dept_edit.html", form=form, mode="create")
            dept = Department(
                name=form.name.data,
                code=form.code.data,
                parent_id=form.parent_id.data or None,
                sort_order=form.sort_order.data,
                remark=form.remark.data,
            )
            db.session.add(dept)
            db.session.commit()
            log_access(g.current_user, "create", "科室管理", "新增科室: " + dept.name)
            flash("科室创建成功", "success")
            return redirect(url_for("dept_list"))
        return render_template("users/dept_edit.html", form=form, mode="create")

    @app.route("/departments/<int:did>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("dept_manage")
    def dept_edit(did):
        dept = Department.query.get_or_404(did)
        form = DepartmentForm(obj=dept)
        _populate_dept_choices(form, exclude_id=did)
        if form.validate_on_submit():
            dept.name = form.name.data
            dept.code = form.code.data
            dept.parent_id = form.parent_id.data or None
            dept.sort_order = form.sort_order.data
            dept.remark = form.remark.data
            db.session.commit()
            log_access(g.current_user, "update", "科室管理", "编辑科室: " + dept.name)
            flash("科室信息已更新", "success")
            return redirect(url_for("dept_list"))
        return render_template("users/dept_edit.html", form=form, mode="edit", dept=dept)

    @app.route("/departments/<int:did>/delete", methods=["POST"])
    @login_required
    @permission_required("dept_manage")
    def dept_delete(did):
        dept = Department.query.get_or_404(did)
        if dept.users.count() > 0:
            flash("该科室下仍有人员，无法删除", "danger")
            return redirect(url_for("dept_list"))
        dname = dept.name
        db.session.delete(dept)
        db.session.commit()
        log_access(g.current_user, "delete", "科室管理", "删除科室: " + dname)
        flash("科室已删除", "info")
        return redirect(url_for("dept_list"))


def _populate_dept_choices(form: DepartmentForm, exclude_id=None):
    query = Department.query
    if exclude_id:
        query = query.filter(Department.id != exclude_id)
    form.parent_id.choices = [(0, "— 顶级科室 —")] + [
        (d.id, d.name) for d in query.order_by(Department.sort_order).all()
    ]


# --------------------------------------------------------------------------- #
# 权限维护（角色管理）
# --------------------------------------------------------------------------- #

def register_role_routes(app: Flask):
    PERMISSION_CATALOG = [
        {
            "name": "系统管理",
            "code": "system",
            "children": [
                ("user_manage", "用户管理"),
                ("dept_manage", "科室管理"),
                ("role_manage", "角色管理"),
            ]
        },
        {
            "name": "知识管理",
            "code": "knowledge",
            "children": [
                ("knowledge_create", "知识录入"),
                ("knowledge_edit", "知识编辑"),
                ("knowledge_review", "知识审核"),
                ("knowledge_generate", "知识生成"),
                ("category_manage", "分类管理"),
            ]
        },
        {
            "name": "系统工具",
            "code": "tools",
            "children": [
                ("log_view", "日志查看"),
                ("stat_view", "统计查看"),
                ("model_config", "模型配置"),
            ]
        },
    ]

    def flatten_permissions(catalog):
        perms = []
        for item in catalog:
            if "children" in item:
                for code, label in item["children"]:
                    perms.append((code, label))
            else:
                perms.append((item["code"], item["name"]))
        return perms

    def get_permission_label(code, catalog):
        for item in catalog:
            if "children" in item:
                for c, l in item["children"]:
                    if c == code:
                        return l
        return code

    @app.route("/roles")
    @login_required
    @permission_required("role_manage")
    def role_list():
        roles = Role.query.order_by(Role.id).all()
        return render_template("users/roles.html", roles=roles, catalog=PERMISSION_CATALOG)

    @app.route("/roles/create", methods=["GET", "POST"])
    @login_required
    @permission_required("role_manage")
    def role_create():
        form = RoleForm()
        if form.validate_on_submit():
            if Role.query.filter_by(code=form.code.data).first():
                flash("角色编码已存在", "danger")
                return render_template("users/role_edit.html", form=form, mode="create", catalog=PERMISSION_CATALOG)
            perms = request.form.getlist("permissions")
            role = Role(
                name=form.name.data,
                code=form.code.data,
                permissions=",".join(perms),
                remark=form.remark.data,
            )
            db.session.add(role)
            db.session.commit()
            log_access(g.current_user, "create", "角色管理", "新增角色: " + role.name)
            flash("角色创建成功", "success")
            return redirect(url_for("role_list"))
        return render_template("users/role_edit.html", form=form, mode="create", catalog=PERMISSION_CATALOG)

    @app.route("/roles/<int:rid>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("role_manage")
    def role_edit(rid):
        role = Role.query.get_or_404(rid)
        form = RoleForm(obj=role)
        if form.validate_on_submit():
            role.name = form.name.data
            role.code = form.code.data
            role.permissions = ",".join(request.form.getlist("permissions"))
            role.remark = form.remark.data
            db.session.commit()
            log_access(g.current_user, "update", "角色管理", "编辑角色: " + role.name)
            flash("角色信息已更新", "success")
            return redirect(url_for("role_list"))
        return render_template("users/role_edit.html", form=form, mode="edit", role=role, catalog=PERMISSION_CATALOG)

    @app.route("/roles/<int:rid>/delete", methods=["POST"])
    @login_required
    @permission_required("role_manage")
    def role_delete(rid):
        role = Role.query.get_or_404(rid)
        if role.users.count() > 0:
            flash("该角色下仍有用户，无法删除", "danger")
            return redirect(url_for("role_list"))
        rname = role.name
        db.session.delete(role)
        db.session.commit()
        log_access(g.current_user, "delete", "角色管理", "删除角色: " + rname)
        flash("角色已删除", "info")
        return redirect(url_for("role_list"))

    @app.route("/api/users/permission/<string:perm_code>")
    @login_required
    @permission_required("user_manage")
    def users_by_permission(perm_code):
        users = User.query.join(Role).outerjoin(Department).all()
        result = []
        for user in users:
            if user.role and user.role.has_permission(perm_code):
                result.append({
                    "id": user.id,
                    "username": user.username,
                    "real_name": user.real_name,
                    "role_name": user.role.name,
                    "dept_name": user.department.name if user.department else None,
                })
        return jsonify(result)

    @app.route("/api/users/role/<int:role_id>")
    @login_required
    @permission_required("user_manage")
    def users_by_role(role_id):
        users = User.query.filter_by(role_id=role_id).outerjoin(Department).all()
        result = []
        for user in users:
            result.append({
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "dept_name": user.department.name if user.department else None,
            })
        return jsonify(result)


# --------------------------------------------------------------------------- #
# 知识分类管理
# --------------------------------------------------------------------------- #

def register_category_routes(app: Flask):
    @app.route("/categories")
    @login_required
    def category_tree():
        categories = Category.query.order_by(Category.level, Category.sort_order).all()
        return render_template("category/tree.html", categories=categories)

    @app.route("/categories/create", methods=["GET", "POST"])
    @login_required
    @permission_required("category_manage")
    def category_create():
        form = CategoryForm()
        _populate_category_choices(form)
        if form.validate_on_submit():
            if Category.query.filter_by(code=form.code.data).first():
                flash("分类编码已存在", "danger")
                return render_template("category/edit.html", form=form, mode="create")
            cat = Category(
                name=form.name.data,
                code=form.code.data,
                parent_id=form.parent_id.data or None,
                sort_order=form.sort_order.data,
                description=form.description.data,
            )
            if cat.parent_id:
                parent = Category.query.get(cat.parent_id)
                cat.level = parent.level + 1 if parent else 1
            else:
                cat.level = 1
            db.session.add(cat)
            db.session.commit()
            log_access(g.current_user, "create", "分类管理", "新增分类: " + cat.name)
            flash("分类创建成功", "success")
            return redirect(url_for("category_tree"))
        return render_template("category/edit.html", form=form, mode="create")

    @app.route("/categories/<int:cid>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("category_manage")
    def category_edit(cid):
        cat = Category.query.get_or_404(cid)
        form = CategoryForm(obj=cat)
        _populate_category_choices(form, exclude_id=cid)
        if form.validate_on_submit():
            cat.name = form.name.data
            cat.code = form.code.data
            cat.parent_id = form.parent_id.data or None
            cat.sort_order = form.sort_order.data
            cat.description = form.description.data
            if cat.parent_id:
                parent = Category.query.get(cat.parent_id)
                cat.level = parent.level + 1 if parent else 1
            else:
                cat.level = 1
            db.session.commit()
            log_access(g.current_user, "update", "分类管理", "编辑分类: " + cat.name)
            flash("分类信息已更新", "success")
            return redirect(url_for("category_tree"))
        return render_template("category/edit.html", form=form, mode="edit", category=cat)

    @app.route("/categories/<int:cid>/delete", methods=["POST"])
    @login_required
    @permission_required("category_manage")
    def category_delete(cid):
        cat = Category.query.get_or_404(cid)
        if cat.entries.count() > 0 or cat.sub_categories:
            flash("该分类下有知识条目或子分类，无法删除", "danger")
            return redirect(url_for("category_tree"))
        cname = cat.name
        db.session.delete(cat)
        db.session.commit()
        log_access(g.current_user, "delete", "分类管理", "删除分类: " + cname)
        flash("分类已删除", "info")
        return redirect(url_for("category_tree"))

    @app.route("/categories/reorder", methods=["POST"])
    @login_required
    @permission_required("category_manage")
    def category_reorder():
        data = request.get_json()
        parent_id = data.get("parent_id", 0)
        order_ids = data.get("order_ids", [])
        
        for idx, cid in enumerate(order_ids):
            cat = Category.query.get(cid)
            if cat:
                cat.parent_id = parent_id if parent_id != 0 else None
                cat.sort_order = idx + 1
                if parent_id:
                    parent = Category.query.get(parent_id)
                    cat.level = parent.level + 1 if parent else 1
                else:
                    cat.level = 1
        db.session.commit()
        log_access(g.current_user, "update", "分类管理", "调整分类排序")
        return jsonify({"success": True})

    @app.route("/categories/<int:cid>/browse")
    @login_required
    def category_browse(cid):
        cat = Category.query.get_or_404(cid)
        page = request.args.get("page", 1, type=int)
        pagination = KnowledgeEntry.query.filter_by(
            category_id=cid, status="published"
        ).order_by(KnowledgeEntry.updated_at.desc()).paginate(
            page=page, per_page=app.config["PER_PAGE"], error_out=False
        )
        return render_template("category/browse.html", category=cat, entries=pagination.items, pagination=pagination)

    @app.route("/search")
    @login_required
    def search():
        keyword = request.args.get("q", "").strip()
        cat_id = request.args.get("cat", 0, type=int)
        page = request.args.get("page", 1, type=int)

        query = KnowledgeEntry.query.filter_by(status="published")
        if keyword:
            query = query.filter(
                db.or_(
                    KnowledgeEntry.title.contains(keyword),
                    KnowledgeEntry.summary.contains(keyword),
                    KnowledgeEntry.tags.contains(keyword),
                    KnowledgeEntry.definition.contains(keyword),
                )
            )
        if cat_id:
            query = query.filter_by(category_id=cat_id)

        pagination = query.order_by(KnowledgeEntry.updated_at.desc()).paginate(
            page=page, per_page=app.config["PER_PAGE"], error_out=False
        )
        categories = Category.query.order_by(Category.level, Category.sort_order).all()
        
        current_cat_name = ""
        if cat_id:
            cat = Category.query.get(cat_id)
            if cat:
                current_cat_name = cat.name

        log_access(g.current_user, "search", "知识检索", f"关键词:{keyword} 分类:{current_cat_name}")

        return render_template(
            "category/public_search.html",
            entries=pagination.items, pagination=pagination,
            keyword=keyword, cat_id=cat_id, categories=categories,
            current_cat_name=current_cat_name,
        )

    @app.route("/api/search/suggest")
    @login_required
    def search_suggest():
        keyword = request.args.get("q", "").strip()
        cat_id = request.args.get("cat", 0, type=int)

        if not keyword:
            return jsonify([])

        query = KnowledgeEntry.query.filter_by(status="published")
        if cat_id:
            query = query.filter_by(category_id=cat_id)
        
        query = query.filter(
            db.or_(
                KnowledgeEntry.title.contains(keyword),
                KnowledgeEntry.summary.contains(keyword),
            )
        ).order_by(KnowledgeEntry.updated_at.desc()).limit(10)

        results = []
        for entry in query.all():
            results.append({
                "id": entry.id,
                "title": entry.title,
                "category": entry.category.name if entry.category else "未分类",
            })
        return jsonify(results)

    @app.route("/entries/<int:eid>")
    @login_required
    def entry_detail(eid):
        entry = KnowledgeEntry.query.get_or_404(eid)
        log_access(g.current_user, "view", "知识查阅", "查看: " + entry.title)
        return render_template("category/detail.html", entry=entry)


# --------------------------------------------------------------------------- #
# 知识管理
# --------------------------------------------------------------------------- #

def register_knowledge_routes(app: Flask):
    @app.route("/knowledge")
    @login_required
    def knowledge_list():
        status = request.args.get("status", "")
        keyword = request.args.get("keyword", "").strip()
        page = request.args.get("page", 1, type=int)

        query = KnowledgeEntry.query
        if status:
            query = query.filter_by(status=status)
        if keyword:
            query = query.filter(KnowledgeEntry.title.contains(keyword))

        user = g.current_user
        if not user.role or (user.role.code != "admin" and not user.role.has_permission("knowledge_review")):
            query = query.filter_by(created_by=user.id)

        pagination = query.order_by(KnowledgeEntry.id.desc()).paginate(
            page=page, per_page=app.config["PER_PAGE"], error_out=False
        )
        return render_template(
            "knowledge/list.html",
            entries=pagination.items, pagination=pagination,
            status=status, keyword=keyword,
        )

    @app.route("/knowledge/create", methods=["GET", "POST"])
    @login_required
    @permission_required("knowledge_create")
    def knowledge_create():
        form = KnowledgeForm()
        _populate_knowledge_choices(form)
        if form.validate_on_submit():
            entry = KnowledgeEntry(
                title=form.title.data,
                category_id=form.category_id.data or None,
                summary=form.summary.data,
                definition=form.definition.data,
                etiology=form.etiology.data,
                clinical_manifestation=form.clinical_manifestation.data,
                diagnosis=form.diagnosis.data,
                treatment=form.treatment.data,
                prevention=form.prevention.data,
                references=form.references.data,
                tags=form.tags.data,
                source="manual",
                status="draft",
                created_by=g.current_user.id,
            )
            db.session.add(entry)
            db.session.commit()
            log_access(g.current_user, "create", "知识管理", "录入: " + entry.title)
            flash("知识条目已保存为草稿", "success")
            return redirect(url_for("knowledge_list"))
        return render_template("knowledge/edit.html", form=form, mode="create")

    @app.route("/knowledge/<int:eid>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("knowledge_edit")
    def knowledge_edit(eid):
        entry = KnowledgeEntry.query.get_or_404(eid)
        form = KnowledgeForm(obj=entry)
        _populate_knowledge_choices(form)
        if form.validate_on_submit():
            entry.title = form.title.data
            entry.category_id = form.category_id.data or None
            entry.summary = form.summary.data
            entry.definition = form.definition.data
            entry.etiology = form.etiology.data
            entry.clinical_manifestation = form.clinical_manifestation.data
            entry.diagnosis = form.diagnosis.data
            entry.treatment = form.treatment.data
            entry.prevention = form.prevention.data
            entry.references = form.references.data
            entry.tags = form.tags.data
            entry.version += 1
            entry.updated_at = datetime.now()
            db.session.commit()
            log_access(g.current_user, "update", "知识管理", "编辑: " + entry.title)
            flash("知识条目已更新", "success")
            return redirect(url_for("knowledge_list"))
        return render_template("knowledge/edit.html", form=form, mode="edit", entry=entry)

    @app.route("/knowledge/<int:eid>/submit", methods=["POST"])
    @login_required
    def knowledge_submit(eid):
        entry = KnowledgeEntry.query.get_or_404(eid)
        entry.status = "pending"
        db.session.commit()
        log_access(g.current_user, "submit", "知识管理", "提交审核: " + entry.title)
        flash("已提交审核", "info")
        return redirect(url_for("knowledge_list"))

    @app.route("/knowledge/review")
    @login_required
    @permission_required("knowledge_review")
    def knowledge_review_list():
        entries = KnowledgeEntry.query.filter_by(status="pending").order_by(
            KnowledgeEntry.updated_at.desc()
        ).all()
        return render_template("knowledge/review.html", entries=entries)

    @app.route("/knowledge/<int:eid>/approve", methods=["POST"])
    @login_required
    @permission_required("knowledge_review")
    def knowledge_approve(eid):
        entry = KnowledgeEntry.query.get_or_404(eid)
        entry.status = "published"
        entry.reviewed_by = g.current_user.id
        entry.reviewed_at = datetime.now()
        db.session.commit()
        log_access(g.current_user, "approve", "知识审核", "通过: " + entry.title)
        flash("审核通过，已发布", "success")
        return redirect(url_for("knowledge_review_list"))

    @app.route("/knowledge/<int:eid>/reject", methods=["POST"])
    @login_required
    @permission_required("knowledge_review")
    def knowledge_reject(eid):
        entry = KnowledgeEntry.query.get_or_404(eid)
        entry.status = "rejected"
        entry.reviewed_by = g.current_user.id
        entry.reviewed_at = datetime.now()
        db.session.commit()
        log_access(g.current_user, "reject", "知识审核", "驳回: " + entry.title)
        flash("已驳回", "warning")
        return redirect(url_for("knowledge_review_list"))

    @app.route("/knowledge/<int:eid>/delete", methods=["POST"])
    @login_required
    def knowledge_delete(eid):
        entry = KnowledgeEntry.query.get_or_404(eid)
        user = g.current_user
        if entry.created_by != user.id and (not user.role or user.role.code != "admin"):
            abort(403)
        title = entry.title
        db.session.delete(entry)
        db.session.commit()
        log_access(user, "delete", "知识管理", "删除: " + title)
        flash("知识条目已删除", "info")
        return redirect(url_for("knowledge_list"))


def _populate_knowledge_choices(form: KnowledgeForm):
    form.category_id.choices = [(0, "— 请选择 —")] + [
        (c.id, c.name) for c in Category.query.order_by(Category.level, Category.sort_order).all()
    ]


def _populate_category_choices(form, exclude_id=None):
    query = Category.query.order_by(Category.level, Category.sort_order)
    if exclude_id:
        query = query.filter(Category.id != exclude_id)
    form.parent_id.choices = [(0, "— 无上级分类 —")] + [
        (c.id, c.name) for c in query.all()
    ]


# --------------------------------------------------------------------------- #
# 模型配置与知识生成
# --------------------------------------------------------------------------- #

def register_model_routes(app: Flask):
    @app.route("/model/config")
    @login_required
    @permission_required("model_config")
    def model_config_list():
        configs = ModelConfig.query.order_by(ModelConfig.id).all()
        return render_template("knowledge/model_config.html", configs=configs)

    @app.route("/model/config/create", methods=["GET", "POST"])
    @login_required
    @permission_required("model_config")
    def model_config_create():
        form = ModelConfigForm()
        if form.validate_on_submit():
            if form.is_active.data:
                ModelConfig.query.update({ModelConfig.is_active: False})
            cfg = ModelConfig(
                name=form.name.data,
                api_url=form.api_url.data,
                api_key=form.api_key.data,
                model_name=form.model_name.data,
                temperature=form.temperature.data,
                max_tokens=form.max_tokens.data,
                is_active=form.is_active.data,
            )
            db.session.add(cfg)
            db.session.commit()
            log_access(g.current_user, "create", "模型配置", "新增: " + cfg.name)
            flash("模型配置已保存", "success")
            return redirect(url_for("model_config_list"))
        return render_template("knowledge/model_edit.html", form=form, mode="create")

    @app.route("/model/config/<int:cid>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("model_config")
    def model_config_edit(cid):
        cfg = ModelConfig.query.get_or_404(cid)
        form = ModelConfigForm(obj=cfg)
        if form.validate_on_submit():
            if form.is_active.data:
                ModelConfig.query.filter(ModelConfig.id != cid).update({ModelConfig.is_active: False})
            cfg.name = form.name.data
            cfg.api_url = form.api_url.data
            if form.api_key.data:
                cfg.api_key = form.api_key.data
            cfg.model_name = form.model_name.data
            cfg.temperature = form.temperature.data
            cfg.max_tokens = form.max_tokens.data
            cfg.is_active = form.is_active.data
            db.session.commit()
            log_access(g.current_user, "update", "模型配置", "编辑: " + cfg.name)
            flash("模型配置已更新", "success")
            return redirect(url_for("model_config_list"))
        form.api_key.data = ""
        return render_template("knowledge/model_edit.html", form=form, mode="edit", config=cfg)

    @app.route("/model/config/<int:cid>/activate", methods=["POST"])
    @login_required
    @permission_required("model_config")
    def model_config_activate(cid):
        cfg = ModelConfig.query.get_or_404(cid)
        ModelConfig.query.update({ModelConfig.is_active: False})
        cfg.is_active = True
        db.session.commit()
        log_access(g.current_user, "activate", "模型配置", "启用: " + cfg.name)
        flash("已切换为当前启用模型", "success")
        return redirect(url_for("model_config_list"))

    @app.route("/model/config/<int:cid>/delete", methods=["POST"])
    @login_required
    @permission_required("model_config")
    def model_config_delete(cid):
        cfg = ModelConfig.query.get_or_404(cid)
        name = cfg.name
        db.session.delete(cfg)
        db.session.commit()
        log_access(g.current_user, "delete", "模型配置", "删除: " + name)
        flash("模型配置已删除", "info")
        return redirect(url_for("model_config_list"))

    @app.route("/knowledge/generate", methods=["GET", "POST"])
    @login_required
    @permission_required("knowledge_generate")
    def knowledge_generate():
        form = KnowledgeGenerateForm()
        _populate_generate_choices(form)
        active_cfg = ModelConfig.query.filter_by(is_active=True).first()

        if form.validate_on_submit():
            if not active_cfg:
                flash("尚未配置启用的模型，请先在模型配置中设置", "danger")
                return render_template("knowledge/generate.html", form=form, active_cfg=active_cfg)

            title = form.title.data
            success, result = call_model(active_cfg, title)

            if not success:
                flash("生成失败: " + str(result), "danger")
                return render_template("knowledge/generate.html", form=form, active_cfg=active_cfg)

            session["gen_result"] = json.dumps(result, ensure_ascii=False)
            session["gen_title"] = title
            session["gen_category"] = form.category_id.data or 0

            log_access(g.current_user, "generate", "知识生成", "生成: " + title)
            return redirect(url_for("generate_preview"))

        return render_template("knowledge/generate.html", form=form, active_cfg=active_cfg)

    @app.route("/knowledge/generate-preview", methods=["GET", "POST"])
    @login_required
    @permission_required("knowledge_generate")
    def generate_preview():
        raw = session.get("gen_result")
        if not raw:
            flash("没有待预览的生成内容，请先执行生成", "warning")
            return redirect(url_for("knowledge_generate"))

        data = json.loads(raw)
        title = session.get("gen_title", "")
        cat_id = session.get("gen_category", 0)

        if request.method == "POST":
            action = request.form.get("action", "save")
            entry = KnowledgeEntry(
                title=request.form.get("title", title),
                category_id=int(request.form.get("category_id", 0)) or None,
                summary=request.form.get("summary", ""),
                definition=request.form.get("definition", ""),
                etiology=request.form.get("etiology", ""),
                clinical_manifestation=request.form.get("clinical_manifestation", ""),
                diagnosis=request.form.get("diagnosis", ""),
                treatment=request.form.get("treatment", ""),
                prevention=request.form.get("prevention", ""),
                references=request.form.get("references", ""),
                tags=request.form.get("tags", ""),
                source="generated",
                status="draft" if action == "save" else "pending",
                created_by=g.current_user.id,
            )
            db.session.add(entry)
            db.session.commit()
            session.pop("gen_result", None)
            session.pop("gen_title", None)
            session.pop("gen_category", None)
            log_access(g.current_user, "save", "知识生成", "保存: " + entry.title)
            flash("生成内容已保存" + ("并提交审核" if action == "submit" else "为草稿"), "success")
            return redirect(url_for("knowledge_list"))

        categories = Category.query.order_by(Category.level, Category.sort_order).all()
        return render_template(
            "knowledge/generate_preview.html", data=data, title=title, cat_id=cat_id, categories=categories
        )


def _populate_generate_choices(form: KnowledgeGenerateForm):
    form.category_id.choices = [(0, "— 请选择 —")] + [
        (c.id, c.name) for c in Category.query.order_by(Category.level, Category.sort_order).all()
    ]


# --------------------------------------------------------------------------- #
# 辅助功能：日志与统计
# --------------------------------------------------------------------------- #

def register_auxiliary_routes(app: Flask):
    @app.route("/logs")
    @login_required
    @permission_required("log_view")
    def log_list():
        keyword = request.args.get("keyword", "").strip()
        module = request.args.get("module", "")
        page = request.args.get("page", 1, type=int)

        query = AccessLog.query
        if keyword:
            query = query.filter(
                db.or_(AccessLog.username.contains(keyword), AccessLog.target.contains(keyword))
            )
        if module:
            query = query.filter_by(module=module)
        pagination = query.order_by(AccessLog.id.desc()).paginate(
            page=page, per_page=app.config["PER_PAGE"], error_out=False
        )
        modules = db.session.query(AccessLog.module).distinct().all()
        return render_template(
            "auxiliary/logs.html",
            logs=pagination.items, pagination=pagination,
            keyword=keyword, module=module,
            modules=[m[0] for m in modules if m[0]],
        )

    @app.route("/statistics")
    @login_required
    @permission_required("stat_view")
    def statistics():
        # 分类统计
        cat_stats = db.session.query(
            Category.name, db.func.count(KnowledgeEntry.id)
        ).outerjoin(KnowledgeEntry).group_by(Category.id).all()

        # 状态统计
        status_stats = db.session.query(
            KnowledgeEntry.status, db.func.count(KnowledgeEntry.id)
        ).group_by(KnowledgeEntry.status).all()

        # 近7日访问趋势
        trend = []
        for i in range(6, -1, -1):
            day = datetime.now().date() - timedelta(days=i)
            count = AccessLog.query.filter(
                db.func.date(AccessLog.created_at) == day
            ).count()
            trend.append({"date": day.strftime("%m-%d"), "count": count})

        # 活跃用户 TOP5
        top_users = db.session.query(
            User.real_name, db.func.count(AccessLog.id)
        ).join(AccessLog, AccessLog.user_id == User.id).group_by(User.id).order_by(
            db.func.count(AccessLog.id).desc()
        ).limit(5).all()

        # 知识检索排名统计（按分类统计搜索次数，按知识条目统计查看次数）
        search_stats = db.session.query(
            AccessLog.detail, db.func.count(AccessLog.id)
        ).filter(
            AccessLog.module == "知识检索",
            AccessLog.action == "search"
        ).group_by(AccessLog.detail).order_by(
            db.func.count(AccessLog.id).desc()
        ).limit(20).all()

        view_stats = db.session.query(
            AccessLog.target, db.func.count(AccessLog.id)
        ).filter(
            AccessLog.module == "知识查阅",
            AccessLog.action == "view"
        ).group_by(AccessLog.target).order_by(
            db.func.count(AccessLog.id).desc()
        ).limit(20).all()

        category_search_stats = []
        categories = Category.query.order_by(Category.level, Category.sort_order).all()
        for cat in categories:
            if cat.level == 1:
                children = [c for c in categories if c.parent_id == cat.id]
                cat_search_count = AccessLog.query.filter(
                    AccessLog.module == "知识检索",
                    AccessLog.action == "search",
                    AccessLog.detail.contains(cat.name)
                ).count()
                child_stats = []
                for child in children:
                    child_count = AccessLog.query.filter(
                        AccessLog.module == "知识检索",
                        AccessLog.action == "search",
                        AccessLog.detail.contains(child.name)
                    ).count()
                    child_stats.append({
                        "id": child.id,
                        "name": child.name,
                        "count": child_count,
                    })
                category_search_stats.append({
                    "id": cat.id,
                    "name": cat.name,
                    "count": cat_search_count,
                    "children": child_stats,
                })

        return render_template(
            "auxiliary/statistics.html",
            cat_stats=cat_stats, status_stats=status_stats,
            trend=trend, top_users=top_users,
            search_stats=search_stats,
            view_stats=view_stats,
            category_search_stats=category_search_stats,
        )


# --------------------------------------------------------------------------- #
# 模板辅助函数
# --------------------------------------------------------------------------- #

def register_template_helpers(app: Flask):
    @app.template_filter("fmt_date")
    def fmt_date(value):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        return value.strftime("%Y-%m-%d %H:%M")

    @app.template_filter("status_label")
    def status_label(value):
        mapping = {
            "draft": "草稿",
            "pending": "待审核",
            "published": "已发布",
            "rejected": "已驳回",
        }
        return mapping.get(value, value)


# --------------------------------------------------------------------------- #
# 初始化默认数据
# --------------------------------------------------------------------------- #

def seed_default_data(app: Flask):
    """首次启动时写入默认管理员、角色、科室与分类"""
    if Role.query.count() == 0:
        admin_role = Role(
            name="系统管理员", code="admin",
            permissions=",".join([
                "user_manage", "dept_manage", "role_manage",
                "knowledge_create", "knowledge_edit", "knowledge_review",
                "knowledge_generate", "category_manage", "log_view", "stat_view", "model_config",
            ]),
            remark="拥有全部权限",
        )
        editor_role = Role(
            name="知识编辑", code="editor",
            permissions="knowledge_create,knowledge_edit,knowledge_generate,category_manage",
            remark="知识录入与编辑",
        )
        reviewer_role = Role(
            name="审核员", code="reviewer",
            permissions="knowledge_review,stat_view,log_view",
            remark="知识审核",
        )
        db.session.add_all([admin_role, editor_role, reviewer_role])

    if Department.query.count() == 0:
        depts = [
            Department(name="医务部", code="MED", sort_order=1),
            Department(name="内科", code="INT", sort_order=2),
            Department(name="外科", code="SUR", sort_order=3),
            Department(name="急诊科", code="EMG", sort_order=4),
            Department(name="药剂科", code="PHA", sort_order=5),
        ]
        db.session.add_all(depts)

    if User.query.count() == 0:
        admin = User(
            username="admin", real_name="系统管理员",
            email="admin@mks.local", phone="13800000000",
            department_id=1, role_id=1, status="active",
        )
        admin.set_password("admin123")
        db.session.add(admin)

    if Category.query.count() == 0:
        cats = [
            Category(name="疾病", code="DISEASE", level=1, sort_order=1, description="疾病相关知识"),
            Category(name="药品", code="MEDICINE", level=1, sort_order=2, description="药品相关知识"),
            Category(name="检查", code="EXAM", level=1, sort_order=3, description="检查相关知识"),
            Category(name="检验", code="LAB", level=1, sort_order=4, description="检验相关知识"),
            Category(name="手术", code="SURGERY", level=1, sort_order=5, description="手术相关知识"),
            Category(name="麻醉", code="ANESTHESIA", level=1, sort_order=6, description="麻醉相关知识"),
            Category(name="健康宣教", code="HEALTH_EDU", level=1, sort_order=7, description="健康宣教知识"),
        ]
        db.session.add_all(cats)

    db.session.commit()


# --------------------------------------------------------------------------- #
# 启动入口
# --------------------------------------------------------------------------- #

app = create_app(os.environ.get("MKS_ENV", "development"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
