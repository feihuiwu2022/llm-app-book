"""第 6 章配套代码：向量召回、BM25 召回、RRF 融合、拼装提示词。只用标准库。
运行：python code/ch06_retrieve.py

注意：这里的"向量"是字二元组计数做成的玩具向量，只为演示流程，没有语义能力。
真实系统要换成嵌入模型，替换 embed() 一个函数即可。
"""
import math
from collections import Counter
from corpus import MANUAL
from ch05_chunk import chunk

DIM = 256


def bigrams(text: str) -> list[str]:
    return [text[i:i + 2] for i in range(len(text) - 1)]


def embed(text: str) -> list[float]:
    """玩具嵌入：把每个字二元组散列到 DIM 个桶里计数。"""
    v = [0.0] * DIM
    for g in bigrams(text):
        v[sum(ord(ch) for ch in g) % DIM] += 1.0
    return v


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def vector_search(query, chunks, vectors, k):
    qv = embed(query)
    scores = [(cosine(qv, v), i) for i, v in enumerate(vectors)]
    return [i for _, i in sorted(scores, reverse=True)[:k]]


def bm25_search(query, chunks, k, k1=1.5, b=0.75):
    docs = [Counter(bigrams(c)) for c in chunks]
    n = len(docs)
    avg_len = sum(sum(d.values()) for d in docs) / n
    scores = []
    for i, d in enumerate(docs):
        length = sum(d.values())
        s = 0.0
        for term in set(bigrams(query)):
            df = sum(1 for x in docs if term in x)
            if df == 0:
                continue
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            tf = d[term]
            s += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / avg_len))
        scores.append((s, i))
    return [i for _, i in sorted(scores, reverse=True)[:k]]


def rrf(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """倒数排名融合：每路结果按 1/(k+名次) 计分，累加后重排。"""
    score = Counter()
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            score[doc] += 1 / (k + rank)
    return sorted(score.items(), key=lambda x: -x[1])


def build_prompt(query, chunks, ids):
    refs = "\n".join(f"[{n}] {chunks[i]}" for n, i in enumerate(ids, start=1))
    return (
        "请只依据下面的资料回答问题，并在句末用 [编号] 标明依据。\n"
        "如果资料里没有答案，直接回答\"资料中未提及\"。\n\n"
        f"资料：\n{refs}\n\n问题：{query}"
    )


if __name__ == "__main__":
    chunks = chunk(MANUAL, size=80, overlap=20)
    vectors = [embed(c) for c in chunks]
    query = "胎压报警灯亮了是低于多少"

    vec = vector_search(query, chunks, vectors, k=4)
    bm = bm25_search(query, chunks, k=4)
    fused = rrf([vec, bm])

    print(f"问题：{query}")
    print(f"向量召回名次：{vec}")
    print(f"BM25 召回名次：{bm}")
    print("RRF 融合：")
    for doc, s in fused[:4]:
        print(f"  块{doc}  得分 {s:.5f}")

    top = [doc for doc, _ in fused[:2]]
    print("\n最终送给模型的提示词：\n")
    print(build_prompt(query, chunks, top))
