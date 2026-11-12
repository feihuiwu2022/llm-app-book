"""可选的真实模型后端。只用标准库。

本书的配套代码默认用"替身模型"（写死规则的假模型）离线运行，保证谁都能跑通。
想换成真实模型时，设置三个环境变量即可，接口按 OpenAI 兼容的 /chat/completions 格式：

    export LLM_BASE_URL=https://你的服务地址/v1
    export LLM_API_KEY=你的密钥
    export LLM_MODEL=模型名
"""
import json
import os
import urllib.request


def configured() -> bool:
    return all(os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


def chat(prompt: str, temperature: float = 1.0, timeout: int = 60) -> str:
    """发一条用户消息，返回模型的文字回复。"""
    body = json.dumps({
        "model": os.environ["LLM_MODEL"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["LLM_API_KEY"],
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"] or ""
