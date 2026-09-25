# ADR 0003: 统一靶位点规格与生物物理特征单点定义 (SequenceSpec)

## 状态
Accepted

## 背景与上下文
CRISPR/Cas9 的靶位点（30bp seq30）是整个管线最基础的数据原子。然而在现有代码中，对该实体的定义与计算出现了明显的浅层分散与算法漂移：
1. **合法性校验**：`app/app.py` 中使用 `SEQ_RE` 正则和切片检查长度、字符集与 NGG PAM；`predict.py` 中使用 `assert len(s) == 30`；
2. **切片常量**：`features_common.py` 中定义了 `GUIDE_SLICE = slice(4, 24)`、`SEED_SLICE = slice(18, 24)`；
3. **物理特征计算歧义**：
   - `demo/prepare_demo_data.py` 使用简易的 Wallace 公式计算 Tm：`2*(A+T) + 4*(G+C)`；
   - `scripts/features_common.py` 使用 Biopython `Tm_NN` 计算近邻热力学 Tm；
   - 在 `grna-demo` 环境中未安装 `Bio`，直接引用 `features_common.py` 会抛出 `ModuleNotFoundError`。

## 架构决议
1. 建立领域核心模块 `cs_pipeline/core/sequence_spec.py`。
2. 封装 `SequenceSpec` 领域值对象：
   - 输入即校验：提供 `SequenceSpec.parse(seq)` 与 `SequenceSpec.validate(seq)`，集中处理 30bp 长度、IUPAC A/C/G/T 合法性及 NGG PAM 契约；
   - 结构化访问：提供 `.guide` (20nt)、`.pam` (3nt)、`.seed` (6nt)、`.flank_5p` (4nt)、`.flank_3p` (3nt) 只读属性；
   - 统一物理特征：内置纯 Python 无依赖的近邻模型（SantaLucia 1998 经典热力学参数，当未安装 `Bio` 时平滑无缝降级，与 `Tm_NN` 精度对齐）及 GC% 计算，杜绝 Wallace 与 NN 的口径不一致。
3. 作为单一事实来源供 `app/app.py`、`scripts/predict.py`、`scripts/features_common.py` 共享。

## 收益与验证
- **Locality**：序列结构契约与物理计算彻底单点化；
- **环境解耦**：消除轻量运行环境（如 demo 环境或客户端环境）对 Biopython 的硬性绑定；
- **防止静默偏离**：杜绝因计算公式不同导致的特征漂移。
