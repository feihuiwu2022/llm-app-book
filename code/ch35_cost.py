"""第 35 章配套代码：成本与延迟账本。只用标准库。
运行：python code/ch35_cost.py

所有单价、速度都是为了演示而假设的整数，不是任何厂商的报价。
用法是把 PRICE 和 SPEED 换成你自己的合同价和实测值，公式不变。
"""

# 假设单价，单位：元 / 百万 token
PRICE = {"input": 10.0, "cached_input": 1.0, "output": 40.0}
# 假设速度：首字延迟（秒）和输出速度（token / 秒）
SPEED = {"ttft": 0.8, "tokens_per_second": 50}


def cost(input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    """一次调用的费用（元）。cached_tokens 是输入里命中缓存的部分。"""
    fresh = input_tokens - cached_tokens
    return (fresh * PRICE["input"] + cached_tokens * PRICE["cached_input"]
            + output_tokens * PRICE["output"]) / 1_000_000


def latency(output_tokens: int) -> float:
    """一次调用的耗时（秒）= 首字延迟 + 输出 token 数 ÷ 输出速度。"""
    return SPEED["ttft"] + output_tokens / SPEED["tokens_per_second"]


def agent_run(fixed: int, per_turn: int, output: int, turns: int, cache: bool = False):
    """Agent 跑 turns 轮的总账。

    fixed    每轮都带的固定前缀：系统提示词 + 工具清单
    per_turn 每轮新增进上下文的量：上一轮的输出 + 工具结果
    output   每轮模型输出的 token 数
    cache    是否开启提示缓存：开启后，上一轮已经发过的前缀按缓存价计
    """
    total_in = total_cost = total_time = 0.0
    for t in range(turns):
        tokens_in = fixed + t * per_turn
        cached = (fixed + max(t - 1, 0) * per_turn) if (cache and t > 0) else 0
        total_in += tokens_in
        total_cost += cost(tokens_in, output, cached)
        total_time += latency(output)
    return int(total_in), total_cost, total_time


if __name__ == "__main__":
    print("一、单次调用：三种架构回答同一个问题（输出都是 200 token）")
    for label, tokens_in, cached in [
        ("裸问（不带资料）", 100, 0),
        ("RAG（5 块 × 400 字）", 2_100, 0),
        ("整本手册放进上下文", 200_100, 0),
        ("整本手册 + 缓存命中", 200_100, 200_000),
    ]:
        c = cost(tokens_in, 200, cached)
        print(f"  {label:<14} 输入 {tokens_in:>7} token  费用 {c:.4f} 元  每天一万次 {c * 10_000:>8.0f} 元")

    print("\n二、Agent：输入随轮数累加（固定前缀 2000，每轮新增 1500，每轮输出 300）")
    for turns in (1, 5, 10, 20):
        total_in, c, t = agent_run(2_000, 1_500, 300, turns)
        _, c_cached, _ = agent_run(2_000, 1_500, 300, turns, cache=True)
        print(f"  {turns:>2} 轮  累计输入 {total_in:>7} token  费用 {c:.4f} 元  "
              f"开缓存 {c_cached:.4f} 元  串行耗时 {t:.1f} 秒")

    print("\n三、延迟：输出长度决定耗时")
    for out in (50, 200, 1_000):
        print(f"  输出 {out:>4} token  耗时 {latency(out):.1f} 秒")
