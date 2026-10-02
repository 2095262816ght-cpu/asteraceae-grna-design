import React from 'react'
import { OrganelleDecor } from './Organelles'

// 背景动效层：一条从左下伸向右上的大号 3D DNA 双螺旋，绕自身中轴持续旋转
// （CSS 3D：perspective + preserve-3d，碱基横档按螺旋相位 rotateY 摆放，浏览器按深度自动排序）。
// 纵深感：外层 rotate(TILT_Z) rotateX(TILT_X) 让螺旋斜向后退——左下端近（放大）、右上端远（缩小），
// 两端再加透明度渐隐，像延伸进画面深处。
// 精致化：链段是带纵向高光的玻璃圆管，链节处有球珠"骨架原子"；球珠以
// "反向自转动画 + 静态反倾斜"billboard——无论螺旋转到哪个相位都像 3D 球体正对镜头。
// 另配呼吸光晕与微粒漂浮。全部走 transform/opacity（GPU 合成），位于毛玻璃之下供 backdrop-filter 折射；
// prefers-reduced-motion 下全部静止（见 index.css）。

const RUNGS = 48 // 碱基对横档数（也是两条链的取样点数）
const HELIX_HEIGHT = 1650 // 螺旋总长（px），斜置+透视后恰好铺满视口对角线
const HELIX_RADIUS = 95 // 螺旋半径（px）
const DEG_PER_RUNG = 25 // 每级相位差：14.4 级一整圈
const TILT_Z = 45 // 对角线斜置角（左下→右上）
const TILT_X = 30 // 后仰纵深角
const SPACING = HELIX_HEIGHT / (RUNGS - 1) // 相邻横档间距（px），中轴刻度按此对齐

// 链上取样点（右手螺旋；Y 轴向下为正，与 CSS 坐标一致）
function helixPoint(i: number, side: 1 | -1) {
  const th = (i * DEG_PER_RUNG * Math.PI) / 180
  return {
    x: side * HELIX_RADIUS * Math.cos(th),
    y: (i / (RUNGS - 1)) * HELIX_HEIGHT - HELIX_HEIGHT / 2,
    z: -side * HELIX_RADIUS * Math.sin(th),
  }
}

// 两端渐隐：近端（左下）与远端（右上）溶入背景，强化纵深延伸感
const fadeAt = (i: number) => 0.35 + 0.65 * Math.sin((i / (RUNGS - 1)) * Math.PI)

// 碱基对横档：translateY + rotateY 相位
const RUNG_DATA = Array.from({ length: RUNGS }, (_, i) => ({
  y: helixPoint(i, 1).y,
  phase: i * DEG_PER_RUNG,
  fade: fadeAt(i),
}))

// 骨架链段：连接相邻取样点的 3D 线段（translate3d 中点 + rotateY/rotateZ 对齐弦向）
const STRAND_SEGMENTS = ([1, -1] as const).flatMap((side) =>
  Array.from({ length: RUNGS - 1 }, (_, i) => {
    const p1 = helixPoint(i, side)
    const p2 = helixPoint(i + 1, side)
    const d = { x: p2.x - p1.x, y: p2.y - p1.y, z: p2.z - p1.z }
    const len = Math.hypot(d.x, d.y, d.z)
    return {
      side,
      mx: (p1.x + p2.x) / 2,
      my: (p1.y + p2.y) / 2,
      mz: (p1.z + p2.z) / 2,
      len,
      alpha: Math.atan2(-d.z, d.x),
      beta: Math.atan2(d.y, Math.hypot(d.x, d.z)),
      fade: (fadeAt(i) + fadeAt(i + 1)) / 2,
    }
  })
)

// 链节球珠（同时是横档与链段的接点）：取样点处的"骨架原子"
const BEAD_DATA = ([1, -1] as const).flatMap((side) =>
  Array.from({ length: RUNGS }, (_, i) => ({ side, ...helixPoint(i, side), fade: fadeAt(i) }))
)

// 玻璃圆管质感：沿链宽方向 高光→本色→暗缘 + 内阴影圆角光
const STRAND_TUBE: Record<1 | -1, React.CSSProperties> = {
  1: {
    background:
      'linear-gradient(180deg, rgb(233 255 245 / 0.95), rgb(110 231 183 / 0.95) 38%, rgb(16 185 129 / 0.9) 74%, rgb(6 120 90 / 0.88))',
    boxShadow:
      'inset 0 1.5px 1px rgb(255 255 255 / 0.75), inset 0 -1.5px 2px rgb(4 120 87 / 0.4), 0 1px 8px rgb(16 185 129 / 0.3)',
  },
  [-1]: {
    background:
      'linear-gradient(180deg, rgb(245 243 255 / 0.95), rgb(196 181 253 / 0.95) 38%, rgb(139 92 246 / 0.9) 74%, rgb(100 60 200 / 0.88))',
    boxShadow:
      'inset 0 1.5px 1px rgb(255 255 255 / 0.75), inset 0 -1.5px 2px rgb(88 50 180 / 0.4), 0 1px 8px rgb(139 92 246 / 0.3)',
  },
}

// 球珠：单点高光的球面渐变（billboard 后任何相位都呈正圆）
const BEAD_FACE: Record<1 | -1, string> = {
  1: 'radial-gradient(circle at 32% 28%, rgb(255 255 255 / 0.98), rgb(134 239 195) 32%, rgb(52 211 153) 62%, rgb(5 150 105))',
  [-1]:
    'radial-gradient(circle at 32% 28%, rgb(255 255 255 / 0.98), rgb(216 204 254) 32%, rgb(167 139 250) 62%, rgb(124 58 237))',
}

const BigHelix: React.FC = () => (
  <div
    className="absolute inset-0"
    style={{
      perspective: '2000px',
    }}
  >
    {/* 螺旋本体：斜置为左下→右上，rotateX 使远端向画面深处退去（透视自动近大远小） */}
    <div
      className="absolute left-1/2 top-1/2"
      style={{
        width: HELIX_RADIUS * 2,
        height: HELIX_HEIGHT,
        marginLeft: -HELIX_RADIUS,
        marginTop: -HELIX_HEIGHT / 2,
        transform: `rotate(${TILT_Z}deg) rotateX(${TILT_X}deg)`,
        transformStyle: 'preserve-3d',
      }}
    >
      {/* 静态中轴：玻璃质长杆，刻度与横档接点对齐，双螺旋绕其旋转 */}
      <div
        className="absolute left-1/2 top-0 h-full w-2.5 -translate-x-1/2 rounded-full"
        style={{
          background: `repeating-linear-gradient(180deg, rgb(255 255 255 / 0.45) 0 2px, rgb(255 255 255 / 0) 2px ${SPACING}px), linear-gradient(90deg, rgb(255 255 255 / 0.12), rgb(255 255 255 / 0.62) 50%, rgb(255 255 255 / 0.12))`,
        }}
      />
      <div
        className="relative h-full w-full"
        style={{ transformStyle: 'preserve-3d', animation: 'helix-axis 32s linear infinite' }}
      >
        {/* 骨架链段：两条缠绕的玻璃圆管（按 3D 弦向对齐，旋转中不会侧向消失）
            transformOrigin: 0 0 —— 必须以弦中点为旋转原点；默认的盒中心会让链段绕偏心轴偏摆 */}
        {STRAND_SEGMENTS.map((s, i) => (
          <div
            key={`seg-${s.side}-${i}`}
            className="absolute left-1/2 top-1/2"
            style={{
              transform: `translate3d(${s.mx}px, ${s.my}px, ${s.mz}px) rotateY(${s.alpha}rad) rotateZ(${s.beta}rad)`,
              transformOrigin: '0 0',
              opacity: s.fade,
            }}
          >
            <div
              className="rounded-full"
              style={{
                width: s.len * 1.3,
                height: 13,
                marginLeft: -s.len * 0.65,
                marginTop: -6.5,
                ...STRAND_TUBE[s.side],
              }}
            />
          </div>
        ))}

        {/* 碱基对横档：白芯渐变细杆 + 端部球珠接点。transformOrigin 0 0 让杠以中轴为心自转，
            否则默认盒中心使整根杠绕偏心轴公转、两端甩出链条 */}
        {RUNG_DATA.map((r) => (
          <div
            key={r.y}
            className="absolute left-1/2 top-1/2"
            style={{
              transform: `translateY(${r.y}px) rotateY(${r.phase}deg)`,
              transformOrigin: '0 0',
              opacity: r.fade,
            }}
          >
            <div
              className="rounded-full"
              style={{
                width: HELIX_RADIUS * 2,
                height: 5,
                marginLeft: -HELIX_RADIUS,
                marginTop: -2.5,
                background:
                  'linear-gradient(90deg, rgb(16 185 129 / 0.55), rgb(220 252 231 / 0.8) 22%, rgb(255 255 255 / 0.95) 50%, rgb(237 233 254 / 0.8) 78%, rgb(139 92 246 / 0.55))',
                boxShadow: 'inset 0 1px 1px rgb(255 255 255 / 0.7)',
              }}
            />
          </div>
        ))}

        {/* 链节球珠：反向自转动画抵消螺旋自转 + 静态反倾斜抵消外层斜置 → 始终正对镜头的球体。
            注意：opacity 必须放在叶子形状层——分组属性会强制 transform-style: flat，
            若放在中间的 3D 包装层会把 billboard 反转压扁在局部平面上。 */}
        {BEAD_DATA.map((b) => (
          <div
            key={`bead-${b.side}-${b.x}-${b.y}`}
            className="absolute left-1/2 top-1/2"
            style={{
              transform: `translate3d(${b.x}px, ${b.y}px, ${b.z}px)`,
              transformStyle: 'preserve-3d',
            }}
          >
            <div
              style={{
                animation: 'helix-axis-reverse 32s linear infinite',
                transformOrigin: '0 0',
                transformStyle: 'preserve-3d',
              }}
            >
              <div
                className="rounded-full"
                style={{
                  width: 15,
                  height: 15,
                  marginLeft: -7.5,
                  marginTop: -7.5,
                  transform: `rotateX(${-TILT_X}deg) rotate(${-TILT_Z}deg)`,
                  background: BEAD_FACE[b.side],
                  boxShadow: `0 1px 6px ${b.side === 1 ? 'rgb(16 185 129 / 0.35)' : 'rgb(139 92 246 / 0.35)'}`,
                  opacity: b.fade,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
)

// memo：无 props 的纯装饰层，父组件（页签切换等）重渲染时不重建 200+ 动画节点
export const BackgroundMotion = React.memo(function BackgroundMotion() {
  return (
  <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-motion">
    {/* 呼吸光晕：让磨砂玻璃有柔和色场可折射（色相刻意加深，穿过玻璃后被 saturate 放大） */}
    <div
      className="absolute -left-24 -top-24 h-[560px] w-[560px] rounded-full"
      style={{
        background: 'radial-gradient(circle, rgb(244 114 182 / 0.42), transparent 70%)',
        animation: 'bg-breathe 26s ease-in-out infinite',
      }}
    />
    <div
      className="absolute right-[-180px] top-[18%] h-[640px] w-[640px] rounded-full"
      style={{
        background: 'radial-gradient(circle, rgb(167 139 250 / 0.42), transparent 70%)',
        animation: 'bg-breathe 32s ease-in-out 6s infinite',
      }}
    />
    <div
      className="absolute bottom-[-220px] left-[28%] h-[560px] w-[560px] rounded-full"
      style={{
        background: 'radial-gradient(circle, rgb(52 211 153 / 0.38), transparent 70%)',
        animation: 'bg-breathe 29s ease-in-out 11s infinite',
      }}
    />

    {/* 细胞器点缀：叶绿体（多）与线粒体（少），衬托生命科学主题 */}
    <OrganelleDecor />

    {/* 主角：从左下伸向右上的大号 3D 双螺旋，绕中轴旋转 */}
    {/* 静态辉光替代挂在旋转子树上的 drop-shadow：filter 会让整棵持续动画的 3D 子树每帧重算阴影栅格化 */}
    <div
      className="absolute left-1/2 top-1/2 h-[1500px] w-[420px] -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-full"
      style={{
        background:
          'radial-gradient(closest-side, rgb(34 197 94 / 0.22), rgb(34 197 94 / 0.08) 55%, transparent 75%)',
      }}
    />
    <div className="absolute inset-0" style={{ animation: 'bg-float 20s ease-in-out infinite alternate' }}>
      <BigHelix />
    </div>

    {/* 微粒：缓慢上浮的光点 */}
    {[0, 1, 2, 3, 4, 5].map((i) => (
      <span
        key={`dot-${i}`}
        className="absolute h-1.5 w-1.5 rounded-full bg-white/70"
        style={{
          left: `${14 + i * 15}%`,
          top: `${30 + (i % 3) * 22}%`,
          animation: `bg-drift-up ${18 + i * 3}s ease-in-out ${i * 2.6}s infinite`,
        }}
      />
    ))}
  </div>
  )
})
