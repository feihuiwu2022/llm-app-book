"""第 19 章配套代码：ReAct 循环。只用标准库。
运行：python code/ch19_react.py

ReAct 的原始形态是纯文本协议：模型按"思考 / 行动"的格式续写，
程序用正则把行动抠出来执行，再把"观察"拼回提示词。
模型用替身代替，它根据已经出现的观察决定下一步，循环本身是真的。
"""
import json
import re

import car

PROMPT_HEAD = """你可以使用以下工具：
get_tire_pressure[] 读取四个轮胎的当前胎压
search_manual[关键词] 在车主手册里检索
finish[答案] 给出最终答案并结束

请按下面的格式交替输出，每次只输出一组"思考"和"行动"：
思考：分析现在知道了什么、还缺什么
行动：工具名[参数]

问题：{question}
"""


def stand_in_model(prompt: str) -> str:
    """替身模型：数一数提示词里已有几条观察，决定下一步。真实模型在这里是续写。"""
    observations = re.findall(r"观察：(.*)", prompt)
    if len(observations) == 0:
        return "思考：要判断胎压正不正常，先得知道现在四个轮胎各是多少。\n行动：get_tire_pressure[]"
    if len(observations) == 1:
        return "思考：右前185明显比其他三个低，但我不知道这款车的标准值和报警线。\n行动：search_manual[胎压标准值]"
    if len(observations) == 2:
        return "思考：标准值查到了，前轮240、后轮250，还缺报警线是多少。\n行动：search_manual[胎压低于多少报警]"
    return (
        "思考：前轮标准240，右前只有185，低于报警线190；其余三个与标准相差不超过2。信息够了。\n"
        "行动：finish[右前轮胎压185千帕，低于190千帕的报警线，也远低于前轮标准240千帕，"
        "请尽快减速靠边检查；其余三个轮胎正常。]"
    )


def react(question: str, max_steps: int = 6) -> str:
    prompt = PROMPT_HEAD.format(question=question)
    for step in range(1, max_steps + 1):
        output = stand_in_model(prompt)
        print(f"--- 第 {step} 轮 ---\n{output}")
        match = re.search(r"行动：(\w+)\[(.*)\]", output, re.S)
        if not match:  # 模型没按格式写：把错误当作观察喂回去，让它重来
            observation = "格式错误，请按 行动：工具名[参数] 输出"
        else:
            name, arg = match.group(1), match.group(2).strip()
            if name == "finish":
                return arg
            arguments = {"query": arg} if name == "search_manual" else {}
            observation = car.run_tool(name, arguments)
            if not isinstance(observation, str):
                observation = json.dumps(observation, ensure_ascii=False)
        print(f"观察：{observation}")
        prompt += f"{output}\n观察：{observation}\n"
    return "达到步数上限，未完成"


if __name__ == "__main__":
    answer = react("我的胎压正常吗？")
    print(f"\n最终答案：{answer}")
