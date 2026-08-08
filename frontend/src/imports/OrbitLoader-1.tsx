import { motion } from 'framer-motion'

interface OrbitLoaderProps {
  label?: string
  size?: number
}

export function OrbitLoader({ label = 'Thinking…', size = 100 }: OrbitLoaderProps) {
  const containerSize = size + 40

  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 gap-6">
      {/* 3D Orbit Space */}
      <div 
        className="relative flex items-center justify-center"
        style={{ width: containerSize, height: containerSize }}
      >
        {/* Ambient background glow */}
        <div className="absolute inset-4 rounded-full bg-rust/5 blur-xl animate-pulse" />

        {/* Orbit Path 1 (Inner) */}
        <div 
          className="absolute rounded-full border border-border/40"
          style={{ width: size * 0.5, height: size * 0.5 }}
        />
        
        {/* Orbit Path 2 (Mid) */}
        <div 
          className="absolute rounded-full border border-border/30"
          style={{ width: size * 0.8, height: size * 0.8 }}
        />

        {/* Orbit Path 3 (Outer) */}
        <div 
          className="absolute rounded-full border border-border/20"
          style={{ width: size, height: size }}
        />

        {/* Glowing Sun Core */}
        <motion.div 
          className="absolute rounded-full bg-gradient-to-tr from-rust to-accent shadow-lg shadow-rust/40 z-10"
          style={{ width: size * 0.28, height: size * 0.28 }}
          animate={{
            scale: [1, 1.15, 1],
            boxShadow: [
              '0px 4px 12px rgba(217, 119, 6, 0.4)',
              '0px 4px 24px rgba(217, 119, 6, 0.6)',
              '0px 4px 12px rgba(217, 119, 6, 0.4)'
            ]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />

        {/* Orbiting Planet 1 (Inner) */}
        <motion.div
          className="absolute w-2 h-2 rounded-full bg-rust"
          animate={{ rotate: 360 }}
          style={{ originX: 0.5, originY: 0.5, left: containerSize / 2 - 4 }}
          transition={{
            duration: 1.8,
            repeat: Infinity,
            ease: "linear"
          }}
        >
          <div style={{ transform: `translateY(-${size * 0.25}px)` }} className="w-2.5 h-2.5 rounded-full bg-rust shadow-sm" />
        </motion.div>

        {/* Orbiting Planet 2 (Mid) */}
        <motion.div
          className="absolute w-2.5 h-2.5 rounded-full bg-accent"
          animate={{ rotate: -360 }}
          style={{ originX: 0.5, originY: 0.5, left: containerSize / 2 - 5 }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "linear"
          }}
        >
          <div style={{ transform: `translateY(${size * 0.4}px)` }} className="w-3 h-3 rounded-full bg-accent shadow-sm" />
        </motion.div>

        {/* Orbiting Planet 3 (Outer) */}
        <motion.div
          className="absolute w-2 h-2 rounded-full bg-text-muted"
          animate={{ rotate: 360 }}
          style={{ originX: 0.5, originY: 0.5, left: containerSize / 2 - 4 }}
          transition={{
            duration: 4.5,
            repeat: Infinity,
            ease: "linear"
          }}
        >
          <div style={{ transform: `translateY(-${size * 0.5}px)` }} className="w-2 h-2 rounded-full bg-text-muted opacity-80" />
        </motion.div>
      </div>

      {/* Loading Label */}
      <div className="flex flex-col items-center gap-1">
        <span className="text-xs font-bold uppercase tracking-wider text-text-muted">
          {label}
        </span>
        <span className="text-[10px] text-text-muted/60 font-medium">
          Securing agent context...
        </span>
      </div>
    </div>
  )
}
