"""第 13 章配套代码：函数调用的四步往返。只用标准库。
运行：python code/ch13_function_call.py

模型用替身代替：它只会输出"想调哪个工具、参数是什么"，和真实模型在这一步做的事一样。
真正改变车辆状态的，是下面第 3 步里程序自己执行的那一行。
"""
import json

import car


def stand_in_model(messages: list, tools: list) -> dict:
    """替身模型。真实模型在这里读完整个上下文后生成一条消息，形态相同。"""
    last = messages[-1]
    if last["role"] == "user":  # 看到用户请求：不回答，输出一个调用请求
        return {
            "role": "assistant",
            "tool_calls": [{"id": "call_1", "name": "set_ac_temperature", "arguments": '{"celsius": 22}'}],
        }
    result = json.loads(last["content"])  # 看到工具结果：据此写最终回复
    if result.get("ok"):
        return {"role": "assistant", "content": f"已将空调调到 {result['ac_celsius']} 度。"}
    return {"role": "assistant", "content": f"没有调成功：{result['error']}"}


def show(step: str, obj) -> None:
    print(f"\n{step}\n{json.dumps(obj, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    print(f"调用前，空调真实状态：{car.STATE['ac_celsius']} 度")

    # 第 1 步：程序把工具清单和用户消息一起发给模型
    messages = [{"role": "user", "content": "帮我把空调调到22度"}]
    show("第 1 步　程序 → 模型：用户消息（工具清单同时发出，共 %d 个工具）" % len(car.TOOLS), messages[0])

    # 第 2 步：模型返回的不是答案，而是一个调用请求
    reply = stand_in_model(messages, car.TOOLS)
    messages.append(reply)
    show("第 2 步　模型 → 程序：调用请求（只是一段文字，此刻什么都没发生）", reply)
    print(f"此刻，空调真实状态：{car.STATE['ac_celsius']} 度")

    # 第 3 步：程序解析请求，自己执行函数，把结果作为一条新消息追加进去
    call = reply["tool_calls"][0]
    result = car.run_tool(call["name"], json.loads(call["arguments"]))
    tool_message = {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)}
    messages.append(tool_message)
    show("第 3 步　程序执行函数，结果 → 模型", tool_message)
    print(f"此刻，空调真实状态：{car.STATE['ac_celsius']} 度")

    # 第 4 步：模型读到结果，生成给用户的最终回复
    final = stand_in_model(messages, car.TOOLS)
    messages.append(final)
    show("第 4 步　模型 → 用户：最终回复", final)

    print(f"\n一次工具调用，模型被调用 2 次，消息列表从 1 条涨到 {len(messages)} 条。")
    print(f"工具清单序列化后 {len(json.dumps(car.TOOLS, ensure_ascii=False))} 个字符，每次调用模型都要带上。")
