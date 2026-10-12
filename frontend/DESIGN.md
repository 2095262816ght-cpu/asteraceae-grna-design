# DESIGN.md — 菊科 CRISPR/Cas9 基因编辑与多组学决策系统 · 前端视觉系统

> 从已建成的界面记录（ground truth over intention）。文案契约见 `cs_pipeline/docs/USER_MANUAL.md` 第 3 章；
> 可见字符串冻结，本文件只描述视觉系统。方向契约见 `index.html` body 首个注释块（THESIS/OWN-WORLD/STORY/FIRST VIEWPORT/FORM/FINISH）。

## 世界（OWN-WORLD）

全天候科研数据工作台：**浅松绿毛玻璃侧栏 + 浅色毛玻璃工作区 + 浅色基因组图谱面板**。

| 角色 | 值 | 用途 |
|---|---|---|
| pine-900 | `#0E1F1A` | logo 字形等品牌深绿图形（侧栏/图谱卡已改为 brand-50 浅松绿玻璃，见「处置记录」） |
| pine-800 / 700 | `#17352B` / `#1D4234` | 深色面的分隔与按压态 |
| brand-500 / 600 | `#22C55E` / `#16A34A` | 品牌绿：logo、主操作、正向数据、激活指示 |
| surface / surface-sunken | `#FFFFFF` / `#F8FAF9` | 工作区卡片与页面底 |
| line / line-strong | `#E2E8F0` / `#CBD5E1` | 1px 细线（卡片边界、分隔线） |
| ink / ink-muted / ink-faint | `#0F172A` / `#64748B` / `#6B7280` | 正文 / 次级 / 三级（均 ≥4.5:1） |
| 语义色 | emerald / amber / rose / sky / purple | 状态徽章与数据分档（≥70 绿、40–70 琥珀、<40 灰） |

深色面上的次级文字用 `white/50–70` 透明度阶梯（≥5:1）。Tailwind 色板：`tailwind.config.js`（brand / pine / surface / line / ink 为 token，
其余语义色沿用内置）。

## 字体与排版

- Inter（`@fontsource/inter` latin 400–700 自托管，构建期打包，运行期零外链）；中文回落 PingFang SC / Microsoft YaHei。
- 数字与序列一律 `font-mono` + `tabular-nums`（坐标、PAM、分数、ID、耗时）。
- 字号阶梯：`text-2xs`(11px 表头/脚注) / `text-xs` / `text-sm`（正文与卡片标题）/ `text-lg`（页级标题）。
- **不用 `text-transform: uppercase`**——冻结文案的手册字形必须逐字渲染（30nt、DeepSpCas9、v2.1 等）。
- 标题 `tracking-tight` + `text-wrap: balance`；链接 `text-underline-offset: 2px`。

## 布局（Operate）

- 256px 固定浅松绿毛玻璃侧栏（<lg 断点转顶部栏）：品牌块（logo tile + 产品全名 + 副题）+ 垂直导航（3 个工作台，激活 = white/75 药丸 + brand-700 文字）。
- 工作区 `max-w-[1560px]`，纵向动线：服务状态条 → 检索/过滤工具卡 → 表达看板 → 基因组图谱 → 候选大表 → 浮动导出条。
- 卡片语言：`rounded-card`(16px) + 液态玻璃材质 `.card`（配方见「处置记录 · 全局液态玻璃」）。**不嵌套卡片**——卡内分区用
  分隔线或留白，不用带框小卡。
- 表格：两层分组表头（识别/定位/序列/活性/脱靶/多组学/评分），18 列锁定；窄容器横向滚动 + sticky 识别列
  （`sticky` 单元格 `bg-inherit` + 右侧 2px 柔化阴影分界）；行高 45px，数值右对齐。

## 组件（src/components/ui/）

Card / Button(primary·secondary·ghost·danger) / Badge(6 tone × soft·solid，`title` 透传) / Table(Table·Thead·Tbody·Tr·Th·Td，
支持 `numeric`·`sticky`·`width`) / Tabs(pill·underline·nav 三形态 + TabPanel keepMounted) / Dialog / Drawer
（焦点陷阱、Esc 关闭优先级 3>2>1、点遮罩关闭、焦点归还、滚动锁）/ InfoHint（原生 title）/ SegmentedControl /
Pagination / EmptyState / Spinner / Skeleton。工具：`lib/cn.ts`（clsx + tailwind-merge）。

## 状态与动效

- loading / error / empty 三态齐全；错误文案命名问题 + 恢复路径；「未计算」类诚实标注用虚线下划线 + `title` 全文。
- 唯一授权动效：工作区入场 `.rise`（0.38s，cubic-bezier(.16,1,.3,1)，起点 opacity .65 已可见；`prefers-reduced-motion` 关闭）。
- **背景动效系统（用户钉定）**：`BackgroundMotion` 固定动效层（`-z-10`，毛玻璃之下供折射）——
  8 个散点双螺旋走 `bg-spin-turn`（24s 轮播：转一整圈后静候，8 个 3s 错峰启动 = "一个一个转"，
  转动含 rotate+scaleX 伪 3D 扭转）+ `bg-float` 上下漂；3 个大光晕 `bg-breathe` 呼吸（26~32s）；
  6 颗微粒 `bg-drift-up` 缓慢上浮。全部 transform/opacity GPU 合成，`prefers-reduced-motion` 全部静止。
- 焦点：全局 `focus-visible:ring-2 ring-brand-500/40`（鼠标不显示）。

## 浏览器表面

`::selection` 品牌绿染色；双滚动条主题（浅色 10px 圆头 thumb + 侧栏同款弱化变体）；表单控件 `accent-brand-600`
统一复选框/滑块；基因组图谱的 ECharts 轴标签/分割线/dataZoom 全部用浅底可读色，tooltip 固定白底。

## 处置记录

- 表达看板诊断 banner（"⚠️ 弱表型警示：" 等）内嵌的 ⚠️/✅/ℹ️ emoji 属冻结文案的一部分，**文案冻结优先于
  "emoji 不作图标"纪律**，保留原样；banner 的图标系统由并排的 lucide 图标承担。
- **品牌绿减淡（用户钉定）**：logo tile 用 brand-300 薄荷底 + pine-900 深字形（替代 brand-500 实色块），
  表达看板目标组织高亮条降到 brand-400→teal-400；功能性文字绿（brand-600/700/800）与数据语义色保持不变以护对比度。
- **全局液态玻璃（用户钉定，配方移植自「毛玻璃」参考稿）**：页面底为粉→紫→天蓝→薄荷→暖黄的柔和多色渐变 +
  `BackgroundMotion` 动效层（毛玻璃必须"背后有内容"才显形）。**渐变底必须放在 fixed 图层（`.bg-motion`），
  不可用 body 的 `background-attachment: fixed`**——后者会被 `backdrop-filter` 漏采样，表现为
  "悬停才出现玻璃"的合成伪影（事故记录）。玻璃三层结构：
  ① 背景层 `background-image`（始终位于文字之下）= 指针追光径向高光（`--mx/--my` 由 `lib/glassPointer.ts`
  写入）+ 镜面渐变 + 分层半透明底。**白浊压低（常态透光率 ~82%，用户逐轮校准的定稿值）**——
  玻璃要透，背景色场（彩色光晕 + 双螺旋）要穿过来；
  ② 材质层 = `backdrop-filter: blur(16px) saturate(180%) brightness(1.06)`（饱和+提亮让背景色透进玻璃）
  + 多层阴影（外投影 + 顶部内高光 + 底部内暗边）；
  ③ 边缘层 = `::before` 1px 渐变反光环（`mask-composite` 挖环），模拟玻璃边缘对光源的折射。
  **光照方向右上角射入（用户钉定）**：反光环亮端、镜面渐变、投影偏移全部统一为右上→左下。
  四个材质类：`.card` 白玻璃（工作区卡片，带指针追光）/ `.glass-panel` 浅松绿玻璃（侧栏、基因组图谱卡——
  用户钉定：原 pine 深色与浅色世界对比过强，换浅色；`translateZ(0)` 主动合成层防固定层玻璃延迟显形，
  且**悬停零变化**——透明度恒定，不随鼠标改变）/ `.glass-pop` 高白度玻璃（Dialog / Drawer /
  浮动导出条 / 基因下拉，护正文对比度）/ `.glass-inner` 嵌套玻璃小卡（卡内分区、统计块、列表项、
  结果面板——**全卡片玻璃化**，仅输入框/按钮/表格行等控件保留实底）；背景光晕色相刻意加深
  （pink-500 / violet-400 / emerald-400）供玻璃折射；**不做 `prefers-reduced-transparency` 降级
  （用户钉定）**——曾按无障碍惯例降级为近实底，被用户系统命中后造成"玻璃全不透明"事故，
  玻璃透度是本世界的定稿视觉，任何机器上都一致；全处带 `-webkit-backdrop-filter` 前缀（Safari）。
- **Logo 为手绘 SVG**（`components/icons/DnaHelix.tsx`，两条镜像链 + 三档碱基对，统一 2px 圆头描边），
  替换 lucide Dna 在品牌位（侧栏 tile / 基因选择器 tile / 计算脱靶按钮 / favicon）的粗糊字形。

## 证据（截图 provenance）

`.impeccable/review/PROVENANCE.md` 记录每张截图的生成方式与脚本；产品本身不携带任何 raster 资产
（图标全部为 lucide SVG，字体自托管 woff2 随 dist 打包）。
