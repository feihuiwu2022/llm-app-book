"""第 5 章配套代码：切块、账本复算、余弦相似度。只用标准库。
运行：python code/ch05_chunk.py
"""
import math
from corpus import MANUAL


def chunk(text: str, size: int, overlap: int) -> list[str]:
    """定长切块：每块 size 个字，相邻两块重叠 overlap 个字。"""
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size]]


def budget(total_chars: int, size: int, overlap: int, dim: int) -> tuple[int, float]:
    """给定资料总字数，算出块数和向量库占用（float32，每维 4 字节）。"""
    n = math.ceil((total_chars - overlap) / (size - overlap))
    return n, n * dim * 4 / 1024 / 1024


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


if __name__ == "__main__":
    chunks = chunk(MANUAL, size=80, overlap=20)
    print(f"资料共 {len(MANUAL)} 字，切成 {len(chunks)} 块（每块 80 字，重叠 20 字）")
    for i, c in enumerate(chunks[:3]):
        print(f"  块{i}: {c}")

    print("\n账本复算：")
    for total, label in [(200_000, "一本 20 万字的手册"), (350_000_000, "100 万块规模的资料库")]:
        n, mb = budget(total, size=400, overlap=50, dim=1024)
        print(f"  {label}: {n} 块, 向量占用 {mb:.1f} MB")

    print("\n余弦相似度手算对照：")
    q, d1, d2 = [1, 2, 0], [2, 3, 1], [0, 1, 3]
    print(f"  问题 vs 文档1 = {cosine(q, d1):.3f}")
    print(f"  问题 vs 文档2 = {cosine(q, d2):.3f}")
