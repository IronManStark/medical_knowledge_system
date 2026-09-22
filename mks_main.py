import os
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, redirect, url_for, request, session,
    flash, jsonify, abort, g, send_file, Response,
)
from PIL import Image, ImageDraw, ImageFont
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text

from peizhi import JichuShezhi
from mks_models import (
    shujuku, Department, Role, User, Category, KnowledgeEntry,
    KnowledgeFile, KnowledgeTemplate, ModelConfig, AccessLog, SystemSetting,
    KnowledgeAlias, KnowledgeLink,
)
from biaodan import (
    DengluBiao, YonghuBiao, KeshiBiao, JueseBiao, FenleiBiao,
    ZhishiBiao, MoxingPeizhiBiao, ShengchengBiao,
)
from gongju import jilu_caozuo, xie_wenben_rizhi
from gongju.diao_moxing import qingqiu_moxing, TISHICI as MOREN_TISHICI
from gongju.minio_help import (
    pin_dao_minio, qu_liu_cong_minio, shanchu_minio, shezhi_minio,
)


def qidong_chengxu():
    cdb_app = Flask(__name__)
    cdb_app.config.from_object(JichuShezhi)

    os.makedirs(cdb_app.config.get("UPLOAD_FOLDER", "data/uploads"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

    shujuku.init_app(cdb_app)
    CSRFProtect(cdb_app)

    shezhi_minio(
        dizhi=cdb_app.config.get("MINIO_DIZHI", "10.211.55.4:9000"),
        yonghu=cdb_app.config.get("MINIO_YONGHU", "admin"),
        kouling=cdb_app.config.get("MINIO_KOULING", ""),
        tong=cdb_app.config.get("MINIO_TONG", "mks"),
        anquan=cdb_app.config.get("MINIO_ANQUAN", False),
    )

    zhuang_shang_xiawen(cdb_app)
    gua_denglu_luyou(cdb_app)
    gua_shouye_luyou(cdb_app)
    gua_yonghu_luyou(cdb_app)
    gua_keshi_luyou(cdb_app)
    gua_juese_luyou(cdb_app)
    gua_fenlei_luyou(cdb_app)
    gua_zhishi_luyou(cdb_app)
    gua_moxing_luyou(cdb_app)
    gua_fuzhu_luyou(cdb_app)
    gua_tupu_luyou(cdb_app)
    gua_moban_guolv(cdb_app)

    with cdb_app.app_context():
        shujuku.create_all()
        moren_shuju(cdb_app)

    return cdb_app


def zhuang_shang_xiawen(chengxu):
    @chengxu.before_request
    def _ren_denglu_ma():
        yhid = session.get("yonghu_id")
        g.dangqian_yonghu = None
        if yhid:
            g.dangqian_yonghu = User.query.get(yhid)

    @chengxu.context_processor
    def _sai_dian_quanju():
        return {
            "current_user": g.dangqian_yonghu,
            "current_year": datetime.now().year,
        }

    @chengxu.after_request
    def _bucun_huancun(xiangying):
        lei = xiangying.content_type or ""
        if lei.startswith("text/html"):
            xiangying.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            xiangying.headers["Pragma"] = "no-cache"
            xiangying.headers["Expires"] = "0"
        return xiangying


def xuyao_denglu(fn):
    @wraps(fn)
    def _chan_rao(*canshu, **mingming):
        if not g.dangqian_yonghu:
            flash("请先登录系统", "warning")
            return redirect(url_for("dengluye", next=request.full_path))
        return fn(*canshu, **mingming)
    return _chan_rao


def xuyao_quanxian(quanxian_ma):
    def _bao_yi_ceng(fn):
        @wraps(fn)
        def _kao_yan(*canshu, **mingming):
            yh = g.dangqian_yonghu
            if not yh or not yh.role:
                abort(403)
            if not yh.role.shifou_youquan(quanxian_ma) and yh.role.code != "admin":
                flash("您没有该功能的操作权限", "danger")
                return redirect(diyi_ge_yexian(yh))
            return fn(*canshu, **mingming)
        return _kao_yan
    return _bao_yi_ceng


class YeJiao:
    def __init__(self, jilu_liebiao, dangqian_ye, zong_tiao, meiye):
        self.items = jilu_liebiao
        self.page = dangqian_ye
        self.total = zong_tiao
        zong_ye = (zong_tiao + meiye - 1) // meiye if meiye > 0 else 1
        self.pages = zong_ye if zong_ye >= 1 else 1
        self.has_prev = dangqian_ye > 1
        self.has_next = dangqian_ye < self.pages
        self.prev_num = dangqian_ye - 1 if self.has_prev else None
        self.next_num = dangqian_ye + 1 if self.has_next else None


def shougong_fenye(chaxun, yema, meiye_tiao):
    if yema < 1:
        yema = 1
    zongshu = chaxun.count()
    tiao = chaxun.limit(meiye_tiao).offset((yema - 1) * meiye_tiao).all()
    return YeJiao(tiao, yema, zongshu, meiye_tiao)


def hua_yanzhengma():
    kuzi = string.digits + string.ascii_uppercase
    da_an = "".join(random.sample(kuzi, 4))
    hua_bu = Image.new("RGB", (120, 40), (255, 255, 255))
    bi = ImageDraw.Draw(hua_bu)
    try:
        zi_ti = ImageFont.truetype("/Library/Fonts/Arial.ttf", 30)
    except Exception:
        zi_ti = ImageFont.load_default()
    for i, zifu in enumerate(da_an):
        yanse = (random.randint(0, 150), random.randint(0, 150), random.randint(0, 150))
        bi.text((10 + i * 28, 5), zifu, font=zi_ti, fill=yanse)
    for _ in range(5):
        qi = (random.randint(0, 120), random.randint(0, 40))
        zhong = (random.randint(0, 120), random.randint(0, 40))
        bi.line([qi, zhong], fill=(200, 200, 200), width=1)
    for _ in range(20):
        bi.point((random.randint(0, 120), random.randint(0, 40)),
                 fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    huan_cun = BytesIO()
    hua_bu.save(huan_cun, "JPEG")
    huan_cun.seek(0)
    return da_an, huan_cun


def gua_denglu_luyou(chengxu):

    @chengxu.route("/", methods=["GET"])
    def shouye_tiaozhuan():
        if g.dangqian_yonghu:
            return redirect(url_for("zhuye"))
        return redirect(url_for("dengluye"))

    @chengxu.route("/captcha")
    def yanzhengma():
        da_an, liu = hua_yanzhengma()
        session["yzm"] = da_an
        return send_file(liu, mimetype="image/jpeg")

    @chengxu.route("/login", methods=["GET", "POST"])
    def dengluye():
        if g.dangqian_yonghu:
            return redirect(url_for("zhuye"))
        biao = DengluBiao()
        if biao.validate_on_submit():
            shu_ru = biao.captcha.data.upper()
            cun_zai = session.get("yzm", "").upper()
            if shu_ru != cun_zai:
                flash("验证码不正确", "danger")
                return render_template("login.html", form=biao)

            yh = User.query.filter_by(username=biao.username.data).first()
            if not yh:
                flash("账号或口令不正确", "danger")
                return render_template("login.html", form=biao)

            if yh.shifou_suoding():
                sheng = (yh.lock_time - datetime.now()).total_seconds() // 60
                flash("账号已被锁定，请%d分钟后重试" % int(sheng), "danger")
                return render_template("login.html", form=biao)

            if yh.status != "active":
                flash("该账号已被停用，请联系管理员", "danger")
                return render_template("login.html", form=biao)

            if not yh.yanzheng_mima(biao.password.data):
                yh.failed_attempts += 1
                if yh.failed_attempts >= 5:
                    yh.lock_time = datetime.now() + timedelta(minutes=15)
                    yh.failed_attempts = 0
                    shujuku.session.commit()
                    flash("连续5次密码错误，账号已被锁定，15分钟后自动解锁", "danger")
                else:
                    shujuku.session.commit()
                    flash("账号或口令不正确，密码已错误%d次，连续错误5次需要15分钟后重试" % yh.failed_attempts, "danger")
                return render_template("login.html", form=biao)

            yh.failed_attempts = 0
            yh.lock_time = None
            session.permanent = True
            chengxu.permanent_session_lifetime = timedelta(hours=chengxu.config["SESSION_LIFETIME_HOURS"])
            session["yonghu_id"] = yh.id
            yh.last_login = datetime.now()
            shujuku.session.commit()
            session.pop("yzm", None)
            jilu_caozuo(yh, "login", "认证", "用户登录")
            xie_wenben_rizhi("用户 %s 登录系统" % yh.username)
            flash("登录成功，欢迎回来", "success")
            jie_kou = request.args.get("next")
            return redirect(jie_kou or diyi_ge_yexian(yh))
        return render_template("login.html", form=biao)

    @chengxu.route("/logout")
    def tuichu():
        yh = g.dangqian_yonghu
        if yh:
            jilu_caozuo(yh, "logout", "认证", "用户退出")
        session.clear()
        flash("您已安全退出系统", "info")
        return redirect(url_for("dengluye"))

    @chengxu.route("/change-password", methods=["POST"])
    @xuyao_denglu
    def gaimima():
        yh = g.dangqian_yonghu
        jiu_de = request.form.get("old_password", "").strip()
        xin_de = request.form.get("new_password", "").strip()
        zai_shu = request.form.get("confirm_password", "").strip()

        if not yh.yanzheng_mima(jiu_de):
            flash("原密码不正确", "danger")
            return redirect(request.referrer or url_for("zhuye"))
        if len(xin_de) < 6:
            flash("新密码长度至少6位", "danger")
            return redirect(request.referrer or url_for("zhuye"))
        if xin_de != zai_shu:
            flash("两次输入的新密码不一致", "danger")
            return redirect(request.referrer or url_for("zhuye"))

        yh.shezhi_mima(xin_de)
        shujuku.session.commit()
        jilu_caozuo(yh, "update", "人员维护", "修改密码")
        flash("密码修改成功，请重新登录", "success")
        session.clear()
        return redirect(url_for("dengluye"))


def gua_shouye_luyou(chengxu):
    @chengxu.route("/dashboard")
    @xuyao_denglu
    def zhuye():
        yh = g.dangqian_yonghu
        if yh and yh.role and yh.role.code != "admin":
            if not yh.role.shifou_youquan("home_view"):
                return redirect(diyi_ge_yexian(yh))
        rs = dict()
        rs["users"] = User.query.count()
        rs["entries"] = KnowledgeEntry.query.count()
        rs["published"] = KnowledgeEntry.query.filter_by(status="published").count()
        rs["pending"] = KnowledgeEntry.query.filter_by(status="pending").count()
        rs["categories"] = Category.query.count()

        ling_dian = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        rs["today_logs"] = AccessLog.query.filter(AccessLog.created_at >= ling_dian).count()

        rs["db_type"] = "MySQL"
        return render_template("dashboard.html", stats=rs)


def tian_yonghu_xuanxiang(biao):
    biao.department_id.choices = [(0, "— 请选择 —")] + [
        (d.id, d.name) for d in Department.query.order_by(Department.sort_order).all()
    ]
    biao.role_id.choices = [(0, "— 请选择 —")] + [
        (r.id, r.name) for r in Role.query.order_by(Role.id).all()
    ]


def gua_yonghu_luyou(chengxu):
    @chengxu.route("/users")
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def yonghu_liebiao():
        guan_jian = request.args.get("keyword", "").strip()
        ks_id = request.args.get("dept", 0, type=int)
        yema = request.args.get("page", 1, type=int)

        chaxun = User.query
        if guan_jian:
            chaxun = chaxun.filter(
                shujuku.or_(User.username.contains(guan_jian), User.real_name.contains(guan_jian))
            )
        if ks_id:
            chaxun = chaxun.filter_by(department_id=ks_id)
        fenye = chaxun.order_by(User.id.desc()).paginate(
            page=yema, per_page=chengxu.config["PER_PAGE"], error_out=False
        )
        ks_all = Department.query.order_by(Department.sort_order).all()
        return render_template(
            "users/list.html",
            users=fenye.items, pagination=fenye,
            keyword=guan_jian, dept_id=ks_id, departments=ks_all,
        )

    @chengxu.route("/users/create", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def yonghu_xinzeng():
        biao = YonghuBiao()
        tian_yonghu_xuanxiang(biao)
        if biao.validate_on_submit():
            if User.query.filter_by(username=biao.username.data).first():
                flash("该登录账号已存在", "danger")
                return render_template("users/edit.html", form=biao, mode="create")
            yh = User(
                username=biao.username.data,
                real_name=biao.real_name.data,
                email=biao.email.data,
                phone=biao.phone.data,
                department_id=biao.department_id.data or None,
                role_id=biao.role_id.data or None,
                status=biao.status.data,
            )
            yh.shezhi_mima(biao.password.data or "123456")
            shujuku.session.add(yh)
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "create", "人员维护", "新增用户: " + yh.username)
            flash("用户创建成功", "success")
            return redirect(url_for("yonghu_liebiao"))
        return render_template("users/edit.html", form=biao, mode="create")

    @chengxu.route("/users/<int:uid>/edit", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def yonghu_bianji(uid):
        yh = User.query.get_or_404(uid)
        biao = YonghuBiao(obj=yh)
        tian_yonghu_xuanxiang(biao)
        if biao.validate_on_submit():
            yh.real_name = biao.real_name.data
            yh.email = biao.email.data
            yh.phone = biao.phone.data
            yh.department_id = biao.department_id.data or None
            yh.role_id = biao.role_id.data or None
            yh.status = biao.status.data
            if biao.password.data:
                yh.shezhi_mima(biao.password.data)
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "update", "人员维护", "编辑用户: " + yh.username)
            flash("用户信息已更新", "success")
            return redirect(url_for("yonghu_liebiao"))
        biao.password.data = ""
        return render_template("users/edit.html", form=biao, mode="edit", user=yh)

    @chengxu.route("/users/<int:uid>/delete", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def yonghu_shanchu(uid):
        yh = User.query.get_or_404(uid)
        if yh.id == g.dangqian_yonghu.id:
            flash("不能删除当前登录账号", "danger")
            return redirect(url_for("yonghu_liebiao"))
        jiao_sha = yh.username
        shujuku.session.delete(yh)
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "delete", "人员维护", "删除用户: " + jiao_sha)
        flash("用户已删除", "info")
        return redirect(url_for("yonghu_liebiao"))

    @chengxu.route("/users/<int:uid>/unlock", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def yonghu_jiesuo(uid):
        yh = User.query.get_or_404(uid)
        yh.lock_time = None
        yh.failed_attempts = 0
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "update", "人员维护", "解锁账号: " + yh.username)
        flash("已解锁账号 %s，该用户现在可以正常登录" % yh.username, "success")
        return redirect(url_for("yonghu_liebiao"))


def tian_keshi_xuanxiang(biao, paichu=None):
    chaxun = Department.query
    if paichu:
        chaxun = chaxun.filter(Department.id != paichu)
    biao.parent_id.choices = [(0, "— 顶级科室 —")] + [
        (d.id, d.name) for d in chaxun.order_by(Department.sort_order).all()
    ]


def gua_keshi_luyou(chengxu):
    @chengxu.route("/departments")
    @xuyao_denglu
    @xuyao_quanxian("dept_manage")
    def keshi_liebiao():
        ks_all = Department.query.order_by(Department.sort_order, Department.id).all()
        return render_template("users/departments.html", departments=ks_all)

    @chengxu.route("/departments/create", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("dept_manage")
    def keshi_xinzeng():
        biao = KeshiBiao()
        tian_keshi_xuanxiang(biao)
        if biao.validate_on_submit():
            if Department.query.filter_by(code=biao.code.data).first():
                flash("科室编码已存在", "danger")
                return render_template("users/dept_edit.html", form=biao, mode="create")
            ks = Department(
                name=biao.name.data,
                code=biao.code.data,
                parent_id=biao.parent_id.data or None,
                sort_order=biao.sort_order.data,
                remark=biao.remark.data,
            )
            shujuku.session.add(ks)
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "create", "科室维护", "新增科室: " + ks.name)
            flash("科室创建成功", "success")
            return redirect(url_for("keshi_liebiao"))
        return render_template("users/dept_edit.html", form=biao, mode="create")

    @chengxu.route("/departments/<int:did>/edit", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("dept_manage")
    def keshi_bianji(did):
        ks = Department.query.get_or_404(did)
        biao = KeshiBiao(obj=ks)
        tian_keshi_xuanxiang(biao, paichu=did)
        if biao.validate_on_submit():
            ks.name = biao.name.data
            ks.code = biao.code.data
            ks.parent_id = biao.parent_id.data or None
            ks.sort_order = biao.sort_order.data
            ks.remark = biao.remark.data
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "update", "科室维护", "编辑科室: " + ks.name)
            flash("科室信息已更新", "success")
            return redirect(url_for("keshi_liebiao"))
        return render_template("users/dept_edit.html", form=biao, mode="edit", dept=ks)

    @chengxu.route("/departments/<int:did>/delete", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("dept_manage")
    def keshi_shanchu(did):
        ks = Department.query.get_or_404(did)
        if ks.users.count() > 0:
            flash("该科室下仍有人员，无法删除", "danger")
            return redirect(url_for("keshi_liebiao"))
        jiao_sha = ks.name
        shujuku.session.delete(ks)
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "delete", "科室维护", "删除科室: " + jiao_sha)
        flash("科室已删除", "info")
        return redirect(url_for("keshi_liebiao"))


QUANXIAN_MULU = [
    {
        "name": "概览", "code": "overview",
        "children": [
            ("home_view", "系统首页"),
        ],
    },
    {
        "name": "知识管理", "code": "knowledge",
        "children": [
            ("category_manage", "知识分类"),
            ("model_config", "模型配置"),
            ("knowledge_generate", "知识生成"),
            ("knowledge_create", "知识录入"),
            ("knowledge_review", "知识审核"),
            ("knowledge_edit", "知识列表"),
        ],
    },
    {
        "name": "分类查阅", "code": "browse",
        "children": [
            ("search_view", "知识检索"),
            ("graph_view", "图谱查询"),
        ],
    },
    {
        "name": "用户管理", "code": "system",
        "children": [
            ("user_manage", "人员维护"),
            ("dept_manage", "科室维护"),
            ("role_manage", "权限维护"),
        ],
    },
    {
        "name": "辅助功能", "code": "tools",
        "children": [
            ("stat_view", "统计分析"),
            ("log_view", "系统日志"),
        ],
    },
]

QUANXIAN_LUYOU = {
    "home_view": "zhuye",
    "category_manage": "fenlei_zongshu",
    "model_config": "moxing_liebiao",
    "knowledge_generate": "wo_de_shengcheng",
    "knowledge_create": "wo_de_zhishi",
    "knowledge_review": "shenhe_liebiao",
    "knowledge_edit": "zhishi_liebiao",
    "search_view": "jiansuo",
    "graph_view": "zhishi_tupu",
    "user_manage": "yonghu_liebiao",
    "dept_manage": "keshi_liebiao",
    "role_manage": "juese_liebiao",
    "stat_view": "tongji_fenxi",
    "log_view": "rizhi_liebiao",
}


def diyi_ge_yexian(yh):
    if not yh or not yh.role:
        return url_for("zhuye")
    if yh.role.code == "admin":
        return url_for("zhuye")
    for zu in QUANXIAN_MULU:
        for ma, _ in zu["children"]:
            if yh.role.shifou_youquan(ma):
                dian = QUANXIAN_LUYOU.get(ma)
                if dian:
                    return url_for(dian)
    return url_for("zhuye")


def gua_juese_luyou(chengxu):
    @chengxu.route("/roles")
    @xuyao_denglu
    @xuyao_quanxian("role_manage")
    def juese_liebiao():
        js_all = Role.query.order_by(Role.id).all()
        return render_template("users/roles.html", roles=js_all, catalog=QUANXIAN_MULU)

    @chengxu.route("/roles/create", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("role_manage")
    def juese_xinzeng():
        biao = JueseBiao()
        if biao.validate_on_submit():
            if Role.query.filter_by(code=biao.code.data).first():
                flash("角色编码已存在", "danger")
                return render_template("users/role_edit.html", form=biao, mode="create", catalog=QUANXIAN_MULU)
            gou_xuan = request.form.getlist("permissions")
            if not gou_xuan:
                flash("请至少选择一个功能菜单权限", "danger")
                return render_template("users/role_edit.html", form=biao, mode="create", catalog=QUANXIAN_MULU)
            js = Role(
                name=biao.name.data,
                code=biao.code.data,
                permissions=",".join(gou_xuan),
                remark=biao.remark.data,
            )
            shujuku.session.add(js)
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "create", "权限维护", "新增角色: " + js.name)
            flash("角色创建成功", "success")
            return redirect(url_for("juese_liebiao"))
        return render_template("users/role_edit.html", form=biao, mode="create", catalog=QUANXIAN_MULU)

    @chengxu.route("/roles/<int:rid>/edit", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("role_manage")
    def juese_bianji(rid):
        js = Role.query.get_or_404(rid)
        biao = JueseBiao(obj=js)
        if biao.validate_on_submit():
            gou_xuan = request.form.getlist("permissions")
            if not gou_xuan:
                flash("请至少选择一个功能菜单权限", "danger")
                return render_template("users/role_edit.html", form=biao, mode="edit", role=js, catalog=QUANXIAN_MULU)
            js.name = biao.name.data
            js.code = biao.code.data
            js.permissions = ",".join(gou_xuan)
            js.remark = biao.remark.data
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "update", "权限维护", "编辑角色: " + js.name)
            flash("角色信息已更新", "success")
            return redirect(url_for("juese_liebiao"))
        return render_template("users/role_edit.html", form=biao, mode="edit", role=js, catalog=QUANXIAN_MULU)

    @chengxu.route("/roles/<int:rid>/delete", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("role_manage")
    def juese_shanchu(rid):
        js = Role.query.get_or_404(rid)
        if js.users.count() > 0:
            flash("该角色下仍有用户，无法删除", "danger")
            return redirect(url_for("juese_liebiao"))
        jiao_sha = js.name
        shujuku.session.delete(js)
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "delete", "权限维护", "删除角色: " + jiao_sha)
        flash("角色已删除", "info")
        return redirect(url_for("juese_liebiao"))

    @chengxu.route("/api/users/permission/<string:quanxian_ma>")
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def gen_quanxian_chayonghu(quanxian_ma):
        quan = User.query.join(Role).outerjoin(Department).all()
        jie_guo = []
        for yh in quan:
            if yh.role and yh.role.shifou_youquan(quanxian_ma):
                jie_guo.append({
                    "id": yh.id,
                    "username": yh.username,
                    "real_name": yh.real_name,
                    "role_name": yh.role.name,
                    "dept_name": yh.department.name if yh.department else None,
                })
        return jsonify(jie_guo)

    @chengxu.route("/api/users/role/<int:role_id>")
    @xuyao_denglu
    @xuyao_quanxian("user_manage")
    def gen_juese_chayonghu(role_id):
        quan = User.query.filter_by(role_id=role_id).outerjoin(Department).all()
        jie_guo = []
        for yh in quan:
            jie_guo.append({
                "id": yh.id,
                "username": yh.username,
                "real_name": yh.real_name,
                "dept_name": yh.department.name if yh.department else None,
            })
        return jsonify(jie_guo)


def tian_fenlei_shangji(biao, paichu=None):
    chaxun = Category.query.order_by(Category.level, Category.sort_order)
    if paichu:
        chaxun = chaxun.filter(Category.id != paichu)
    biao.parent_id.choices = [(0, "— 无上级分类 —")] + [
        (c.id, c.name) for c in chaxun.all()
    ]


def tian_zhishi_fenlei(biao):
    biao.category_id.choices = [(0, "— 请选择 —")] + [
        (c.id, c.name) for c in Category.query.order_by(Category.level, Category.sort_order).all()
    ]


def gua_fenlei_luyou(chengxu):
    @chengxu.route("/categories")
    @xuyao_denglu
    def fenlei_zongshu():
        fl = Category.query.order_by(Category.level, Category.sort_order).all()
        return render_template("category/tree.html", categories=fl)

    @chengxu.route("/categories/create", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("category_manage")
    def fenlei_xinzeng():
        biao = FenleiBiao()
        tian_fenlei_shangji(biao)
        if biao.validate_on_submit():
            if Category.query.filter_by(code=biao.code.data).first():
                flash("分类编码已存在", "danger")
                return render_template("category/edit.html", form=biao, mode="create")
            fl = Category(
                name=biao.name.data,
                code=biao.code.data,
                parent_id=biao.parent_id.data or None,
                sort_order=biao.sort_order.data,
                description=biao.description.data,
            )
            if fl.parent_id:
                die = Category.query.get(fl.parent_id)
                fl.level = die.level + 1 if die else 1
            else:
                fl.level = 1
            shujuku.session.add(fl)
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "create", "知识分类", "新增分类: " + fl.name)
            flash("分类创建成功", "success")
            return redirect(url_for("fenlei_zongshu"))
        return render_template("category/edit.html", form=biao, mode="create")

    @chengxu.route("/categories/<int:cid>/edit", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("category_manage")
    def fenlei_bianji(cid):
        fl = Category.query.get_or_404(cid)
        biao = FenleiBiao(obj=fl)
        tian_fenlei_shangji(biao, paichu=cid)
        if biao.validate_on_submit():
            fl.name = biao.name.data
            fl.code = biao.code.data
            fl.parent_id = biao.parent_id.data or None
            fl.sort_order = biao.sort_order.data
            fl.description = biao.description.data
            if fl.parent_id:
                die = Category.query.get(fl.parent_id)
                fl.level = die.level + 1 if die else 1
            else:
                fl.level = 1
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "update", "知识分类", "编辑分类: " + fl.name)
            flash("分类信息已更新", "success")
            return redirect(url_for("fenlei_zongshu"))
        return render_template("category/edit.html", form=biao, mode="edit", category=fl)

    @chengxu.route("/categories/<int:cid>/delete", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("category_manage")
    def fenlei_shanchu(cid):
        fl = Category.query.get_or_404(cid)
        if fl.entries.count() > 0 or fl.sub_categories:
            flash("该分类下有知识条目或子分类，无法删除", "danger")
            return redirect(url_for("fenlei_zongshu"))
        jiao_sha = fl.name
        shujuku.session.delete(fl)
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "delete", "知识分类", "删除分类: " + jiao_sha)
        flash("分类已删除", "info")
        return redirect(url_for("fenlei_zongshu"))

    @chengxu.route("/categories/reorder", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("category_manage")
    def fenlei_paixu():
        bao = request.get_json()
        shangji = bao.get("parent_id", 0)
        shunxu = bao.get("order_ids", [])

        for xh, cid in enumerate(shunxu):
            fl = Category.query.get(cid)
            if fl:
                fl.parent_id = shangji if shangji != 0 else None
                fl.sort_order = xh + 1
                if shangji:
                    die = Category.query.get(shangji)
                    fl.level = die.level + 1 if die else 1
                else:
                    fl.level = 1
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "update", "知识分类", "调整分类排序")
        return jsonify({"success": True})

    @chengxu.route("/categories/<int:cid>/browse")
    @xuyao_denglu
    @xuyao_quanxian("search_view")
    def fenlei_liulan(cid):
        fl = Category.query.get_or_404(cid)
        yema = request.args.get("page", 1, type=int)
        fenye = KnowledgeEntry.query.filter_by(
            category_id=cid, status="published"
        ).order_by(KnowledgeEntry.updated_at.desc()).paginate(
            page=yema, per_page=chengxu.config["PER_PAGE"], error_out=False
        )
        return render_template("category/browse.html", category=fl, entries=fenye.items, pagination=fenye)

    @chengxu.route("/search")
    @xuyao_denglu
    @xuyao_quanxian("search_view")
    def jiansuo():
        guan_jian = request.args.get("q", "").strip()
        fl_id = request.args.get("cat", 0, type=int)
        yema = request.args.get("page", 1, type=int)

        chaxun = KnowledgeEntry.query.filter_by(status="published")
        if guan_jian:
            alias_hit_ids = []
            alias_rows = KnowledgeAlias.query.filter(KnowledgeAlias.alias_name.contains(guan_jian)).all()
            alias_hit_ids = [a.entry_id for a in alias_rows]
            chaxun = chaxun.filter(
                shujuku.or_(
                    KnowledgeEntry.title.contains(guan_jian),
                    KnowledgeEntry.summary.contains(guan_jian),
                    KnowledgeEntry.tags.contains(guan_jian),
                    KnowledgeEntry.definition.contains(guan_jian),
                    KnowledgeEntry.icd_code.contains(guan_jian),
                    KnowledgeEntry.id.in_(alias_hit_ids) if alias_hit_ids else KnowledgeEntry.id < 0,
                )
            )
        if fl_id:
            chaxun = chaxun.filter_by(category_id=fl_id)

        fenye = chaxun.order_by(KnowledgeEntry.updated_at.desc()).paginate(
            page=yema, per_page=chengxu.config["PER_PAGE"], error_out=False
        )
        fl_all = Category.query.order_by(Category.level, Category.sort_order).all()

        dangqian_ming = ""
        if fl_id:
            fl = Category.query.get(fl_id)
            if fl:
                dangqian_ming = fl.name

        jilu_caozuo(g.dangqian_yonghu, "search", "知识检索",
                    guan_jian or "(无关键词)",
                    "关键词:%s 分类:%s" % (guan_jian, dangqian_ming))

        return render_template(
            "category/public_search.html",
            entries=fenye.items, pagination=fenye,
            keyword=guan_jian, cat_id=fl_id, categories=fl_all,
            current_cat_name=dangqian_ming,
        )

    @chengxu.route("/api/search/suggest")
    @xuyao_denglu
    @xuyao_quanxian("search_view")
    def jiansuo_tishi():
        guan_jian = request.args.get("q", "").strip()
        fl_id = request.args.get("cat", 0, type=int)

        if not guan_jian:
            return jsonify([])

        chaxun = KnowledgeEntry.query.filter_by(status="published")
        if fl_id:
            chaxun = chaxun.filter_by(category_id=fl_id)
        chaxun = chaxun.filter(
            shujuku.or_(
                KnowledgeEntry.title.contains(guan_jian),
                KnowledgeEntry.summary.contains(guan_jian),
            )
        ).order_by(KnowledgeEntry.updated_at.desc()).limit(10)

        jie_guo = []
        for tiao in chaxun.all():
            jie_guo.append({
                "id": tiao.id,
                "title": tiao.title,
                "category": tiao.category.name if tiao.category else "未分类",
            })
        return jsonify(jie_guo)

    @chengxu.route("/entries/<int:eid>")
    @xuyao_denglu
    @xuyao_quanxian("search_view")
    def tiaomu_xiangqing(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        jilu_caozuo(g.dangqian_yonghu, "view", "知识检索", "查看: " + tm.title)
        return render_template("category/detail.html", entry=tm)


def _guanlian_linshi_wenjian(zhishi_id, wenjian_id_str=None):
    if wenjian_id_str:
        id_liebiao = [int(x) for x in wenjian_id_str.split(",") if x.strip().isdigit()]
    else:
        id_liebiao = [
            w.id for w in KnowledgeFile.query.filter(KnowledgeFile.entry_id.is_(None)).all()
        ]
    if id_liebiao:
        KnowledgeFile.query.filter(KnowledgeFile.id.in_(id_liebiao)).update(
            {KnowledgeFile.entry_id: zhishi_id}, synchronize_session=False
        )
        shujuku.session.commit()


def gua_zhishi_luyou(chengxu):
    @chengxu.route("/knowledge")
    @xuyao_denglu
    def zhishi_liebiao():
        zhuangtai = request.args.get("status", "")
        guan_jian = request.args.get("keyword", "").strip()
        yema = request.args.get("page", 1, type=int)
        ke_xuan = (10, 20, 50, 100)
        meiye = request.args.get("per_page", 20, type=int)
        if meiye not in ke_xuan:
            meiye = 20

        chaxun = KnowledgeEntry.query
        if zhuangtai == "tingyong":
            chaxun = chaxun.filter_by(yi_tingyong=True)
        elif zhuangtai == "published":
            chaxun = chaxun.filter_by(status="published")
        else:
            chaxun = chaxun.filter(
                shujuku.or_(KnowledgeEntry.status == "published", KnowledgeEntry.yi_tingyong == True)
            )
        if guan_jian:
            chaxun = chaxun.filter(KnowledgeEntry.title.contains(guan_jian))

        yh = g.dangqian_yonghu
        if not yh.role or (yh.role.code != "admin" and not yh.role.shifou_youquan("knowledge_review")):
            chaxun = chaxun.filter_by(created_by=yh.id)

        chaxun = chaxun.order_by(KnowledgeEntry.id.desc())
        fenye = shougong_fenye(chaxun, yema, meiye)
        return render_template(
            "knowledge/list.html",
            entries=fenye.items, pagination=fenye,
            status=zhuangtai, keyword=guan_jian, per_page=meiye,
            ke_xuan=ke_xuan,
        )

    @chengxu.route("/knowledge/mine")
    @xuyao_denglu
    def wo_de_zhishi():
        zhuangtai = request.args.get("status", "draft")
        guan_jian = request.args.get("keyword", "").strip()
        yema = request.args.get("page", 1, type=int)

        chaxun = KnowledgeEntry.query.filter_by(
            created_by=g.dangqian_yonghu.id, source="manual")
        if zhuangtai == "tingyong":
            chaxun = chaxun.filter_by(yi_tingyong=True)
        elif zhuangtai:
            chaxun = chaxun.filter_by(status=zhuangtai, yi_tingyong=False)
        if guan_jian:
            chaxun = chaxun.filter(KnowledgeEntry.title.contains(guan_jian))

        chaxun = chaxun.order_by(KnowledgeEntry.id.desc())
        fenye = chaxun.paginate(page=yema, per_page=chengxu.config["PER_PAGE"], error_out=False)
        return render_template(
            "knowledge/mine.html",
            entries=fenye.items, pagination=fenye,
            status=zhuangtai, keyword=guan_jian,
        )

    @chengxu.route("/knowledge/generated")
    @xuyao_denglu
    def wo_de_shengcheng():
        zhuangtai = request.args.get("status", "draft")
        guan_jian = request.args.get("keyword", "").strip()
        yema = request.args.get("page", 1, type=int)

        chaxun = KnowledgeEntry.query.filter_by(
            created_by=g.dangqian_yonghu.id, source="generated")
        if zhuangtai == "tingyong":
            chaxun = chaxun.filter_by(yi_tingyong=True)
        elif zhuangtai:
            chaxun = chaxun.filter_by(status=zhuangtai, yi_tingyong=False)
        if guan_jian:
            chaxun = chaxun.filter(KnowledgeEntry.title.contains(guan_jian))

        chaxun = chaxun.order_by(KnowledgeEntry.id.desc())
        fenye = chaxun.paginate(page=yema, per_page=chengxu.config["PER_PAGE"], error_out=False)
        return render_template(
            "knowledge/generated.html",
            entries=fenye.items, pagination=fenye,
            status=zhuangtai, keyword=guan_jian,
        )

    @chengxu.route("/knowledge/create", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_create")
    def zhishi_luru():
        biao = ZhishiBiao()
        tian_zhishi_fenlei(biao)
        if biao.validate_on_submit():
            tm = KnowledgeEntry(
                title=biao.title.data,
                category_id=biao.category_id.data or None,
                icd_code=(biao.icd_code.data or "").strip(),
                evidence_level=(biao.evidence_level.data or "").strip(),
                summary=biao.summary.data,
                definition=biao.definition.data,
                etiology=biao.etiology.data,
                clinical_manifestation=biao.clinical_manifestation.data,
                diagnosis=biao.diagnosis.data,
                treatment=biao.treatment.data,
                prevention=biao.prevention.data,
                references=biao.references.data,
                tags=biao.tags.data,
                source="manual",
                status="draft",
                created_by=g.dangqian_yonghu.id,
            )
            shujuku.session.add(tm)
            shujuku.session.commit()
            _guanlian_linshi_wenjian(tm.id, request.form.get("file_ids", ""))
            jilu_caozuo(g.dangqian_yonghu, "create", "知识录入", "录入: " + tm.title)
            flash("知识条目已保存为草稿", "success")
            return redirect(url_for("wo_de_zhishi"))
        return render_template("knowledge/edit.html", form=biao, mode="create")

    @chengxu.route("/knowledge/<int:eid>/edit", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_edit")
    def zhishi_bianji(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        yh = g.dangqian_yonghu
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review"))
        lai_can = request.args.get("lai", "")
        if lai_can == "shengcheng":
            hui_qu = "wo_de_shengcheng"
        elif lai_can == "wode":
            hui_qu = "wo_de_zhishi"
        elif shi_guanli:
            hui_qu = "zhishi_liebiao"
        else:
            hui_qu = "wo_de_shengcheng" if tm.source == "generated" else "wo_de_zhishi"
        if not shi_guanli and tm.created_by != yh.id:
            abort(403)
        if tm.yi_tingyong and not shi_guanli:
            flash("该知识已被停用，仅可在「知识列表」由管理员处理，这里不能编辑", "warning")
            return redirect(url_for(hui_qu))
        if tm.status == "pending":
            flash("该知识已提交审核，审核期间不能编辑；若被驳回可再修改", "warning")
            return redirect(url_for(hui_qu))
        if tm.status == "published":
            flash("该知识已上线，请先在列表点开关下架后再编辑", "warning")
            return redirect(url_for(hui_qu))
        biao = ZhishiBiao(obj=tm)
        tian_zhishi_fenlei(biao)
        if biao.validate_on_submit():
            tm.title = biao.title.data
            tm.category_id = biao.category_id.data or None
            tm.icd_code = (biao.icd_code.data or "").strip()
            tm.evidence_level = (biao.evidence_level.data or "").strip()
            tm.summary = biao.summary.data
            tm.definition = biao.definition.data
            tm.etiology = biao.etiology.data
            tm.clinical_manifestation = biao.clinical_manifestation.data
            tm.diagnosis = biao.diagnosis.data
            tm.treatment = biao.treatment.data
            tm.prevention = biao.prevention.data
            tm.references = biao.references.data
            tm.tags = biao.tags.data
            tm.version += 1
            tm.updated_at = datetime.now()
            shujuku.session.commit()
            _guanlian_linshi_wenjian(tm.id, request.form.get("file_ids", ""))
            jilu_caozuo(g.dangqian_yonghu, "update", "知识录入", "编辑: " + tm.title)
            flash("知识条目已更新", "success")
            return redirect(url_for(hui_qu))
        return render_template("knowledge/edit.html", form=biao, mode="edit", entry=tm)

    @chengxu.route("/knowledge/<int:eid>/submit", methods=["POST"])
    @xuyao_denglu
    def zhishi_tijiao(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        yh = g.dangqian_yonghu
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review"))
        lai_can = request.form.get("lai", "")
        if lai_can == "shengcheng":
            hui_qu = "wo_de_shengcheng"
        elif lai_can == "wode":
            hui_qu = "wo_de_zhishi"
        elif shi_guanli:
            hui_qu = "zhishi_liebiao"
        else:
            hui_qu = "wo_de_shengcheng" if tm.source == "generated" else "wo_de_zhishi"
        if not shi_guanli and tm.created_by != yh.id:
            abort(403)
        if tm.yi_tingyong and not shi_guanli:
            flash("该知识已被停用，仅可在「知识列表」由管理员重新启用", "warning")
            return redirect(url_for(hui_qu))
        if tm.status == "pending":
            flash("该知识已在审核中，请勿重复提交", "info")
        elif tm.status == "published":
            flash("该知识已发布上线，无需提交审核", "info")
        else:
            tm.status = "pending"
            tm.bohui_liyou = ""
            tm.updated_at = datetime.now()
            shujuku.session.commit()
            jilu_caozuo(yh, "submit",
                        "知识生成" if tm.source == "generated" else "知识录入",
                        "提交审核: " + tm.title)
            flash("已提交审核，审核通过前不能编辑", "info")
        return redirect(url_for(hui_qu))

    @chengxu.route("/knowledge/review")
    @xuyao_denglu
    @xuyao_quanxian("knowledge_review")
    def shenhe_liebiao():
        zhuangtai = request.args.get("zhuangtai", "deng")
        if zhuangtai == "deng":
            chaxun = KnowledgeEntry.query.filter_by(status="pending")
        elif zhuangtai in ("rejected", "published"):
            chaxun = KnowledgeEntry.query.filter_by(status=zhuangtai)
        else:
            zhuangtai = "all"
            chaxun = KnowledgeEntry.query.filter(
                KnowledgeEntry.status.in_(["pending", "rejected", "published"])
            )
        tiao_mu = chaxun.order_by(KnowledgeEntry.updated_at.desc()).all()
        tongji = dict(
            deng=KnowledgeEntry.query.filter_by(status="pending").count(),
            rejected=KnowledgeEntry.query.filter_by(status="rejected").count(),
            published=KnowledgeEntry.query.filter_by(status="published").count(),
        )
        tongji["all"] = tongji["deng"] + tongji["rejected"] + tongji["published"]
        return render_template("knowledge/review.html", entries=tiao_mu,
                               dangqian=zhuangtai, tongji=tongji)

    @chengxu.route("/knowledge/<int:eid>/review", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_review")
    def shenhe_shenhe(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        biao = ZhishiBiao(obj=tm)
        tian_zhishi_fenlei(biao)
        if biao.validate_on_submit():
            if tm.status != "pending":
                flash("该知识当前不在待审核状态，无需审核", "warning")
                return redirect(url_for("shenhe_liebiao"))
            dongzuo = request.form.get("action", "approve")
            liyou = request.form.get("bohui_liyou", "").strip()
            _guanlian_linshi_wenjian(tm.id, request.form.get("file_ids", ""))
            if dongzuo == "reject":
                if not liyou:
                    flash("驳回必须填写驳回理由，以便录入人修改", "danger")
                    return render_template("knowledge/review_edit.html", form=biao, entry=tm)
                tm.status = "rejected"
                tm.bohui_liyou = liyou
                tm.reviewed_by = g.dangqian_yonghu.id
                tm.reviewed_at = datetime.now()
                tm.updated_at = datetime.now()
                shujuku.session.commit()
                jilu_caozuo(g.dangqian_yonghu, "reject", "知识审核", "驳回: " + tm.title)
                flash("已驳回「%s」，理由已退回给录入人" % tm.title, "warning")
                return redirect(url_for("shenhe_liebiao"))
            tm.title = biao.title.data
            tm.category_id = biao.category_id.data or None
            tm.icd_code = (biao.icd_code.data or "").strip()
            tm.evidence_level = (biao.evidence_level.data or "").strip()
            tm.summary = biao.summary.data
            tm.definition = biao.definition.data
            tm.etiology = biao.etiology.data
            tm.clinical_manifestation = biao.clinical_manifestation.data
            tm.diagnosis = biao.diagnosis.data
            tm.treatment = biao.treatment.data
            tm.prevention = biao.prevention.data
            tm.references = biao.references.data
            tm.tags = biao.tags.data
            tm.status = "published"
            tm.bohui_liyou = ""
            tm.yi_tingyong = False
            tm.reviewed_by = g.dangqian_yonghu.id
            tm.reviewed_at = datetime.now()
            tm.updated_at = datetime.now()
            tm.version += 1
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "approve", "知识审核", "审核通过并发布: " + tm.title)
            flash("审核通过，「%s」已发布上线" % tm.title, "success")
            return redirect(url_for("shenhe_liebiao"))
        return render_template("knowledge/review_edit.html", form=biao, entry=tm)

    @chengxu.route("/knowledge/<int:eid>/toggle-publish", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_review")
    def zhishi_shangxia(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        if tm.status == "published":
            tm.status = "draft"
            tm.yi_tingyong = True
            tm.updated_at = datetime.now()
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "update", "知识列表", "停用: " + tm.title)
            flash("已停用「%s」。它在知识录入/生成箱中将变为只读，如需重新启用请在本页点开关上线" % tm.title, "info")
        else:
            tm.status = "published"
            tm.yi_tingyong = False
            tm.reviewed_by = g.dangqian_yonghu.id
            tm.reviewed_at = datetime.now()
            tm.updated_at = datetime.now()
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "approve", "知识列表", "一键上线: " + tm.title)
            flash("已发布上线「%s」，前台可检索" % tm.title, "success")
        return redirect(request.referrer or url_for("zhishi_liebiao"))

    @chengxu.route("/knowledge/<int:eid>/delete", methods=["POST"])
    @xuyao_denglu
    def zhishi_shanchu(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        yh = g.dangqian_yonghu
        if tm.created_by != yh.id and (not yh.role or yh.role.code != "admin"):
            abort(403)
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review"))
        if tm.yi_tingyong and not shi_guanli:
            flash("该知识已被停用，仅可在「知识列表」由管理员处理，这里不能删除", "warning")
            hui_qu = "wo_de_shengcheng" if tm.source == "generated" else "wo_de_zhishi"
            return redirect(url_for(hui_qu))
        if tm.status == "published":
            flash("该知识已上线，请先下架后再删除", "warning")
            return redirect(url_for("zhishi_liebiao"))
        jiao_sha = tm.title
        for wj in tm.files.all():
            shanchu_minio(wj.object_name)
        shujuku.session.delete(tm)
        shujuku.session.commit()
        jilu_caozuo(yh, "delete", "知识列表", "删除: " + jiao_sha)
        flash("知识条目已删除", "info")
        return redirect(url_for("zhishi_liebiao"))

    @chengxu.route("/knowledge/file/upload", methods=["POST"])
    @xuyao_denglu
    def wenjian_shangchuan():
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"success": False, "msg": "没收到文件"}), 400

        entry_id = request.form.get("entry_id", 0, type=int) or None
        fenlei_id = request.form.get("category_id", 0, type=int) or 0
        zhushi_ming = request.form.get("title", "").strip() or "未命名知识"

        fenlei_ming = "未分类"
        if fenlei_id:
            fl = Category.query.get(fenlei_id)
            if fl:
                fenlei_ming = fl.name

        yuan_ming = f.filename
        leixing = f.content_type or "application/octet-stream"
        f.stream.seek(0, 2)
        daxiao = f.stream.tell()
        f.stream.seek(0)

        try:
            duixiang = pin_dao_minio(fenlei_ming, zhushi_ming, entry_id or 0, f.stream, yuan_ming, daxiao, leixing)
        except Exception as e:
            return jsonify({"success": False, "msg": "上传到文件服务器失败: %s" % e}), 500

        wj = KnowledgeFile(
            entry_id=entry_id,
            original_name=yuan_ming,
            object_name=duixiang,
            content_type=leixing,
            file_size=daxiao,
        )
        shujuku.session.add(wj)
        shujuku.session.commit()

        return jsonify({
            "success": True,
            "file": {
                "id": wj.id,
                "name": wj.original_name,
                "size": wj.file_size,
                "is_image": wj.shi_tupian(),
                "is_pdf": wj.shi_pdf(),
                "is_word": wj.shi_word(),
                "preview_url": url_for("wenjian_yulan", fid=wj.id),
                "delete_url": url_for("wenjian_shanchu", fid=wj.id),
            },
        })

    @chengxu.route("/knowledge/file/<int:fid>/preview")
    @xuyao_denglu
    def wenjian_yulan(fid):
        wj = KnowledgeFile.query.get_or_404(fid)
        xiang = qu_liu_cong_minio(wj.object_name)
        shuju = xiang.read()
        xiang.close()
        xiang.release_conn()
        liu = BytesIO(shuju)
        return send_file(
            liu,
            mimetype=wj.content_type,
            as_attachment=False,
            download_name=wj.original_name,
        )

    @chengxu.route("/knowledge/file/<int:fid>/download")
    @xuyao_denglu
    def wenjian_xiazai(fid):
        wj = KnowledgeFile.query.get_or_404(fid)
        xiang = qu_liu_cong_minio(wj.object_name)
        shuju = xiang.read()
        xiang.close()
        xiang.release_conn()
        liu = BytesIO(shuju)
        return send_file(
            liu,
            mimetype=wj.content_type,
            as_attachment=True,
            download_name=wj.original_name,
        )

    @chengxu.route("/knowledge/file/<int:fid>/delete", methods=["POST"])
    @xuyao_denglu
    def wenjian_shanchu(fid):
        wj = KnowledgeFile.query.get_or_404(fid)
        yh = g.dangqian_yonghu
        shi_admin = yh.role and yh.role.code == "admin"
        shi_shenhe = yh.role and yh.role.shifou_youquan("knowledge_review")
        tm = KnowledgeEntry.query.get(wj.entry_id) if wj.entry_id else None
        if tm and tm.created_by != yh.id and not shi_admin and not shi_shenhe:
            return jsonify({"success": False, "msg": "无权删除"}), 403
        shanchu_minio(wj.object_name)
        shujuku.session.delete(wj)
        shujuku.session.commit()
        return jsonify({"success": True})


def gua_moxing_luyou(chengxu):
    @chengxu.route("/model/config")
    @xuyao_denglu
    @xuyao_quanxian("model_config")
    def moxing_liebiao():
        pei = ModelConfig.query.order_by(ModelConfig.id).all()
        return render_template("knowledge/model_config.html", configs=pei)

    @chengxu.route("/model/config/create", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("model_config")
    def moxing_xinzeng():
        biao = MoxingPeizhiBiao()
        if request.method == "GET":
            biao.ti_shi_ci.data = MOREN_TISHICI
        if biao.validate_on_submit():
            chong = ModelConfig.query.filter(
                shujuku.or_(
                    ModelConfig.name == biao.name.data.strip(),
                    ModelConfig.model_name == biao.model_name.data.strip(),
                )
            ).first()
            if chong:
                flash("配置名称：%s + 模型名称：%s 和当前配置重复，请勿重复添加" % (chong.name, chong.model_name), "danger")
                return render_template("knowledge/model_edit.html", form=biao, mode="create",
                                       moren_tishi=MOREN_TISHICI)
            if biao.is_active.data:
                ModelConfig.query.update({ModelConfig.is_active: False})
            px = ModelConfig(
                name=biao.name.data.strip(),
                api_url=biao.api_url.data,
                api_key=biao.api_key.data,
                model_name=biao.model_name.data.strip(),
                temperature=biao.temperature.data if biao.temperature.data is not None else 0.3,
                max_tokens=biao.max_tokens.data if biao.max_tokens.data is not None else 2048,
                ti_shi_ci=biao.ti_shi_ci.data or MOREN_TISHICI,
                si_kao_mo_shi=bool(biao.si_kao_mo_shi.data),
                is_active=biao.is_active.data,
            )
            shujuku.session.add(px)
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "create", "模型配置", "新增: " + px.name)
            flash("模型配置已保存", "success")
            return redirect(url_for("moxing_liebiao"))
        return render_template("knowledge/model_edit.html", form=biao, mode="create",
                               moren_tishi=MOREN_TISHICI)

    @chengxu.route("/model/config/<int:cid>/edit", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("model_config")
    def moxing_bianji(cid):
        px = ModelConfig.query.get_or_404(cid)
        biao = MoxingPeizhiBiao(obj=px)
        if biao.validate_on_submit():
            chong = ModelConfig.query.filter(
                ModelConfig.id != cid,
                shujuku.or_(
                    ModelConfig.name == biao.name.data.strip(),
                    ModelConfig.model_name == biao.model_name.data.strip(),
                ),
            ).first()
            if chong:
                flash("配置名称：%s + 模型名称：%s 和当前配置重复，请勿重复添加" % (chong.name, chong.model_name), "danger")
                biao.api_key.data = ""
                return render_template("knowledge/model_edit.html", form=biao, mode="edit", config=px,
                                       moren_tishi=MOREN_TISHICI)
            if biao.is_active.data:
                ModelConfig.query.filter(ModelConfig.id != cid).update({ModelConfig.is_active: False})
            px.name = biao.name.data.strip()
            px.api_url = biao.api_url.data
            if biao.api_key.data:
                px.api_key = biao.api_key.data
            px.model_name = biao.model_name.data.strip()
            px.temperature = biao.temperature.data if biao.temperature.data is not None else 0.3
            px.max_tokens = biao.max_tokens.data if biao.max_tokens.data is not None else 2048
            px.ti_shi_ci = biao.ti_shi_ci.data or MOREN_TISHICI
            px.si_kao_mo_shi = bool(biao.si_kao_mo_shi.data)
            px.is_active = biao.is_active.data
            shujuku.session.commit()
            jilu_caozuo(g.dangqian_yonghu, "update", "模型配置", "编辑: " + px.name)
            flash("模型配置已更新", "success")
            return redirect(url_for("moxing_liebiao"))
        biao.api_key.data = ""
        if not biao.ti_shi_ci.data:
            biao.ti_shi_ci.data = MOREN_TISHICI
        return render_template("knowledge/model_edit.html", form=biao, mode="edit", config=px,
                               moren_tishi=MOREN_TISHICI)

    @chengxu.route("/model/config/<int:cid>/activate", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("model_config")
    def moxing_qiyong(cid):
        px = ModelConfig.query.get_or_404(cid)
        ModelConfig.query.update({ModelConfig.is_active: False})
        px.is_active = True
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "activate", "模型配置", "启用: " + px.name)
        flash("已启用「%s」，其他模型已自动停用" % px.name, "success")
        return redirect(url_for("moxing_liebiao"))

    @chengxu.route("/model/config/<int:cid>/deactivate", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("model_config")
    def moxing_tingyong(cid):
        px = ModelConfig.query.get_or_404(cid)
        px.is_active = False
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "deactivate", "模型配置", "停用: " + px.name)
        flash("已停用「%s」，停用后知识生成将无可用模型" % px.name, "info")
        return redirect(url_for("moxing_liebiao"))

    @chengxu.route("/model/config/<int:cid>/delete", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("model_config")
    def moxing_shanchu(cid):
        px = ModelConfig.query.get_or_404(cid)
        if px.is_active:
            flash("「%s」正在启用中，请先停用后再删除" % px.name, "warning")
            return redirect(url_for("moxing_liebiao"))
        jiao_sha = px.name
        shujuku.session.delete(px)
        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "delete", "模型配置", "删除: " + jiao_sha)
        flash("模型配置已删除", "info")
        return redirect(url_for("moxing_liebiao"))

    @chengxu.route("/knowledge/generate", methods=["GET", "POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_generate")
    def zhishi_shengcheng():
        biao = ShengchengBiao()
        tian_zhishi_fenlei(biao)
        qiyong = ModelConfig.query.filter_by(is_active=True).first()

        if biao.validate_on_submit():
            if not qiyong:
                flash("尚未配置启用的模型，请先在模型配置中设置", "danger")
                return render_template("knowledge/generate.html", form=biao, active_cfg=qiyong)

            biaoti = biao.title.data
            cheng, jie_guo = qingqiu_moxing(qiyong, biaoti)

            if not cheng:
                flash("生成失败: " + str(jie_guo), "danger")
                xie_wenben_rizhi("模型生成失败: %s" % jie_guo, "error")
                return render_template("knowledge/generate.html", form=biao, active_cfg=qiyong)

            tm = KnowledgeEntry(
                title=biaoti,
                category_id=biao.category_id.data or None,
                icd_code="",
                evidence_level="AI待核",
                summary=jie_guo.get("summary", ""),
                definition=jie_guo.get("definition", ""),
                etiology=jie_guo.get("etiology", ""),
                clinical_manifestation=jie_guo.get("clinical_manifestation", ""),
                diagnosis=jie_guo.get("diagnosis", ""),
                treatment=jie_guo.get("treatment", ""),
                prevention=jie_guo.get("prevention", ""),
                references=jie_guo.get("references", ""),
                source="generated",
                status="draft",
                created_by=g.dangqian_yonghu.id,
            )
            shujuku.session.add(tm)
            shujuku.session.commit()

            jilu_caozuo(g.dangqian_yonghu, "generate", "知识生成",
                        "生成: %s（模型: %s）" % (biaoti, qiyong.name))
            flash("已生成《%s》并保存到生成箱草稿，可在列表中查看、编辑后提交审核" % biaoti, "success")
            return redirect(url_for("wo_de_shengcheng"))

        return render_template("knowledge/generate.html", form=biao, active_cfg=qiyong)


def gua_fuzhu_luyou(chengxu):
    def _suan_quekou():
        sousuo_cichu = shujuku.session.execute(text(
            "SELECT target AS guan, COUNT(*) AS c FROM access_log "
            "WHERE module = '知识检索' AND action = 'search' "
            "AND target IS NOT NULL AND target != '' AND target != '(无关键词)' "
            "GROUP BY target ORDER BY c DESC LIMIT 200"
        )).fetchall()
        que_kou = []
        for hang in sousuo_cichu:
            guan = (hang.guan or "").strip()
            if not guan:
                continue
            youzhong = KnowledgeEntry.query.filter_by(status="published").filter(
                shujuku.or_(
                    KnowledgeEntry.title.contains(guan),
                    KnowledgeEntry.summary.contains(guan),
                    KnowledgeEntry.tags.contains(guan),
                    KnowledgeEntry.definition.contains(guan),
                    KnowledgeEntry.icd_code.contains(guan),
                )
            ).count()
            alias_count = KnowledgeAlias.query.filter(KnowledgeAlias.alias_name.contains(guan)).count()
            if youzhong == 0 and alias_count == 0:
                que_kou.append({"keyword": guan, "count": hang.c})
        que_kou.sort(key=lambda x: x["count"], reverse=True)
        return que_kou, len(sousuo_cichu)

    @chengxu.route("/logs")
    @xuyao_denglu
    @xuyao_quanxian("log_view")
    def rizhi_liebiao():
        guan_jian = request.args.get("keyword", "").strip()
        mo_kuai = request.args.get("module", "")
        yema = request.args.get("page", 1, type=int)

        chaxun = AccessLog.query
        if guan_jian:
            chaxun = chaxun.filter(
                shujuku.or_(AccessLog.username.contains(guan_jian), AccessLog.target.contains(guan_jian))
            )
        if mo_kuai:
            chaxun = chaxun.filter_by(module=mo_kuai)
        chaxun = chaxun.order_by(AccessLog.id.desc())
        fenye = shougong_fenye(chaxun, yema, chengxu.config["PER_PAGE"])

        mokualist = shujuku.session.query(AccessLog.module).distinct().all()
        return render_template(
            "auxiliary/logs.html",
            logs=fenye.items, pagination=fenye,
            keyword=guan_jian, module=mo_kuai,
            modules=[m[0] for m in mokualist if m[0]],
        )

    @chengxu.route("/statistics")
    @xuyao_denglu
    @xuyao_quanxian("stat_view")
    def tongji_fenxi():
        cat_hang = shujuku.session.execute(text(
            "SELECT c.name AS m, COUNT(k.id) AS c "
            "FROM category c LEFT JOIN knowledge_entry k ON k.category_id = c.id "
            "GROUP BY c.id, c.name ORDER BY c.level ASC, c.sort_order ASC"
        )).fetchall()
        fenlei_tj = [(hang.m, hang.c) for hang in cat_hang]

        zt_hang = shujuku.session.execute(text(
            "SELECT status AS zt, COUNT(*) AS c FROM knowledge_entry GROUP BY status"
        )).fetchall()
        zhuangtai_tj = [(hang.zt, hang.c) for hang in zt_hang]

        jintian = datetime.now().date()
        qidian = datetime.combine(jintian - timedelta(days=6), datetime.min.time())
        qushi_hang = shujuku.session.execute(
            text("SELECT date(created_at) AS rq, COUNT(*) AS c FROM access_log "
                 "WHERE created_at >= :qi GROUP BY date(created_at)"),
            {"qi": qidian},
        ).fetchall()
        ri_ying = {}
        for hang in qushi_hang:
            ri_ying[str(hang.rq)] = hang.c
        qushi = []
        for wang_hou in range(6, -1, -1):
            yi_tian = jintian - timedelta(days=wang_hou)
            qushi.append({
                "date": yi_tian.strftime("%m-%d"),
                "count": ri_ying.get(yi_tian.isoformat(), 0),
            })

        yonghu_hang = shujuku.session.execute(text(
            "SELECT user_id AS uid, username AS un, COUNT(*) AS c "
            "FROM access_log GROUP BY user_id, username ORDER BY c DESC LIMIT 5"
        )).fetchall()
        huoyue = []
        for hang in yonghu_hang:
            mingcheng = hang.un
            if hang.uid:
                dui = User.query.get(hang.uid)
                if dui:
                    mingcheng = dui.real_name
            huoyue.append((mingcheng, hang.c))

        jiansuo_hang = shujuku.session.execute(text(
            "SELECT target AS x, COUNT(*) AS c FROM access_log "
            "WHERE module = '知识检索' AND action = 'search' "
            "AND target IS NOT NULL AND target != '' AND target != '(无关键词)' "
            "GROUP BY target ORDER BY c DESC LIMIT 20"
        )).fetchall()
        jiansuo_tj = [(hang.x, hang.c) for hang in jiansuo_hang]

        chakan_hang = shujuku.session.execute(text(
            "SELECT target AS x, COUNT(*) AS c FROM access_log "
            "WHERE module = '知识检索' AND action = 'view' "
            "GROUP BY target ORDER BY c DESC LIMIT 20"
        )).fetchall()
        chakan_tj = [(hang.x, hang.c) for hang in chakan_hang]

        def _shu_yixia(ming_zi):
            jie = shujuku.session.execute(
                text("SELECT COUNT(*) FROM access_log "
                     "WHERE module = '知识检索' AND action = 'search' AND detail LIKE :gz"),
                {"gz": "%%%s%%" % ming_zi},
            ).scalar()
            return jie or 0

        fenlei_jiansuo = []
        fl_all = Category.query.order_by(Category.level, Category.sort_order).all()
        for fl in fl_all:
            if fl.level != 1:
                continue
            zi_ji = [z for z in fl_all if z.parent_id == fl.id]
            zi_tj = []
            for zi in zi_ji:
                zi_tj.append({"id": zi.id, "name": zi.name, "count": _shu_yixia(zi.name)})
            fenlei_jiansuo.append({
                "id": fl.id,
                "name": fl.name,
                "count": _shu_yixia(fl.name),
                "children": zi_tj,
            })

        que_kou_quan, guanjian_zong = _suan_quekou()
        que_kou = que_kou_quan[:50]

        return render_template(
            "auxiliary/statistics.html",
            cat_stats=fenlei_tj,
            status_stats=zhuangtai_tj,
            trend=qushi,
            top_users=huoyue,
            search_stats=jiansuo_tj,
            view_stats=chakan_tj,
            category_search_stats=fenlei_jiansuo,
            gaps=que_kou,
            gap_total=guanjian_zong,
        )

    @chengxu.route("/knowledge-gap")
    @xuyao_denglu
    @xuyao_quanxian("stat_view")
    def zhishi_quekou():
        return redirect(url_for("tongji_fenxi") + "#zhishi-quekou")

    @chengxu.route("/knowledge-gap/export")
    @xuyao_denglu
    @xuyao_quanxian("stat_view")
    def zhishi_quekou_daochu():
        que_kou, _ = _suan_quekou()

        from io import StringIO
        from urllib.parse import quote as url_quote
        huan = StringIO()
        huan.write("\ufeff")
        huan.write("排名,未命中关键词,搜索次数\n")
        for i, g in enumerate(que_kou, 1):
            huan.write("%d,%s,%d\n" % (i, g["keyword"], g["count"]))
        nei_rong = huan.getvalue()
        huan.close()
        xiang = Response(
            nei_rong,
            mimetype="text/csv; charset=utf-8",
        )
        xiang.headers["Content-Disposition"] = \
            "attachment; filename*=UTF-8''%s" % url_quote("知识缺口清单.csv")
        return xiang


def gua_tupu_luyou(chengxu):
    @chengxu.route("/entries/<int:eid>/alias/add", methods=["POST"])
    @xuyao_denglu
    def ming_zu_tianjia(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        yh = g.dangqian_yonghu
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review"))
        if not shi_guanli and tm.created_by != yh.id:
            abort(403)
        ming = (request.form.get("alias_name", "") or "").strip()
        if not ming:
            flash("别名字不能为空", "warning")
            return redirect(request.referrer or url_for("tiaomu_xiangqing", eid=eid))
        cun = KnowledgeAlias.query.filter_by(entry_id=eid, alias_name=ming).first()
        if cun:
            flash("该别名已存在", "info")
        else:
            shujuku.session.add(KnowledgeAlias(entry_id=eid, alias_name=ming))
            shujuku.session.commit()
        hui = request.form.get("lai", "")
        if hui:
            return redirect(url_for("tiaomu_xiangqing", eid=eid, lai=hui))
        return redirect(request.referrer or url_for("tiaomu_xiangqing", eid=eid))

    @chengxu.route("/entries/alias/<int:aid>/delete", methods=["POST"])
    @xuyao_denglu
    def ming_zu_shanchu(aid):
        ms = KnowledgeAlias.query.get_or_404(aid)
        yh = g.dangqian_yonghu
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review"))
        if not shi_guanli and ms.entry and ms.entry.created_by != yh.id:
            abort(403)
        eid = ms.entry_id
        shujuku.session.delete(ms)
        shujuku.session.commit()
        hui = request.form.get("lai", "")
        if hui:
            return redirect(url_for("tiaomu_xiangqing", eid=eid, lai=hui))
        return redirect(request.referrer or url_for("tiaomu_xiangqing", eid=eid))

    @chengxu.route("/entries/<int:eid>/link/add", methods=["POST"])
    @xuyao_denglu
    def guan_lian_tianjia(eid):
        tm = KnowledgeEntry.query.get_or_404(eid)
        yh = g.dangqian_yonghu
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review") or yh.role.shifou_youquan("knowledge_edit"))
        if not shi_guanli and tm.created_by != yh.id:
            abort(403)
        tgt_id = request.form.get("target_id", 0, type=int)
        tgt_ming = (request.form.get("target_title", "") or "").strip()
        if tgt_id:
            tgt = KnowledgeEntry.query.get(tgt_id)
        elif tgt_ming:
            tgt = KnowledgeEntry.query.filter(KnowledgeEntry.title.contains(tgt_ming)).first()
        else:
            tgt = None
        if not tgt:
            flash("没找到目标知识条目，请确认标题或ID", "warning")
            return redirect(request.referrer or url_for("tupu_goujian_yemian"))
        if tgt.id == eid:
            flash("不能关联自己", "warning")
            return redirect(request.referrer or url_for("tupu_goujian_yemian"))
        guan_xing = (request.form.get("link_type", "鉴别诊断") or "").strip() or "关联"
        qiang_du = request.form.get("strength", 0.9, type=float) or 0.9
        qiang_du = max(0.01, min(1.0, qiang_du))
        cun = KnowledgeLink.query.filter_by(
            source_entry_id=eid, target_entry_id=tgt.id, link_type=guan_xing
        ).first()
        if cun:
            cun.strength = qiang_du
            cun.is_explicit = True
        else:
            shujuku.session.add(KnowledgeLink(
                source_entry_id=eid, target_entry_id=tgt.id,
                link_type=guan_xing, strength=qiang_du, is_explicit=True,
            ))
        shujuku.session.commit()
        jilu_caozuo(yh, "create", "鉴别诊断",
                    "关联: %s → %s (%s)" % (tm.title, tgt.title, guan_xing))
        hui = request.form.get("lai", "")
        if hui == "build":
            return redirect(url_for("tupu_goujian_yemian"))
        if hui:
            return redirect(url_for("tiaomu_xiangqing", eid=eid, lai=hui))
        return redirect(request.referrer or url_for("tiaomu_xiangqing", eid=eid))

    @chengxu.route("/entries/link/batch", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_edit")
    def guan_lian_piliang():
        yh = g.dangqian_yonghu
        src_id = request.form.get("source_id", 0, type=int)
        if not src_id:
            flash("请选择源知识", "warning")
            return redirect(url_for("tupu_goujian_yemian"))
        tm = KnowledgeEntry.query.get_or_404(src_id)
        tgt_ids = request.form.getlist("target_id[]")
        lx_list = request.form.getlist("link_type[]")
        qd_list = request.form.getlist("strength[]")
        added = 0
        for i, tid_str in enumerate(tgt_ids):
            tid = int(tid_str) if tid_str else 0
            if not tid or tid == src_id:
                continue
            tgt = KnowledgeEntry.query.get(tid)
            if not tgt:
                continue
            gx = (lx_list[i] if i < len(lx_list) else "关联") or "关联"
            qd = float(qd_list[i]) if i < len(qd_list) and qd_list[i] else 0.9
            qd = max(0.01, min(1.0, qd))
            cun = KnowledgeLink.query.filter_by(
                source_entry_id=src_id, target_entry_id=tid, link_type=gx
            ).first()
            if cun:
                cun.strength = qd
                cun.is_explicit = True
            else:
                shujuku.session.add(KnowledgeLink(
                    source_entry_id=src_id, target_entry_id=tid,
                    link_type=gx, strength=qd, is_explicit=True,
                ))
            added += 1
        shujuku.session.commit()
        if added:
            jilu_caozuo(yh, "create", "鉴别诊断",
                        "批量关联: %s → %d条" % (tm.title, added))
            flash("成功添加 %d 条关联关系" % added, "success")
        else:
            flash("没有有效的关联可添加", "warning")
        return redirect(url_for("tupu_goujian_yemian"))

    @chengxu.route("/entries/link/<int:lid>/delete", methods=["POST"])
    @xuyao_denglu
    def guan_lian_shanchu(lid):
        lk = KnowledgeLink.query.get_or_404(lid)
        yh = g.dangqian_yonghu
        shi_guanli = yh.role and (yh.role.code == "admin" or yh.role.shifou_youquan("knowledge_review") or yh.role.shifou_youquan("knowledge_edit"))
        if not shi_guanli and lk.source and lk.source.created_by != yh.id:
            abort(403)
        eid = lk.source_entry_id
        shujuku.session.delete(lk)
        shujuku.session.commit()
        hui = request.form.get("lai", "")
        if hui == "build":
            return redirect(url_for("tupu_goujian_yemian"))
        if hui:
            return redirect(url_for("tiaomu_xiangqing", eid=eid, lai=hui))
        return redirect(request.referrer or url_for("tiaomu_xiangqing", eid=eid))

    @chengxu.route("/knowledge/graph/link/<int:lid>/edit", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_edit")
    def guan_lian_gengxin(lid):
        lk = KnowledgeLink.query.get_or_404(lid)
        yh = g.dangqian_yonghu
        qd = request.form.get("strength", type=float)
        gx = request.form.get("link_type", "").strip()
        if qd is not None:
            lk.strength = max(0.01, min(1.0, qd))
        if gx:
            lk.link_type = gx
        lk.is_explicit = True
        shujuku.session.commit()
        jilu_caozuo(yh, "update", "知识关联",
                    "更新关联 #%d: %s-%s | type=%s strength=%.2f (已升级为人工)" % (
                        lk.id,
                        lk.source.title if lk.source else "?",
                        lk.target.title if lk.target else "?",
                        lk.link_type, lk.strength))
        flash("关联已更新，已升级为人工关联", "success")
        return redirect(url_for("tupu_goujian_yemian"))

    @chengxu.route("/knowledge/graph/link/<int:lid>/promote", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_edit")
    def guan_lian_shengji(lid):
        lk = KnowledgeLink.query.get_or_404(lid)
        if lk.is_explicit:
            flash("这条已经是人工关联了", "warning")
            return redirect(url_for("tupu_goujian_yemian"))
        lk.is_explicit = True
        shujuku.session.commit()
        yh = g.dangqian_yonghu
        jilu_caozuo(yh, "update", "知识关联",
                    "升级自动关联 #%d 为人工: %s-%s | strength=%.2f" % (
                        lk.id,
                        lk.source.title if lk.source else "?",
                        lk.target.title if lk.target else "?",
                        lk.strength))
        flash("已升级为人工关联，下次自动构建时不会被清理", "success")
        return redirect(url_for("tupu_goujian_yemian"))

    @chengxu.route("/knowledge/graph/build")
    @xuyao_denglu
    @xuyao_quanxian("knowledge_edit")
    def tupu_goujian_yemian():
        jibing_cat = Category.query.filter(
            shujuku.or_(Category.name == "疾病", Category.name == "DISEASE")
        ).first()
        jibing_entries = []
        if jibing_cat:
            jibing_entries = KnowledgeEntry.query.filter_by(
                status="published", category_id=jibing_cat.id
            ).order_by(KnowledgeEntry.title).all()

        fenlei_zu = []
        all_cats = Category.query.order_by(Category.sort_order).all()
        for cat in all_cats:
            tiaomu = KnowledgeEntry.query.filter_by(
                status="published", category_id=cat.id
            ).order_by(KnowledgeEntry.title).all()
            if tiaomu:
                fenlei_zu.append({"cat": cat, "entries": tiaomu})
        wei_fen = KnowledgeEntry.query.filter_by(
            status="published", category_id=None
        ).order_by(KnowledgeEntry.title).all()
        if wei_fen:
            fenlei_zu.append({"cat": None, "entries": wei_fen})

        xian_you = KnowledgeLink.query.filter_by(is_explicit=True).order_by(KnowledgeLink.strength.desc()).all()
        zidong = KnowledgeLink.query.filter_by(is_explicit=False).order_by(KnowledgeLink.strength.desc()).all()
        guanxi_leixing = [
            "鉴别诊断", "并发症", "诱因", "上游疾病",
            "治疗药品", "辅助检查", "临床表现", "关联",
        ]
        return render_template(
            "knowledge/build_graph.html",
            jibing_entries=jibing_entries,
            fenlei_zu=fenlei_zu,
            xian_you=xian_you,
            zidong=zidong,
            guanxi_leixing=guanxi_leixing,
        )

    @chengxu.route("/knowledge/graph/auto-build", methods=["POST"])
    @xuyao_denglu
    @xuyao_quanxian("knowledge_edit")
    def zhishi_tupu_goujian():
        zidong_bian = KnowledgeLink.query.filter_by(is_explicit=False).all()
        for b in zidong_bian:
            shujuku.session.delete(b)
        shujuku.session.commit()

        tiaomu = KnowledgeEntry.query.filter_by(status="published").all()
        if len(tiaomu) < 2:
            flash("至少需要2条已发布知识才能构建图谱", "warning")
            return redirect(request.referrer or url_for("zhishi_liebiao"))

        def _pin_wenben(tm):
            return " ".join([
                tm.title or "", tm.summary or "", tm.definition or "",
                tm.etiology or "", tm.clinical_manifestation or "",
                tm.diagnosis or "", tm.treatment or "", tm.tags or "",
            ])

        bian_shu = 0
        for i in range(len(tiaomu)):
            a = tiaomu[i]
            a_text = _pin_wenben(a)
            for j in range(i + 1, len(tiaomu)):
                b = tiaomu[j]
                b_text = _pin_wenben(b)
                cun = KnowledgeLink.query.filter(
                    shujuku.or_(
                        shujuku.and_(
                            KnowledgeLink.source_entry_id == a.id,
                            KnowledgeLink.target_entry_id == b.id,
                            KnowledgeLink.is_explicit == True,
                        ),
                        shujuku.and_(
                            KnowledgeLink.source_entry_id == b.id,
                            KnowledgeLink.target_entry_id == a.id,
                            KnowledgeLink.is_explicit == True,
                        ),
                    )
                ).first()
                if cun:
                    continue

                qiang_du = 0.0
                guan_xing = "关联"

                if a.category_id and a.category_id == b.category_id:
                    qiang_du += 0.3

                a_tags = set((a.tags or "").replace("，", ",").split(","))
                b_tags = set((b.tags or "").replace("，", ",").split(","))
                a_tags.discard("")
                b_tags.discard("")
                jiao = a_tags & b_tags
                if jiao:
                    qiang_du += min(len(jiao) * 0.1, 0.5)

                a_title_zip = a.title.strip()[:4]
                b_title_zip = b.title.strip()[:4]
                if a_title_zip and a_title_zip in b_text:
                    qiang_du += 0.2
                    guan_xing = "鉴别诊断"
                if b_title_zip and b_title_zip in a_text:
                    qiang_du += 0.2
                    guan_xing = "关联"

                if a.definition and b.title[:3] in a.definition:
                    qiang_du += 0.15
                if b.definition and a.title[:3] in b.definition:
                    qiang_du += 0.15
                if a.diagnosis and b.title[:3] in a.diagnosis:
                    qiang_du += 0.15
                if b.diagnosis and a.title[:3] in b.diagnosis:
                    qiang_du += 0.15
                    guan_xing = "并发症"

                if qiang_du < 0.1:
                    continue
                qiang_du = round(min(max(qiang_du, 0.1), 0.6), 2)

                shujuku.session.add(KnowledgeLink(
                    source_entry_id=a.id, target_entry_id=b.id,
                    link_type=guan_xing, strength=qiang_du, is_explicit=False,
                ))
                shujuku.session.add(KnowledgeLink(
                    source_entry_id=b.id, target_entry_id=a.id,
                    link_type="关联", strength=round(qiang_du * 0.8, 2), is_explicit=False,
                ))
                bian_shu += 2
                if bian_shu % 50 == 0:
                    shujuku.session.commit()

        shujuku.session.commit()
        jilu_caozuo(g.dangqian_yonghu, "build", "构建知识图谱",
                    "构建完成，新增自动关系 %d 条" % bian_shu)
        flash("知识图谱已构建完成：清理旧自动边，新增 %d 条自动关联" % bian_shu, "success")
        return redirect(url_for("tupu_goujian_yemian"))

    @chengxu.route("/graph")
    @xuyao_denglu
    @xuyao_quanxian("graph_view")
    def zhishi_tupu():
        jibing_cat = Category.query.filter(
            shujuku.or_(Category.name == "疾病", Category.name == "DISEASE")
        ).first()
        tiaomu = []
        if jibing_cat:
            tiaomu = KnowledgeEntry.query.filter_by(
                status="published", category_id=jibing_cat.id
            ).order_by(KnowledgeEntry.title).all()
        return render_template(
            "category/graph.html",
            entries=tiaomu,
        )

    @chengxu.route("/api/graph/data")
    @xuyao_denglu
    @xuyao_quanxian("graph_view")
    def tupu_shuju():
        zhongxin_id = request.args.get("center", 0, type=int)
        if zhongxin_id:
            zhongxin = KnowledgeEntry.query.get(zhongxin_id)
            if not zhongxin or zhongxin.status != "published":
                return jsonify({"nodes": [], "links": []})
            lin_id = set([zhongxin_id])
            yi_tiao_all = KnowledgeLink.query.filter(shujuku.or_(
                KnowledgeLink.source_entry_id == zhongxin_id,
                KnowledgeLink.target_entry_id == zhongxin_id,
            )).all()
            for lk in yi_tiao_all:
                lin_id.add(lk.source_entry_id)
                lin_id.add(lk.target_entry_id)
            nodes = KnowledgeEntry.query.filter(
                KnowledgeEntry.id.in_(lin_id),
                KnowledgeEntry.status == "published",
            ).all()
            shi_ids = [n.id for n in nodes]
            links = KnowledgeLink.query.filter(shujuku.or_(
                KnowledgeLink.source_entry_id == zhongxin_id,
                KnowledgeLink.target_entry_id == zhongxin_id,
            )).all()
        else:
            nodes = KnowledgeEntry.query.filter_by(status="published").limit(200).all()
            node_ids = [n.id for n in nodes]
            links = KnowledgeLink.query.filter(shujuku.and_(
                KnowledgeLink.source_entry_id.in_(node_ids),
                KnowledgeLink.target_entry_id.in_(node_ids),
            )).all()

        fenlei_se_map = {
            "疾病": "#ffc107", "DISEASE": "#ffc107",
            "药品": "#ff7043", "MEDICINE": "#ff7043",
            "检查": "#26c6da", "EXAM": "#26c6da",
            "检验": "#42a5f5", "LAB": "#42a5f5",
            "手术": "#7e57c2", "SURGERY": "#7e57c2",
            "麻醉": "#ef5350", "ANESTHESIA": "#ef5350",
            "健康宣教": "#66bb6a", "HEALTH_EDU": "#66bb6a",
            "症状": "#ec407a", "SYMPTOM": "#ec407a",
            "成分": "#2e7d32", "INGREDIENT": "#2e7d32",
            "未分类": "#b0bec5",
        }

        _du_cache = {}
        for lk in links:
            a, b = lk.source_entry_id, lk.target_entry_id
            _du_cache[a] = _du_cache.get(a, 0) + 1
            _du_cache[b] = _du_cache.get(b, 0) + 1

        nodes_jie = []
        for n in nodes:
            fl_name = n.category.name if n.category else "未分类"
            se = fenlei_se_map.get(fl_name, "#b0bec5")
            is_center = (zhongxin_id and n.id == zhongxin_id)
            du_shu = _du_cache.get(n.id, 0)
            if is_center:
                sz = 80
            else:
                sz = min(52, max(26, 26 + du_shu * 5))
            nodes_jie.append({
                "id": n.id,
                "name": n.title,
                "category": fl_name,
                "symbolSize": sz,
                "itemStyle": {
                    "color": se,
                    "borderColor": "#fff",
                    "borderWidth": 2,
                    "shadowBlur": 8,
                    "shadowColor": "rgba(0,0,0,0.15)",
                },
                "url": url_for("tiaomu_xiangqing", eid=n.id, lai="tupu"),
                "_degree": du_shu,
            })

        links_jie = []
        yi_jia = set()
        for lk in links:
            key = tuple(sorted([lk.source_entry_id, lk.target_entry_id]))
            if key in yi_jia:
                continue
            yi_jia.add(key)
            zh_que = KnowledgeLink.query.filter_by(
                source_entry_id=lk.source_entry_id, target_entry_id=lk.target_entry_id
            ).first()
            fan_x = KnowledgeLink.query.filter_by(
                source_entry_id=lk.target_entry_id, target_entry_id=lk.source_entry_id
            ).first()
            qiang = 0.1
            xing = lk.link_type
            if zh_que:
                qiang = max(qiang, zh_que.strength or 0.1)
                xing = zh_que.link_type
            if fan_x:
                qiang = max(qiang, fan_x.strength or 0.1)
            qiang = round(qiang, 2)
            links_jie.append({
                "source": lk.source_entry_id,
                "target": lk.target_entry_id,
                "value": qiang,
                "label": {
                    "show": True,
                    "position": "middle",
                    "formatter": xing,
                    "fontSize": 10,
                    "color": "#666",
                    "fontWeight": "normal",
                },
                "lineStyle": {
                    "width": 1,
                    "color": "#d0d0d0" if not lk.is_explicit else "#ffb74d",
                    "opacity": 0.85 if not lk.is_explicit else 1.0,
                    "curveness": 0.05,
                },
            })

        fenlei_list = []
        yi_fen = set()
        for n in nodes:
            fn = n.category.name if n.category else "未分类"
            if fn not in yi_fen:
                yi_fen.add(fn)
                fenlei_list.append({"name": fn, "itemStyle": {"color": fenlei_se_map.get(fn, "#90a4ae")}})

        return jsonify({
            "nodes": nodes_jie,
            "links": links_jie,
            "categories": fenlei_list,
            "center": zhongxin_id or 0,
            "total_links": len(links_jie),
        })


def gua_moban_guolv(chengxu):
    @chengxu.template_filter("shijian_ge_shi")
    def _geshihua(zhi):
        if not zhi:
            return ""
        if isinstance(zhi, str):
            return zhi
        return zhi.strftime("%Y-%m-%d %H:%M")

    @chengxu.template_filter("zhuangtai_zhuan_hua")
    def _zhuangtai_wenan(zhi):
        dui_zhao = {
            "draft": "草稿",
            "pending": "待审核",
            "published": "已发布",
            "rejected": "已驳回",
        }
        return dui_zhao.get(zhi, zhi)


def moren_shuju(chengxu):
    if Role.query.count() == 0:
        guan_li = Role(
            name="系统管理员", code="admin",
            permissions=",".join([
                "home_view", "search_view",
                "user_manage", "dept_manage", "role_manage",
                "knowledge_create", "knowledge_edit", "knowledge_review",
                "knowledge_generate", "category_manage", "log_view",
                "stat_view", "model_config",
                "graph_view",
            ]),
            remark="拥有全部权限",
        )
        bian_ji = Role(
            name="知识编辑", code="editor",
            permissions="knowledge_create,knowledge_edit,knowledge_generate,category_manage",
            remark="知识录入与编辑",
        )
        shen_he = Role(
            name="审核员", code="reviewer",
            permissions="knowledge_review,stat_view,log_view",
            remark="知识审核",
        )
        shujuku.session.add_all([guan_li, bian_ji, shen_he])

    if Department.query.count() == 0:
        ji_ge_ks = [
            Department(name="医务部", code="MED", sort_order=1),
            Department(name="内科", code="INT", sort_order=2),
            Department(name="外科", code="SUR", sort_order=3),
            Department(name="急诊科", code="EMG", sort_order=4),
            Department(name="药剂科", code="PHA", sort_order=5),
        ]
        shujuku.session.add_all(ji_ge_ks)

    if User.query.count() == 0:
        admin = User(
            username="admin", real_name="系统管理员",
            email="admin@mks.local", phone="13800000000",
            department_id=1, role_id=1, status="active",
        )
        admin.shezhi_mima("Cdb123456!")
        shujuku.session.add(admin)

    if Category.query.count() == 0:
        ji_ge_fl = [
            Category(name="疾病", code="DISEASE", level=1, sort_order=1, description="疾病相关知识"),
            Category(name="药品", code="MEDICINE", level=1, sort_order=2, description="药品相关知识"),
            Category(name="检查", code="EXAM", level=1, sort_order=3, description="检查相关知识"),
            Category(name="检验", code="LAB", level=1, sort_order=4, description="检验相关知识"),
            Category(name="手术", code="SURGERY", level=1, sort_order=5, description="手术相关知识"),
            Category(name="麻醉", code="ANESTHESIA", level=1, sort_order=6, description="麻醉相关知识"),
            Category(name="健康宣教", code="HEALTH_EDU", level=1, sort_order=7, description="健康宣教知识"),
        ]
        shujuku.session.add_all(ji_ge_fl)

    shujuku.session.commit()


cdb_app = qidong_chengxu()

if __name__ == "__main__":
    cdb_app.run(host="0.0.0.0", port=7122)
