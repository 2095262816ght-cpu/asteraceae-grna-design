"""计A → 计B 的模型接口（9.17 交付），约定见《分工详案_计算机系.md》0.4 节。

计B 只调 predict_efficiency()，不接触模型内部；
模型文件 results/meta_model_ridge_0919.joblib 与公开模型打分由本模块内部加载。
"""


def predict_efficiency(seq30_list: list[str]) -> list[float]:
    """输入30bp序列（4nt上游+20nt guide+3nt PAM+3nt下游），返回集成模型预测分数（与indel_pct同尺度的相对分数）。"""
    raise NotImplementedError("9.17 由计A 实现：内部串联 crisprScore 打分 → 特征计算 → 岭回归")
