import React from 'react'

// 背景细胞器点缀：叶绿体与线粒体，形态刻意区分——
// 叶绿体：扁平椭球双层膜，内含基粒（类囊体堆叠的圆盘柱）与基质片层，绿色系（光合作用）；
// 线粒体：豆状双层膜，内膜向质内折叠成嵴（圆指状褶皱），暖橙系（能量代谢）。
// 数量上叶绿体多于线粒体。全 SVG 手绘，渐变 + 细描边 + 柔光，位于毛玻璃之下作色场点缀。

const Chloroplast: React.FC<{ id: string }> = ({ id }) => (
  <svg viewBox="0 0 140 92" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id={`cp-${id}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#bbf7d0" />
        <stop offset="0.5" stopColor="#4ade80" />
        <stop offset="1" stopColor="#16a34a" />
      </linearGradient>
    </defs>
    {/* 外膜 */}
    <ellipse cx="70" cy="46" rx="66" ry="42" fill={`url(#cp-${id})`} stroke="#15803d" strokeWidth="3" />
    {/* 内膜 */}
    <ellipse cx="70" cy="46" rx="58" ry="34" fill="none" stroke="#166534" strokeWidth="1.5" opacity="0.55" />
    {/* 顶部高光 */}
    <path d="M22 34 C 34 18, 58 12, 78 13" stroke="white" strokeWidth="3" opacity="0.4" strokeLinecap="round" />
    {/* 基质片层：连接基粒的细线 */}
    <path d="M30 54 C 46 46, 56 62, 72 52 S 100 44, 112 54" stroke="#166534" strokeWidth="2" opacity="0.5" />
    <path d="M34 38 C 50 44, 60 30, 76 38 S 102 46, 110 38" stroke="#166534" strokeWidth="1.6" opacity="0.35" />
    {/* 基粒：类囊体堆叠的圆盘柱 ×3 */}
    {[
      { x: 26, y: 32, r: -8 },
      { x: 62, y: 42, r: 5 },
      { x: 96, y: 30, r: -4 },
    ].map((g, i) => (
      <g key={i} transform={`rotate(${g.r} ${g.x + 11} ${g.y + 12})`}>
        {[0, 1, 2, 3].map((d) => (
          <rect
            key={d}
            x={g.x}
            y={g.y + d * 6.5}
            width="22"
            height="5.5"
            rx="2.75"
            fill="#15803d"
            stroke="#14532d"
            strokeWidth="1"
          />
        ))}
      </g>
    ))}
    {/* 淀粉粒 */}
    <ellipse cx="48" cy="62" rx="7" ry="5" fill="#f7fee7" stroke="#bef264" strokeWidth="1.2" />
    <ellipse cx="102" cy="58" rx="5" ry="3.6" fill="#f7fee7" stroke="#bef264" strokeWidth="1.1" opacity="0.9" />
  </svg>
)

const Mitochondrion: React.FC<{ id: string }> = ({ id }) => (
  <svg viewBox="0 0 150 72" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id={`mt-${id}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#fed7aa" />
        <stop offset="0.5" stopColor="#fb923c" />
        <stop offset="1" stopColor="#ea580c" />
      </linearGradient>
    </defs>
    {/* 外膜：豆状 */}
    <path
      d="M20 34 C 20 16, 42 10, 74 10 C 108 10, 134 16, 134 34 C 134 52, 108 62, 74 62 C 42 62, 20 52, 20 34 Z"
      fill={`url(#mt-${id})`}
      stroke="#c2410c"
      strokeWidth="3"
    />
    {/* 内膜 */}
    <path
      d="M28 34 C 28 21, 47 17, 74 17 C 103 17, 126 21, 126 34 C 126 47, 103 55, 74 55 C 47 55, 28 47, 28 34 Z"
      fill="none"
      stroke="#9a3412"
      strokeWidth="1.4"
      opacity="0.55"
    />
    {/* 嵴：内膜向质内折叠的圆指状褶皱 */}
    {[34, 62, 90, 112].map((x, i) => (
      <path
        key={i}
        d={`M${x} 21 v ${9 + (i % 2) * 3} a 8 8 0 0 0 16 0 v -${9 + (i % 2) * 3}`}
        fill="#ea580c"
        opacity="0.8"
        stroke="#9a3412"
        strokeWidth="1.2"
      />
    ))}
    {/* 基质高光 */}
    <ellipse cx="72" cy="46" rx="26" ry="6" fill="white" opacity="0.18" />
    <path d="M30 28 C 40 18, 58 14, 74 14" stroke="white" strokeWidth="2.6" opacity="0.38" strokeLinecap="round" />
  </svg>
)

// 实例布局：叶绿体 4 枚（多）、线粒体 2 枚；错落分布在四周留白与卡片间隙后方
// drift = 慢速游走（16~22s），bob = 轻快浮沉（6~9s），两层叠加出漂浮感
const INSTANCES = [
  { kind: 'cp' as const, left: '20%', top: '12%', size: 118, dur: 18, bob: 7, delay: 0 },
  { kind: 'cp' as const, left: '86%', top: '8%', size: 96, dur: 21, bob: 6, delay: 3 },
  { kind: 'cp' as const, left: '80%', top: '72%', size: 132, dur: 16, bob: 8, delay: 6 },
  { kind: 'cp' as const, left: '28%', top: '88%', size: 104, dur: 22, bob: 9, delay: 1.5 },
  { kind: 'mt' as const, left: '19%', top: '86%', size: 118, dur: 19, bob: 7.5, delay: 4 },
  { kind: 'mt' as const, left: '93%', top: '42%', size: 102, dur: 17, bob: 6.5, delay: 8 },
]

export const OrganelleDecor: React.FC = () => (
  <>
    {INSTANCES.map((o, i) => (
      <div
        key={`org-${i}`}
        className="absolute"
        style={{ left: o.left, top: o.top, width: o.size, transform: 'translate(-50%, -50%)' }}
      >
        <div
          style={{
            width: '100%',
            animation: `organelle-drift ${o.dur}s ease-in-out ${o.delay}s infinite`,
          }}
        >
          <div
            style={{
              width: '100%',
              filter: `drop-shadow(0 6px 18px ${o.kind === 'cp' ? 'rgb(22 163 74 / 0.22)' : 'rgb(234 88 12 / 0.2)'})`,
              animation: `organelle-bob ${o.bob}s ease-in-out ${o.delay / 2}s infinite`,
            }}
          >
            {o.kind === 'cp' ? <Chloroplast id={`c${i}`} /> : <Mitochondrion id={`m${i}`} />}
          </div>
        </div>
      </div>
    ))}
  </>
)
