# -*- coding: utf-8 -*-
"""
医学知识库系统 - 表单验证层
使用 WTForms 对各模块输入进行服务端校验
作者：陈的斌
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, SelectField,
    IntegerField, BooleanField, FloatField, SubmitField,
)
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError


class LoginForm(FlaskForm):
    username = StringField("账号", validators=[DataRequired(message="请输入登录账号")])
    password = PasswordField("口令", validators=[DataRequired(message="请输入口令")])
    captcha = StringField("验证码", validators=[DataRequired(message="请输入验证码")])


class UserForm(FlaskForm):
    username = StringField("登录账号", validators=[DataRequired(), Length(3, 50)])
    real_name = StringField("真实姓名", validators=[DataRequired(), Length(1, 50)])
    password = PasswordField("登录口令", validators=[Optional(), Length(6, 50)])
    email = StringField("邮箱", validators=[Optional(), Email(message="邮箱格式不正确")])
    phone = StringField("电话", validators=[Optional(), Length(0, 20)])
    department_id = SelectField("所属科室", coerce=int, validators=[Optional()])
    role_id = SelectField("角色", coerce=int, validators=[Optional()])
    status = SelectField("状态", choices=[("active", "正常"), ("disabled", "停用")])
    submit = SubmitField("保存")


class DepartmentForm(FlaskForm):
    name = StringField("科室名称", validators=[DataRequired(), Length(1, 80)])
    code = StringField("科室编码", validators=[DataRequired(), Length(1, 30)])
    parent_id = SelectField("上级科室", coerce=int, validators=[Optional()])
    sort_order = IntegerField("排列序号", default=0)
    remark = StringField("备注", validators=[Optional(), Length(0, 200)])
    submit = SubmitField("保存")


class RoleForm(FlaskForm):
    name = StringField("角色名称", validators=[DataRequired(), Length(1, 50)])
    code = StringField("角色编码", validators=[DataRequired(), Length(1, 30)])
    permissions = StringField("权限列表", validators=[Optional()])
    remark = StringField("备注", validators=[Optional(), Length(0, 200)])
    submit = SubmitField("保存")


class CategoryForm(FlaskForm):
    name = StringField("分类名称", validators=[DataRequired(), Length(1, 80)])
    code = StringField("分类编码", validators=[DataRequired(), Length(1, 30)])
    parent_id = SelectField("上级分类", coerce=int, validators=[Optional()])
    sort_order = IntegerField("排列序号", default=0)
    description = StringField("描述", validators=[Optional(), Length(0, 300)])
    submit = SubmitField("保存")


class KnowledgeForm(FlaskForm):
    title = StringField("知识标题", validators=[DataRequired(), Length(1, 200)])
    category_id = SelectField("所属分类", coerce=int, validators=[Optional()])
    summary = TextAreaField("摘要", validators=[Optional()])
    definition = TextAreaField("定义", validators=[Optional()])
    etiology = TextAreaField("病因", validators=[Optional()])
    clinical_manifestation = TextAreaField("临床表现", validators=[Optional()])
    diagnosis = TextAreaField("诊断标准", validators=[Optional()])
    treatment = TextAreaField("治疗方案", validators=[Optional()])
    prevention = TextAreaField("预防措施", validators=[Optional()])
    references = TextAreaField("参考文献", validators=[Optional()])
    tags = StringField("标签", validators=[Optional(), Length(0, 300)])
    submit = SubmitField("保存")


class ModelConfigForm(FlaskForm):
    name = StringField("配置名称", validators=[DataRequired(), Length(1, 80)])
    api_url = StringField("接口地址", validators=[DataRequired(), Length(1, 500)])
    api_key = PasswordField("接口密钥", validators=[Optional()])
    model_name = StringField("模型标识", validators=[DataRequired(), Length(1, 100)])
    temperature = FloatField("生成温度", default=0.3)
    max_tokens = IntegerField("最大Token", default=2048)
    is_active = BooleanField("设为当前启用")
    submit = SubmitField("保存")


class KnowledgeGenerateForm(FlaskForm):
    title = StringField("知识名称", validators=[DataRequired(message="请输入知识名称"), Length(1, 200)])
    category_id = SelectField("所属分类", coerce=int, validators=[Optional()])
    submit = SubmitField("开始生成")
