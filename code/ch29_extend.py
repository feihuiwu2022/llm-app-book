"""第 29 章配套代码：给最小 Agent 加上技能、命令、钩子。只用标准库。
运行：python code/ch29_extend.py

三种扩展机制的区别在于谁触发：
  技能  模型触发  平时只有一行描述在上下文里，模型判断用得上时才读入正文
  命令  用户触发  用户输入 /名字，程序把它展开成一段预先写好的提示词
  钩子  事件触发  工具执行前后必然运行的普通函数，可以放行或拦截
模型用替身代替；技能加载、命令展开、钩子拦截都是真的。
"""
import json
from pathlib import Path

import car

SKILL_DIR = Path(__file__).parent / "skills"


# ---------- 技能：按需加载 ----------

def read_skill(path: Path) -> tuple[dict, str]:
    """把 SKILL.md 拆成头部（名字、描述）和正文。"""
    _, head, body = path.read_text(encoding="utf-8").split("---", 2)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    return meta, body.strip()


def skill_listing() -> str:
    """常驻上下文的部分：每个技能只占一行。"""
    metas = [read_skill(p)[0] for p in sorted(SKILL_DIR.glob("*/SKILL.md"))]
    return "\n".join(f"- {m['name']}：{m['description']}" for m in metas)


def load_skill(name: str) -> str:
    """模型调用这个工具时，技能正文才进入上下文。"""
    path = SKILL_DIR / name / "SKILL.md"
    return read_skill(path)[1] if path.exists() else f"没有名为 {name} 的技能"


# ---------- 命令：用户触发的提示词模板 ----------

COMMANDS = {"trip": "我{0}要跑长途，出发前帮我把车检查一遍。"}


def expand(user_input: str) -> str:
    """/trip 明天  →  展开成完整的一句任务。不是命令就原样返回。"""
    if not user_input.startswith("/"):
        return user_input
    name, _, argument = user_input[1:].partition(" ")
    return COMMANDS[name].format(argument)


# ---------- 钩子：工具执行前后必然运行的函数 ----------

READ_ONLY = {"get_tire_pressure", "search_manual", "load_skill"}
AUDIT = []


def observe_only(name: str, arguments: dict):
    """执行前钩子：观察模式下，有副作用的工具只记录、不执行。返回拒绝原因，或 None 表示放行。"""
    if name not in READ_ONLY:
        return f"观察模式：{name} 未执行，已记录供人工确认"
    return None


def audit(name: str, arguments: dict, result) -> None:
    """执行后钩子：每次工具调用留一条审计记录。"""
    AUDIT.append(f"{name}({json.dumps(arguments, ensure_ascii=False)})")


# ---------- 带扩展点的主循环（在第 21 章的循环上加了三处）----------

def agent(user_input: str, model, pre_hooks=(), post_hooks=(), max_turns: int = 8) -> str:
    system = "你是车载助手。可用技能如下，需要时先调用 load_skill 读取完整流程：\n" + skill_listing()  # 扩展点一
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": expand(user_input)}]                                    # 扩展点二
    for turn in range(1, max_turns + 1):
        reply = model(messages)
        messages.append(reply)
        calls = reply.get("tool_calls", [])
        if not calls:
            return reply["content"]
        for call in calls:
            name, arguments = call["name"], json.loads(call["arguments"])
            denied = next((r for hook in pre_hooks if (r := hook(name, arguments))), None)          # 扩展点三
            if denied:
                result = {"ok": False, "error": denied}
            elif name == "load_skill":
                result = load_skill(**arguments)
            else:
                result = car.run_tool(name, arguments)
            for hook in post_hooks:
                hook(name, arguments, result)
            print(f"  第 {turn} 轮  {name}  →  {'被钩子拦截' if denied else '已执行'}")
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result, ensure_ascii=False)})
    return "达到轮数上限，任务未完成。"


# ---------- 以下是替身模型 ----------

def stand_in_model(messages: list) -> dict:
    done, names = {}, {}
    for m in messages:
        for c in m.get("tool_calls", []):
            names[c["id"]] = c["name"]
        if m["role"] == "tool":
            done[names[m["tool_call_id"]]] = json.loads(m["content"])

    def call(i, tool, **arguments):
        return {"id": f"call_{len(names) + i}", "name": tool,
                "arguments": json.dumps(arguments, ensure_ascii=False)}

    if "load_skill" not in done:      # 系统提示词里的描述提到"长途"，于是先读技能正文
        return {"role": "assistant", "tool_calls": [call(1, "load_skill", name="long-trip")]}
    if "get_tire_pressure" not in done:
        return {"role": "assistant", "tool_calls": [
            call(1, "get_tire_pressure"), call(2, "search_manual", query="胎压标准值")]}
    if "set_ac_temperature" not in done:
        return {"role": "assistant", "tool_calls": [call(1, "set_ac_temperature", celsius=22)]}
    low = [f"{k}{v}千帕" for k, v in done["get_tire_pressure"].items() if v < 190]
    ac = done["set_ac_temperature"]
    ac_line = "空调已预设为22度。" if ac.get("ok") else "空调未调整，等待你确认后再设置。"
    return {"role": "assistant", "content":
            f"暂时不建议出发。{'、'.join(low)}，低于报警线，请先检查补气。{ac_line}出发前建议充电至百分之一百。"}


if __name__ == "__main__":
    listing = skill_listing()
    full = sum(len(p.read_text(encoding="utf-8")) for p in SKILL_DIR.glob("*/SKILL.md"))
    print(f"技能清单（常驻上下文，{len(listing)} 字符；全部正文预载要 {full} 字符）：\n{listing}\n")
    print(f"命令展开：/trip 明天  →  {expand('/trip 明天')}\n")

    for label, hooks in [("观察模式（挂上执行前钩子）", [observe_only]), ("正常模式（不挂执行前钩子）", [])]:
        car.STATE["ac_celsius"] = 24
        AUDIT.clear()
        print(label)
        answer = agent("/trip 明天", stand_in_model, pre_hooks=hooks, post_hooks=[audit])
        print(f"  答复：{answer}")
        print(f"  空调真实状态：{car.STATE['ac_celsius']} 度；审计记录 {len(AUDIT)} 条\n")
