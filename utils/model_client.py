# -*- coding: utf-8 -*-
"""
医学知识库系统 - 模型接口客户端
封装对模型 API 的调用逻辑，根据知识模板构造提示词并解析返回结果
作者：陈的斌
"""

import json
import logging

import requests

logger = logging.getLogger(__name__)

FIELD_LABELS = {
    "definition": "定义",
    "etiology": "病因",
    "clinical_manifestation": "临床表现",
    "diagnosis": "诊断标准",
    "treatment": "治疗方案",
    "prevention": "预防措施",
    "references": "参考文献",
}

PROMPT_TEMPLATE = (
    "你是一位资深的医学专家，请根据以下知识名称，生成一份结构化的医学知识条目。\n"
    "知识名称：{title}\n\n"
    "请严格按照以下 JSON 格式输出，每个字段都需填写专业、准确的内容，"
    "不要输出 JSON 以外的任何文字：\n"
    "{{\n"
    '  "summary": "该疾病的简要概述（100-200字）",\n'
    '  "definition": "疾病的医学定义",\n'
    '  "etiology": "病因与发病机制",\n'
    '  "clinical_manifestation": "主要临床症状与体征",\n'
    '  "diagnosis": "诊断标准与辅助检查方法",\n'
    '  "treatment": "治疗原则与具体方案",\n'
    '  "prevention": "预防措施与健康指导",\n'
    '  "references": "主要参考文献来源"\n'
    "}}"
)


def call_model(config, title: str):
    """调用模型接口生成医学知识内容

    Args:
        config: ModelConfig 实例，包含接口地址、密钥等信息
        title: 知识名称（如疾病名）

    Returns:
        tuple: (success: bool, result: dict|str)
               成功时 result 为解析后的字段字典，失败时为错误信息
    """
    prompt = PROMPT_TEMPLATE.format(title=title)

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + config.api_key,
    }

    payload = {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": "你是专业的医学知识助手，擅长生成结构化的医学知识条目。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    try:
        resp = requests.post(
            config.api_url,
            headers=headers,
            json=payload,
            timeout=config.max_tokens if config.max_tokens else 60,
        )
        resp.raise_for_status()
        data = resp.json()

        content = ""
        if "choices" in data and len(data["choices"]) > 0:
            msg = data["choices"][0].get("message", {})
            content = msg.get("content", "")
        elif "output" in data:
            content = data["output"].get("text", "")
        elif "data" in data:
            content = data["data"].get("content", "")

        if not content:
            return False, "模型返回内容为空"

        parsed = _extract_json(content)
        if parsed is None:
            return False, "无法解析模型返回的结构化内容"

        result = {}
        for field in FIELD_LABELS:
            result[field] = parsed.get(field, "")
        result["summary"] = parsed.get("summary", "")

        return True, result

    except requests.exceptions.Timeout:
        logger.error("模型接口调用超时")
        return False, "模型接口调用超时，请稍后重试"
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到模型接口")
        return False, "无法连接到模型接口，请检查网络或接口地址配置"
    except requests.exceptions.HTTPError as e:
        logger.error("模型接口返回错误: %s", e)
        return False, "模型接口返回错误: " + str(e)
    except Exception as e:
        logger.error("模型调用异常: %s", e)
        return False, "调用异常: " + str(e)


def _extract_json(text: str):
    """从文本中提取 JSON 对象

    模型可能在 JSON 前后附加额外文字，此方法尝试提取首个合法 JSON 块
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        fragment = text[start:end + 1]
        try:
            return json.loads(fragment)
        except json.JSONDecodeError:
            pass

    return None