# -*- coding: utf-8 -*-
# 调大模型接口拿生成结果，urllib 发的 post

import json
import ssl
import urllib.request
import urllib.error

# 提示词：让模型照着病历的结构吐 JSON
# 这是系统内置的默认模板（唯一一份），新增模型配置时自动填入；
# {title} 是占位符，请求时会被替换成知识名称。各配置可在模型配置页改成自己的版本
TISHICI = (
    "你是一位资深的医学专家，请根据以下知识名称，生成一份结构化的医学知识条目。\n"
    "知识名称：{title}\n\n"
    "请严格按照以下 JSON 格式输出，每个字段都需填写专业、准确的内容：\n"
    "{\n"
    '  "summary": "该疾病的简要概述（100-200字）",\n'
    '  "definition": "疾病的医学定义",\n'
    '  "etiology": "病因与发病机制",\n'
    '  "clinical_manifestation": "主要临床症状与体征",\n'
    '  "diagnosis": "诊断标准与辅助检查方法",\n'
    '  "treatment": "治疗原则与具体方案",\n'
    '  "prevention": "预防措施与健康指导",\n'
    '  "references": "主要参考文献来源"\n'
    "}"
)

# 要从模型回答里摘出来的字段，顺序跟预览页对着
ZIDUAN_LIEBIAO = [
    "summary", "definition", "etiology", "clinical_manifestation",
    "diagnosis", "treatment", "prevention", "references",
]


def qingqiu_moxing(peizhi, biaoti):
    """请求模型，成功返回 (True, 字段字典)，失败返回 (False, 原因)"""
    mu_ban = (getattr(peizhi, "ti_shi_ci", None) or "").strip() or TISHICI
    ti_shi = mu_ban.replace("{title}", biaoti)

    qing_qiu_ti = {
        "model": peizhi.model_name,
        "messages": [
            {"role": "system", "content": "你是专业的医学知识助手"},
            {"role": "user", "content": ti_shi},
        ],
        "temperature": peizhi.temperature,
        "max_tokens": peizhi.max_tokens,
    }
    shu_ju = json.dumps(qing_qiu_ti, ensure_ascii=False).encode("utf-8")

    tou = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + (peizhi.api_key or ""),
    }

    try:
        req = urllib.request.Request(peizhi.api_url, data=shu_ju, headers=tou, method="POST")
        # 60 秒等不到就算了，页面还得给人提示呢
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as resp:
            hui_yuan = resp.read().decode("utf-8")
        jie_xi = json.loads(hui_yuan)

        # 不同厂家返回包的壳不一样，挨个扒一遍
        wen_ben = ""
        if jie_xi.get("choices"):
            wen_ben = jie_xi["choices"][0].get("message", {}).get("content", "")
        elif "output" in jie_xi:
            wen_ben = jie_xi["output"].get("text", "")
        elif "data" in jie_xi:
            wen_ben = jie_xi["data"].get("content", "")

        if not wen_ben:
            return False, "模型返回内容为空"

        jie_guo = wa_jue_json(wen_ben)
        if jie_guo is None:
            return False, "模型返回的内容没法解析成JSON"

        # 缺哪个字段补空串，预览页直接取不会 KeyError
        tian_hao = {}
        for zd in ZIDUAN_LIEBIAO:
            tian_hao[zd] = jie_guo.get(zd, "")
        return True, tian_hao

    except urllib.error.HTTPError as cuo_wu:
        # 接口报错时把状态码带上，排查快一点
        try:
            cuo_wen = cuo_wu.read().decode("utf-8")
        except Exception:
            cuo_wen = ""
        # 常见状态码直接给一句人话，不然用户看到 402 一脸懵
        ren_hua = {
            401: "API密钥无效或已过期，请检查模型配置里的密钥",
            402: "模型接口账户余额不足，请先充值或换用其他模型配置",
            403: "没有该模型接口的访问权限",
            404: "接口地址或模型名称不对（地址404），请检查模型配置",
            429: "请求太频繁或额度超限，稍后再试",
        }.get(cuo_wu.code)
        if ren_hua:
            return False, ren_hua + "（接口返回 %s: %s）" % (cuo_wu.code, cuo_wen[:120])
        return False, "接口返回错误(%s): %s" % (cuo_wu.code, cuo_wen[:200])
    except urllib.error.URLError as cuo_wu:
        return False, "网络连不上模型接口: %s" % cuo_wu.reason
    except Exception as cuo_wu:
        return False, str(cuo_wu)


def wa_jue_json(wen_ben):
    # 模型回答外面爱裹 markdown，直接抠最外层大括号
    try:
        return json.loads(wen_ben)
    except Exception:
        pass

    zuo = wen_ben.find("{")
    you = wen_ben.rfind("}")
    if zuo != -1 and you > zuo:
        try:
            return json.loads(wen_ben[zuo:you + 1])
        except Exception:
            pass
    return None
