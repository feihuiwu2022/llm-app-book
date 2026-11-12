"""第 21 章配套代码：最小 Agent。只用标准库。
运行：python code/ch21_agent.py

文件分两半。上半是 Agent 本体：主循环加工具执行，不到五十行，换成真实模型时一行都不用改。
下半是替身模型：它读消息列表里已有的工具结果来决定下一步，代替真实模型的"想"。
"""
import json

import car

SYSTEM = "你是车载助手。需要数据或操作时调用工具，不要凭印象回答。任务完成后直接给出答复。"


def agent(task: str, model, max_turns: int = 8) -> str:
    """Agent 主循环：问模型下一步 → 有调用就执行并把结果拼回去 → 没有调用就结束。"""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for turn in range(1, max_turns + 1):
        size = len(json.dumps(messages, ensure_ascii=False))
        reply = model(messages, car.TOOLS)              # 1. 让模型决定下一步
        messages.append(reply)
        calls = reply.get("tool_calls", [])
        print(f"第 {turn} 轮｜输入 {size} 字符｜", end="")
        if not calls:                                   # 2. 没有工具调用：任务结束
            print("给出最终答复")
            return reply["content"]
        print("调用 " + "、".join(c["name"] for c in calls))
        for call in calls:                              # 3. 程序替模型执行工具
            result = car.run_tool(call["name"], json.loads(call["arguments"]))
            messages.append({                           # 4. 结果拼回上下文，进入下一轮
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })
    return "达到轮数上限，任务未完成。"                    # 5. 兜底：不允许无限循环


# ---------------------------------------------------------------------------
# 以下是替身模型，不属于 Agent 本体。
# ---------------------------------------------------------------------------

def stand_in_model(messages: list, tools: list) -> dict:
    """根据已拿到的工具结果决定下一步。真实模型靠阅读上下文做同样的判断。"""
    results = {}
    names = {}
    for m in messages:
        for c in m.get("tool_calls", []):
            names[c["id"]] = c["name"]
        if m["role"] == "tool":
            results.setdefault(names[m["tool_call_id"]], []).append(json.loads(m["content"]))

    def call(i, name, **arguments):
        return {"id": f"call_{len(names) + i}", "name": name,
                "arguments": json.dumps(arguments, ensure_ascii=False)}

    if "get_tire_pressure" not in results:
        # 两件互不依赖的事，一轮里同时发起
        return {"role": "assistant", "tool_calls": [
            call(1, "get_tire_pressure"),
            call(2, "search_manual", query="胎压标准值"),
        ]}
    if len(results["search_manual"]) == 1:
        return {"role": "assistant", "tool_calls": [call(1, "search_manual", query="胎压低于多少报警")]}
    if "set_ac_temperature" not in results:
        return {"role": "assistant", "tool_calls": [call(1, "set_ac_temperature", celsius=22)]}

    tires = results["get_tire_pressure"][0]
    low = [f"{k}{v}千帕" for k, v in tires.items() if v < 190]
    ac = results["set_ac_temperature"][0]
    return {"role": "assistant", "content": (
        f"胎压：{'、'.join(low)}，低于手册规定的190千帕报警线（前轮标准240千帕），请尽快减速靠边检查；"
        f"其余三个轮胎正常。空调已从24度调到{ac['ac_celsius']}度。"
    )}


if __name__ == "__main__":
    task = "帮我看看胎压正不正常，另外车里有点热，把空调调低两度。"
    print(f"任务：{task}\n")
    answer = agent(task, stand_in_model)
    print(f"\n答复：{answer}")
    print(f"空调真实状态：{car.STATE['ac_celsius']} 度")
