import os
import sys
import tempfile
import unittest

XIANGMU_GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if XIANGMU_GEN not in sys.path:
    sys.path.insert(0, XIANGMU_GEN)


class MoxingPeizhiTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ku_wenjian = os.path.join(tempfile.gettempdir(), "mks_test_model_config.db")
        if os.path.exists(cls.ku_wenjian):
            os.remove(cls.ku_wenjian)

        import peizhi
        peizhi.JichuShezhi.SQLALCHEMY_DATABASE_URI = "sqlite:///" + cls.ku_wenjian

        import mks_main
        from mks_models import shujuku, User, Role, ModelConfig

        cls.mks_main = mks_main
        cls.shujuku = shujuku
        cls.User = User
        cls.Role = Role
        cls.ModelConfig = ModelConfig

        cls.app = mks_main.qidong_chengxu()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        with cls.app.app_context():
            putong_juese = Role(
                name="普通查看员", code="putong_chakan",
                permissions="knowledge_view",
            )
            shujuku.session.add(putong_juese)
            shujuku.session.commit()

            putong = User(
                username="putong", real_name="普通查看员",
                status="active", role_id=putong_juese.id,
            )
            putong.shezhi_mima("123456")
            shujuku.session.add(putong)
            shujuku.session.commit()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.shujuku.session.remove()
        try:
            os.remove(cls.ku_wenjian)
        except OSError:
            pass

    def setUp(self):
        with self.app.app_context():
            self.ModelConfig.query.delete()
            self.shujuku.session.commit()

    def _denglu(self, yonghu, mima):
        c = self.app.test_client()
        c.get("/captcha")
        with c.session_transaction() as sess:
            yanzheng_ma = sess["yzm"]
        resp = c.post(
            "/login",
            data={"username": yonghu, "password": mima, "captcha": yanzheng_ma},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302, "登录应成功跳转(302)")
        return c

    def _admin(self):
        return self._denglu("admin", "Cdb123456!")

    def _biao_dan(self, name="测试配置", model_name="test-model", thinking=False,
                  api_key="sk-test", active=False, temperature="0.3", max_tokens="2048"):
        data = {
            "name": name,
            "api_url": "https://api.example.com/v1/chat/completions",
            "api_key": api_key,
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if thinking:
            data["si_kao_mo_shi"] = "y"
        if active:
            data["is_active"] = "y"
        return data

    def _chuangjian(self, client, **kwargs):
        r = client.post("/model/config/create", data=self._biao_dan(**kwargs),
                        follow_redirects=False)
        self.assertEqual(r.status_code, 302, "新增成功应 302 跳回列表")
        with self.app.app_context():
            name = kwargs.get("name", "测试配置")
            obj = self.ModelConfig.query.filter_by(name=name).first()
            self.assertIsNotNone(obj, "新增后库里应能查到")
            return obj.id

    def _zhuangtai(self, cid):
        with self.app.app_context():
            o = self.ModelConfig.query.get(cid)
            return o.is_active

    def test_01_weidenglu_bei_lan(self):
        c = self.app.test_client()
        r = c.get("/model/config", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers.get("Location", ""))

    def test_02_wuquanxian_bei_lan(self):
        c = self._denglu("putong", "123456")
        r_list = c.get("/model/config", follow_redirects=False)
        self.assertEqual(r_list.status_code, 302, "无权限看列表应 302")
        self.assertNotIn("/model/config", r_list.headers.get("Location", "") + "##")

        r_create = c.post("/model/config/create", data=self._biao_dan(),
                          follow_redirects=False)
        self.assertEqual(r_create.status_code, 302, "无权限新增应 302")
        with self.app.app_context():
            self.assertEqual(self.ModelConfig.query.count(), 0, "无权限新增不应落库")

    def test_03_admin_keyikan_liebiao(self):
        c = self._admin()
        r = c.get("/model/config")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("模型名称", html)
        self.assertIn("思考模式", html)
        self.assertNotIn("<th>模型标识</th>", html)

    def test_10_xinzeng_jiben_yu_sikao(self):
        c = self._admin()
        cid = self._chuangjian(c, name="思考配置", model_name="think-model", thinking=True)
        with self.app.app_context():
            o = self.ModelConfig.query.get(cid)
            self.assertTrue(o.si_kao_mo_shi, "思考模式应开启")
            self.assertFalse(o.is_active, "未勾选启用则应为未启用")
            self.assertEqual(o.model_name, "think-model")

    def test_11_xinzeng_wendu_token_moren(self):
        c = self._admin()
        data = self._biao_dan(name="空数字配置", temperature="", max_tokens="")
        r = c.post("/model/config/create", data=data, follow_redirects=False)
        self.assertEqual(r.status_code, 302, "留空温度/Token 也应保存成功")
        with self.app.app_context():
            o = self.ModelConfig.query.filter_by(name="空数字配置").first()
            self.assertIsNotNone(o)
            self.assertAlmostEqual(o.temperature, 0.3)
            self.assertEqual(o.max_tokens, 2048)

    def test_12_xinzeng_gou_qiyong_huting_qita(self):
        c = self._admin()
        a = self._chuangjian(c, name="先启用A", model_name="model-a", active=True)
        self.assertTrue(self._zhuangtai(a))
        data = self._biao_dan(name="后启用B", model_name="model-b", active=True)
        r = c.post("/model/config/create", data=data, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            b = self.ModelConfig.query.filter_by(name="后启用B").first()
            self.assertTrue(b.is_active, "新配置应启用")
            self.assertFalse(self.ModelConfig.query.get(a).is_active, "旧配置应被互斥停用")
            self.assertEqual(
                self.ModelConfig.query.filter_by(is_active=True).count(), 1,
                "同一时间只能有一个启用",
            )

    def test_20_quchong_peizhiming(self):
        c = self._admin()
        self._chuangjian(c, name="同名配置", model_name="model-origin")
        r = c.post(
            "/model/config/create",
            data=self._biao_dan(name="同名配置", model_name="model-new"),
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 200, "重复应停留在表单页而不是跳转")
        html = r.get_data(as_text=True)
        self.assertIn("和当前配置重复", html)
        self.assertIn("配置名称：同名配置", html)
        self.assertIn("模型名称：model-origin", html)
        with self.app.app_context():
            self.assertEqual(self.ModelConfig.query.filter_by(name="同名配置").count(), 1,
                             "重复的那条不应被新增")

    def test_21_quchong_moxingming(self):
        c = self._admin()
        self._chuangjian(c, name="原配置", model_name="dup-model")
        r = c.post(
            "/model/config/create",
            data=self._biao_dan(name="另一个配置名", model_name="dup-model"),
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("配置名称：原配置", html)
        self.assertIn("模型名称：dup-model", html)
        with self.app.app_context():
            self.assertIsNone(
                self.ModelConfig.query.filter_by(name="另一个配置名").first(),
                "模型名重复不应落库",
            )

    def test_22_bianji_quchong_paichu_zishen(self):
        c = self._admin()
        a = self._chuangjian(c, name="配置甲", model_name="model-jia")
        b = self._chuangjian(c, name="配置乙", model_name="model-yi")

        r = c.post(
            "/model/config/%d/edit" % a,
            data=self._biao_dan(name="配置乙", model_name="model-jia"),
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("和当前配置重复", r.get_data(as_text=True))

        r2 = c.post(
            "/model/config/%d/edit" % a,
            data=self._biao_dan(name="配置甲", model_name="model-jia"),
            follow_redirects=False,
        )
        self.assertEqual(r2.status_code, 302, "编辑自身同名应保存成功")

    def test_30_qiyong_huchi(self):
        c = self._admin()
        a = self._chuangjian(c, name="配置A", model_name="m-a")
        b = self._chuangjian(c, name="配置B", model_name="m-b")
        self.assertFalse(self._zhuangtai(a))
        self.assertFalse(self._zhuangtai(b))

        c.post("/model/config/%d/activate" % a)
        self.assertTrue(self._zhuangtai(a), "A 应启用")
        self.assertFalse(self._zhuangtai(b), "B 应保持停用")

        c.post("/model/config/%d/activate" % b)
        self.assertTrue(self._zhuangtai(b), "B 应启用")
        self.assertFalse(self._zhuangtai(a), "启用 B 后 A 应被自动停用")

        with self.app.app_context():
            self.assertEqual(self.ModelConfig.query.filter_by(is_active=True).count(), 1)

    def test_31_tingyong(self):
        c = self._admin()
        a = self._chuangjian(c, name="待停用", model_name="m-off", active=True)
        self.assertTrue(self._zhuangtai(a))
        r = c.post("/model/config/%d/deactivate" % a, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self._zhuangtai(a), "停用后 is_active 应为 False")

    def test_32_shanchu_qiyongzhong_bei_yinglan(self):
        c = self._admin()
        a = self._chuangjian(c, name="启用中", model_name="m-active", active=True)
        r = c.post("/model/config/%d/delete" % a, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertIsNotNone(self.ModelConfig.query.get(a),
                                 "启用中的配置删除应被拦截、记录仍在")

    def test_33_shanchu_weiyiyong_chenggong(self):
        c = self._admin()
        a = self._chuangjian(c, name="待删除", model_name="m-del")
        self.assertFalse(self._zhuangtai(a))
        r = c.post("/model/config/%d/delete" % a, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(self.ModelConfig.query.get(a), "未启用配置删除后应不存在")

    def test_40_bianji_ye_wenan_yu_huitian(self):
        c = self._admin()
        a = self._chuangjian(c, name="回填配置", model_name="m-backfill", thinking=True)
        r = c.get("/model/config/%d/edit" % a)
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("模型名称", html)
        self.assertIn("开启思考模式", html)
        self.assertNotIn("模型标识", html)
        self.assertIn("checked", html, "开启思考模式时勾选框应 checked")

    def test_41_bianji_guanbi_sikao(self):
        c = self._admin()
        a = self._chuangjian(c, name="切换思考", model_name="m-toggle", thinking=True)
        data = self._biao_dan(name="切换思考", model_name="m-toggle", thinking=False)
        r = c.post("/model/config/%d/edit" % a, data=data, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertFalse(self.ModelConfig.query.get(a).si_kao_mo_shi,
                             "保存后思考模式应为关闭")

    def test_42_bianji_yaoyue_liukong_bu_gai(self):
        c = self._admin()
        a = self._chuangjian(c, name="密钥配置", model_name="m-key", api_key="sk-original")
        data = self._biao_dan(name="密钥配置", model_name="m-key", api_key="")
        r = c.post("/model/config/%d/edit" % a, data=data, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.ModelConfig.query.get(a).api_key, "sk-original",
                             "密钥留空不应覆盖原密钥")


if __name__ == "__main__":
    unittest.main(verbosity=2)
