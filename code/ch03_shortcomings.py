"""第 3 章配套代码：四个短板的探针与判分器。只用标准库。
运行：python code/ch03_shortcomings.py

默认用"替身模型"离线运行：它的翻车方式是照着四个短板写死的，
数字来自脚本设定，不代表任何真实模型。本章要交付的是测法，不是某个模型的成绩。
设置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 三个环境变量后，同一套探针会改测真实模型。
"""
import json
import random
import re

import llm

AC_STATE = {"celsius": 24}  # 空调的真实状态。模型只能输出文字，碰不到它。

# 探针四的题目：每题要连续算好几步。answer 是标准答案。
MULTI_STEP = [
    ("电池容量60度电，从百分之二十充到百分之九十，从电网取的电是充进电池的1.1倍，电价每度0.6元，这次充电花多少元？", 27.72),
    ("百公里电耗15度电，电池60度电，只用其中的百分之八十，零下十度续航再降百分之三十，能跑多少公里？", 224.0),
    ("四个轮胎胎压分别是238、185、251、249千帕，前轮标准240，后轮标准250，四个轮胎与标准值的偏差绝对值之和是多少千帕？", 59.0),
    ("滤芯每一万公里或十二个月更换，以先到者为准。每月跑1500公里，三年内要换几次滤芯？", 5.0),
    ("去程180公里电耗每百公里14度，回程180公里电耗每百公里17度，电价每度1.2元，往返电费多少元？", 66.96),
]


class StandIn:
    """替身模型：照着四个短板写死的假模型。"""

    def __init__(self, seed: int = 3):
        self.rng = random.Random(seed)
        self.direct = dict(zip([q for q, _ in MULTI_STEP], ["25.2", "224", "53", "3", "66.96"]))
        self.stepwise = dict(zip([q for q, _ in MULTI_STEP], ["27.72", "224", "59", "5", "66.96"]))

    def __call__(self, prompt: str) -> str:
        if "JSON" in prompt:
            body = '{"code": "P0420", "level": "warning"}'
            r = self.rng.random()
            if r < 0.10:
                return "好的，以下是结果：\n" + body
            if r < 0.20:
                return "```json\n" + body + "\n```"
            return body
        if "空调" in prompt and "调到" in prompt:
            return "好的，已为您将空调调到22度。"
        if "胎压标准" in prompt:
            return "一般乘用车的冷态胎压在230千帕左右，具体请以车辆标签为准。"
        for q in self.direct:
            if q in prompt:
                table = self.stepwise if "一步一步" in prompt else self.direct
                return f"答案：{table[q]}"
        return "我不确定。"


def probe_unknown(ask) -> dict:
    """探针一 不知道：问一个只写在私有资料里的事实，看答案里有没有那个值。"""
    reply = ask("我这款车前轮的冷态胎压标准是多少千帕？")
    return {"通过": "240" in reply, "回复": reply}


def probe_unstable(ask, runs: int = 20) -> dict:
    """探针二 不稳定：同一条提示词连发多次，逐次用解析器验收格式。"""
    prompt = '故障码P0420，等级warning。只输出JSON：{"code": 故障码, "level": 等级}，不要输出任何别的内容。'
    ok = 0
    for _ in range(runs):
        try:
            data = json.loads(ask(prompt))
            ok += data.get("code") == "P0420" and data.get("level") == "warning"
        except (json.JSONDecodeError, AttributeError):
            pass
    return {"通过": ok == runs, "合格次数": f"{ok}/{runs}"}


def probe_cannot_act(ask) -> dict:
    """探针三 做不了：不听它怎么说，去查真实状态变没变。"""
    before = AC_STATE["celsius"]
    reply = ask("帮我把空调调到22度。")
    after = AC_STATE["celsius"]
    return {"通过": after == 22, "回复": reply, "真实状态": f"调用前 {before} 度，调用后 {after} 度"}


def last_number(text: str):
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(nums[-1]) if nums else None


def probe_shallow(ask) -> dict:
    """探针四 想不深：同一批多步题，对比"直接给答案"和"一步一步算"两种问法的正确率。"""
    result = {}
    for mode, suffix in [("直接答", "只输出最终数字，不要写过程。"), ("分步答", "请一步一步计算，最后一行写出最终数字。")]:
        right = 0
        for question, answer in MULTI_STEP:
            got = last_number(ask(question + suffix))
            right += got is not None and abs(got - answer) < 0.01
        result[mode] = f"{right}/{len(MULTI_STEP)}"
    result["通过"] = result["直接答"] == f"{len(MULTI_STEP)}/{len(MULTI_STEP)}"
    return result


if __name__ == "__main__":
    if llm.configured():
        ask = llm.chat
        print("被测对象：环境变量指定的真实模型\n")
    else:
        ask = StandIn()
        print("被测对象：替身模型（数字来自脚本设定，不代表任何真实模型）\n")

    for title, probe in [
        ("探针一 不知道", probe_unknown),
        ("探针二 不稳定", probe_unstable),
        ("探针三 做不了", probe_cannot_act),
        ("探针四 想不深", probe_shallow),
    ]:
        report = probe(ask)
        verdict = "通过" if report.pop("通过") else "翻车"
        print(f"{title}：{verdict}")
        for key, value in report.items():
            print(f"  {key}：{value}")
