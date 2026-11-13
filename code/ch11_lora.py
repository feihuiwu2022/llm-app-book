"""第 11 章配套代码：用纯 Python 从零训练一个 LoRA。只用标准库。
运行：python code/ch11_lora.py

一个 16×16 的权重矩阵 W 代表"底座模型"里的一层，全程冻结。
"新任务"要求这一层的行为变成 W + 目标变化量，其中目标变化量的秩是 2。
旁边挂两个小矩阵 A、B，只训练它们，看它们能不能把这个变化学出来。
真实的 LoRA 做的是同一件事，只是矩阵是 4096×4096，层有几十上百个。
"""
import random

D = 16       # 矩阵边长。真实模型里是几千
ALPHA = 4    # 缩放系数 alpha，实际生效的倍率是 alpha / r


def matvec(m, v):
    return [sum(a * b for a, b in zip(row, v)) for row in m]


def matmul(a, b):
    cols = list(zip(*b))
    return [[sum(x * y for x, y in zip(row, col)) for col in cols] for row in a]


def rand_matrix(rows, cols, rng, scale=1.0):
    return [[rng.gauss(0, scale) for _ in range(cols)] for _ in range(rows)]


def forward(W, A, B, x, scale):
    """h = W·x + (alpha/r)·B·(A·x)。前一项是冻结的底座，后一项是 LoRA 分支。"""
    ax = matvec(A, x)
    return [w + scale * b for w, b in zip(matvec(W, x), matvec(B, ax))], ax


def train(W, target, r, steps=3000, lr=0.004, seed=1):
    rng = random.Random(seed)
    scale = ALPHA / r
    lr = lr / scale                            # 倍率大时步子相应调小，否则容易发散
    A = rand_matrix(r, D, rng, scale=0.3)      # A 随机初始化
    B = [[0.0] * r for _ in range(D)]          # B 初始化为零，所以一开始 B·A = 0
    history = []
    for step in range(1, steps + 1):
        x = [rng.gauss(0, 1) for _ in range(D)]
        y = matvec(target, x)                  # 标准答案
        h, ax = forward(W, A, B, x, scale)     # 前向计算
        err = [hi - yi for hi, yi in zip(h, y)]
        loss = sum(e * e for e in err) / D     # 损失：输出与标准答案的均方差
        # 反向传播：只算 A、B 的梯度。W 没有梯度，也不更新
        bt_err = [sum(B[i][j] * err[i] for i in range(D)) for j in range(r)]
        for i in range(D):
            for j in range(r):
                B[i][j] -= lr * scale * err[i] * ax[j]
        for j in range(r):
            for k in range(D):
                A[j][k] -= lr * scale * bt_err[j] * x[k]
        history.append(loss)
    return A, B, history


if __name__ == "__main__":
    rng = random.Random(0)
    W = rand_matrix(D, D, rng)
    W_backup = [row[:] for row in W]
    # 新任务需要的权重变化：两个小矩阵相乘，秩为 2
    delta = matmul(rand_matrix(D, 2, rng), rand_matrix(2, D, rng))
    target = [[w + d for w, d in zip(rw, rd)] for rw, rd in zip(W, delta)]

    print(f"底座矩阵 W：{D}×{D} = {D * D} 个参数，全程冻结")
    for r in (1, 2, 4):
        print(f"  r={r} 时 LoRA 参数：A {r}×{D} + B {D}×{r} = {2 * r * D} 个，占 W 的 {2 * r * D / (D * D):.0%}")

    x = [rng.gauss(0, 1) for _ in range(D)]
    A, B, history = train(W, target, r=2)

    print("\n一、初始状态：B 全零，挂上 LoRA 后输出与底座完全相同")
    A0 = rand_matrix(2, D, random.Random(1), scale=0.3)
    B0 = [[0.0] * 2 for _ in range(D)]
    h0, _ = forward(W, A0, B0, x, ALPHA / 2)
    print(f"  与底座输出的最大差值：{max(abs(a - b) for a, b in zip(h0, matvec(W, x))):.6f}")

    print("\n二、训练过程（r=2）：损失逐步下降")
    for lo, hi in [(0, 50), (50, 200), (200, 500), (500, 1000), (2900, 3000)]:
        print(f"  第 {lo + 1:>4} 到 {hi:>4} 步平均损失：{sum(history[lo:hi]) / (hi - lo):.4f}")

    print("\n三、训练结束后")
    print(f"  底座 W 是否被改动：{'是' if W != W_backup else '否'}")
    scale = ALPHA / 2
    BA = matmul(B, A)
    merged = [[w + scale * d for w, d in zip(rw, rd)] for rw, rd in zip(W, BA)]
    h_branch, _ = forward(W, A, B, x, scale)
    h_merged = matvec(merged, x)
    print(f"  旁挂计算与合并后计算的最大差值：{max(abs(a - b) for a, b in zip(h_branch, h_merged)):.6f}")
    gap = max(abs(scale * BA[i][j] - delta[i][j]) for i in range(D) for j in range(D))
    print(f"  学到的变化量与目标变化量的最大差值：{gap:.4f}")

    print("\n四、秩选多大：目标变化量的秩是 2")
    for r in (1, 2, 4):
        _, _, hist = train(W, target, r=r)
        print(f"  r={r}  最后 100 步平均损失：{sum(hist[-100:]) / 100:.4f}")
