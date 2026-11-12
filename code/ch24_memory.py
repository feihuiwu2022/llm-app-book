"""第 24 章配套代码：一个最小的长期记忆系统。只用标准库。
运行：python code/ch24_memory.py

三层结构：
  核心记忆  几条最要紧的事实，每次都放进系统提示词
  归档记忆  其余条目，按"时近度 + 重要度 + 相关度"检索后才进上下文
  原始记录  完整对话，不进上下文，只用来事后核对
"从对话里提炼出一条记忆"和"判断新旧是否冲突"在真实系统里由模型完成，
这里用写死的规则代替；存储、打分、检索、更新、衰减、合并都是真的。
相关度用第 6 章的玩具向量，没有语义能力，换成嵌入模型即可。
"""
from dataclasses import dataclass

from ch06_retrieve import cosine, embed

DECAY = 0.995  # 时近度：每过一小时乘一次


@dataclass
class Memory:
    text: str
    slot: str          # 这条记忆说的是哪件事，冲突判断靠它。真实系统由模型判断
    importance: int    # 1 到 10，写入时打分
    last_used: float   # 上次被用到的时刻（小时）


class MemoryStore:
    def __init__(self, replace_on_conflict: bool = True):
        self.items: list[Memory] = []
        self.replace_on_conflict = replace_on_conflict

    def write(self, text: str, slot: str, importance: int, now: float) -> str:
        """写入前先查有没有说同一件事的旧记忆，决定是新增还是更新。"""
        old = next((m for m in self.items if m.slot == slot), None)
        if old and self.replace_on_conflict:
            old.text, old.importance, old.last_used = text, importance, now
            return "更新"
        self.items.append(Memory(text, slot, importance, now))
        return "新增"

    def score(self, m: Memory, query: str, now: float) -> tuple[float, float, float]:
        recency = DECAY ** (now - m.last_used)
        return recency, m.importance / 10, cosine(embed(query), embed(m.text))

    def retrieve(self, query: str, now: float, k: int = 2) -> list[Memory]:
        ranked = sorted(self.items, key=lambda m: -sum(self.score(m, query, now)))
        for m in ranked[:k]:
            m.last_used = now  # 被用到的记忆刷新时近度，常用的不会沉底
        return ranked[:k]

    def forget(self, now: float, threshold: float = 0.3) -> list[str]:
        """遗忘：时近度加重要度低于阈值的条目删除。"""
        gone = [m for m in self.items if DECAY ** (now - m.last_used) + m.importance / 10 < threshold]
        self.items = [m for m in self.items if m not in gone]
        return [m.text for m in gone]


def build_context(core: list[str], recalled: list[Memory]) -> str:
    lines = ["【核心记忆】"] + core + ["【相关记忆】"] + [m.text for m in recalled]
    return "\n".join(lines)


def fill(store: MemoryStore) -> None:
    """模拟一个月的使用。时刻的单位是小时。"""
    store.write("座椅加热默认开二档", "座椅加热档位", 8, now=0)
    store.write("今天问过空调滤芯多久换一次", "滤芯咨询", 2, now=2)
    store.write("常去的充电站是城南站", "常用充电站", 6, now=30)
    store.write("右前轮慢漏气，已约周六补胎", "右前轮状态", 7, now=100)
    store.write("座椅加热默认开一档", "座椅加热档位", 8, now=400)   # 用户改主意了
    store.write("右前轮已补好", "右前轮状态", 5, now=430)


if __name__ == "__main__":
    core = ["用户称呼：王工", "车型：演示车型 2026 款"]
    now = 720  # 第 30 天
    query = "开一下座椅加热"

    for label, replace in [("只新增不更新", False), ("写入前查冲突并更新", True)]:
        store = MemoryStore(replace_on_conflict=replace)
        fill(store)
        print(f"== {label}：库里 {len(store.items)} 条 ==")
        for m in sorted(store.items, key=lambda m: -sum(store.score(m, query, now))):
            r, i, s = store.score(m, query, now)
            print(f"  {r + i + s:.2f} = 时近 {r:.2f} + 重要 {i:.2f} + 相关 {s:.2f}  {m.text}")
        recalled = store.retrieve(query, now)
        print("  取回：" + "；".join(m.text for m in recalled))
        clash = len({m.slot for m in recalled}) < len(recalled)
        print(f"  取回的两条{'互相矛盾' if clash else '没有矛盾'}\n")

    print("== 遗忘：第 60 天清理一次 ==")
    for text in store.forget(now=1440):
        print(f"  删除：{text}")
    print(f"  剩余 {len(store.items)} 条\n")

    print("== 最终放进上下文的内容 ==")
    print(build_context(core, store.retrieve(query, now=1440)))
