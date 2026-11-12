"""一辆虚构的车：第 13、17、19 章共用的工具集。只用标准库。

工具就是普通函数。模型不能直接执行它们，只能输出"我想调哪个、参数是什么"，
由外面的程序代为执行，这是篇四、篇五、篇六反复出现的主题。
"""
from corpus import MANUAL
from ch05_chunk import chunk
from ch06_retrieve import bm25_search, embed, rrf, vector_search

# 车辆当前状态。工具读写的就是这个字典。
STATE = {
    "tire_kpa": {"左前": 238, "右前": 185, "左后": 251, "右后": 249},
    "ac_celsius": 24,
}

_CHUNKS = chunk(MANUAL, size=80, overlap=20)
_VECTORS = [embed(c) for c in _CHUNKS]


def get_tire_pressure() -> dict:
    """读取四个轮胎的当前胎压，单位千帕。"""
    return dict(STATE["tire_kpa"])


def set_ac_temperature(celsius: int) -> dict:
    """设置空调温度，允许范围 16 到 32 摄氏度。"""
    if not 16 <= celsius <= 32:
        return {"ok": False, "error": "温度超出范围，允许 16 到 32 摄氏度"}
    STATE["ac_celsius"] = celsius
    return {"ok": True, "ac_celsius": celsius}


def search_manual(query: str) -> str:
    """在车主手册里检索，返回最相关的一块原文。复用第 6 章的两路召回加 RRF。"""
    fused = rrf([
        vector_search(query, _CHUNKS, _VECTORS, k=4),
        bm25_search(query, _CHUNKS, k=4),
    ])
    return _CHUNKS[fused[0][0]]


# 工具清单：这一份会被原样放进模型的上下文，模型靠它知道有什么可调。
TOOLS = [
    {
        "name": "get_tire_pressure",
        "description": "读取四个轮胎的当前胎压，单位千帕。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "set_ac_temperature",
        "description": "设置空调温度。",
        "parameters": {
            "type": "object",
            "properties": {"celsius": {"type": "integer", "description": "目标温度，16 到 32"}},
            "required": ["celsius"],
        },
    },
    {
        "name": "search_manual",
        "description": "在车主手册里检索，返回最相关的一段原文。",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "检索用的关键词或问题"}},
            "required": ["query"],
        },
    },
]

REGISTRY = {
    "get_tire_pressure": get_tire_pressure,
    "set_ac_temperature": set_ac_temperature,
    "search_manual": search_manual,
}


def run_tool(name: str, arguments: dict):
    """按名字执行工具。名字不存在或参数不对时返回错误信息，而不是让程序崩掉。"""
    if name not in REGISTRY:
        return {"ok": False, "error": f"没有名为 {name} 的工具"}
    try:
        return REGISTRY[name](**arguments)
    except TypeError as e:
        return {"ok": False, "error": f"参数错误：{e}"}
