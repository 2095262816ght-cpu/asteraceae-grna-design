# CRISPRon WSL 环境恢复记录（2026-09-09/10）

## 结论
**WSL 路线本次未走通：虚拟机平台（Virtual Machine Platform）组件未启用，WSL2 当前无法运行任何发行版；已 staged 启用，需重启系统后重试。**
仓库克隆与 CRISPRoff 组件预下载已完成，重启后可直接续跑环境搭建。

## 各步骤结果

| 项目 | 状态 | 说明 |
|---|---|---|
| WSL Ubuntu-22.04 安装 | ❌ 未完成（阻塞） | 见下方错误 |
| CRISPRon 仓库克隆 | ✅ 完成 | `D:\lifesciencechallenge\cs_pipeline\tools\CRISPRon`（经 Clash 代理） |
| CRISPRoff 组件下载 | ✅ 完成（预下载到 Windows 侧） | `env\crisproff_dl\`，两个 tar 包均校验通过 |
| Miniconda / crispron conda 环境 | ❌ 未开始 | 依赖 WSL |
| `bin/test.sh` 验证 | ❌ 未跑 | 依赖 WSL |
| 示例序列打分 | ❌ 未跑 | 依赖 WSL |

## 确切错误信息

1. `wsl -l -v`：只剩 `docker-desktop`（Stopped, WSL2）。
2. `wsl --install -d Ubuntu-22.04 --no-launch`（两种形式均试）：
   退出码 0，但输出：`请求的操作成功。直到重新启动系统前更改将不会生效。`
   → 安装被 staged，重启前不生效。
3. `wsl -d Ubuntu-22.04 -u root -- bash -c "echo OK"`：
   `不存在具有所提供名称的分发。错误代码: Wsl/Service/WSL_E_DISTRO_NOT_FOUND`
4. `wsl --status`（根因）：
   `当前计算机配置不支持 WSL2。请启用"虚拟机平台"可选组件，并确保在 BIOS 中启用虚拟化。`
5. `sc query vmcompute`：`失败 1060: 指定的服务未安装。`
   → 虚拟机平台组件确实处于未安装/未启用状态（docker-desktop 发行版只是注册残留）。
6. 当前 shell **无管理员权限**：`net session` 拒绝；`dism /online /get-featureinfo` 退出码 228。
   但 `wsl --install` 报"成功、待重启"，说明组件启用已被 staged（可能经 UAC 自动提权），重启后应生效。

## 已完成的准备工作（重启后直接用）

- CRISPRon 仓库：`D:\lifesciencechallenge\cs_pipeline\tools\CRISPRon`
  - 结构已核对：`bin/test.sh`、`bin/CRISPRon.sh` 存在；`data/model/` 不存在（setup 脚本会 `mkdir -p`，无需改脚本路径）。
  - 注意：官方 `environment.yml` 是全量注释环境（含 bedtools/blat/repeatmasker 等），setup 脚本的精简依赖列表（python=3.10 tensorflow=2.14 viennarna=2.6.4 biopython pandas numpy scikit-learn）对 test.sh 足够，无需变更。
- CRISPRoff 组件：`D:\lifesciencechallenge\cs_pipeline\env\crisproff_dl\`
  - `crisproff-1.1.2.tar.gz`（24.0 MB）、`CRISPRspec_CRISPRoff_pipeline.v1.1.1.tar.gz`（12.8 MB），`tar -tzf` 校验通过，关键文件 `CRISPRspec_CRISPRoff_pipeline.py`、`energy_dics.pkl` 均在 v1.1.1 包内。
  - rth.dk 直连超时，实际经 Clash 代理（127.0.0.1:7897）下载成功。

## 重启后的下一步（按序执行）

1. 重启 Windows（使虚拟机平台组件生效）。如重启后 `wsl --status` 仍报不支持 WSL2，需管理员手动执行
   `dism /online /enable-feature /featurename:VirtualMachinePlatform /all` 并确认 BIOS 虚拟化已开。
2. `wsl --install -d Ubuntu-22.04 --no-launch`，然后 `wsl -d Ubuntu-22.04 -u root -- bash -c "echo OK"` 验证。
3. WSL 内装 Miniconda（清华镜像直连）：
   `wget -q https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/mc.sh && bash /tmp/mc.sh -b -p /root/miniconda3`，并写 `/root/.condarc` 指向 tuna 镜像。
4. 把预下载的组件放进 WSL 预期位置，跳过脚本里的下载步骤：
   `mkdir -p /root/crisproff_dl && cp /mnt/d/lifesciencechallenge/cs_pipeline/env/crisproff_dl/*.tar.gz /root/crisproff_dl/`
   （setup 脚本 `[ -f ... ] || wget` 逻辑会自动跳过下载。）
5. 以 root 跑 setup（`~` 即 `/root`，脚本里 `~/miniconda3` 与 `~/crisproff_dl` 无需改动）：
   `MSYS_NO_PATHCONV=1 wsl -d Ubuntu-22.04 -u root -- bash /mnt/d/lifesciencechallenge/cs_pipeline/env/setup_crispron_wsl.sh`
6. 跑通 `bin/test.sh`（341 条序列出分）后，按 `scripts/03_score_crispron.py` / `env/run_crispron_wsl.sh` 的方式对示例序列
   `ATCGGCTAAGCTAGGCTAGCATCGTGGATC` 打分验证。

## 备注
- 若 WSL 在重启后仍不可用，备选方案：修 Docker Desktop 跑 Linux 容器（同样依赖 WSL2/Hyper-V，同源问题），或改用纯序列特征 + 已训练权重的 Windows 原生推理（tensorflow 2.14 无 win-64 原生包，需降到 ≤2.10 或走 CPU 版 pip 镜像，精度未验证）。
