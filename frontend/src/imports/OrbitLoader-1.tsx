interface OrbitLoaderProps {
  label?: string
  size?: number
}

export function OrbitLoader({ label = 'Thinking…', size = 80 }: OrbitLoaderProps) {
  const s = size
  const ringStyle = (inset: number, delay: string, dur: string) => ({
    position: 'absolute' as const,
    inset,
    borderRadius: '50%',
    border: `1.5px solid`,
    borderColor: 'rgba(181, 80, 46, 0.35)',
    animation: `orbitPulse ${dur} ease-in-out ${delay} infinite`,
  })

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column' as const,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        padding: '48px 24px',
      }}
    >
      {/* Orbit ring area — reserved for Framer Motion orbit animation */}
      <div
        style={{
          position: 'relative',
          width: s,
          height: s,
          flexShrink: 0,
        }}
        aria-label="Loading"
      >
        <div style={ringStyle(0, '0s', '2.8s')} />
        <div style={ringStyle(s * 0.12, '0.4s', '2.4s')} />
        <div style={ringStyle(s * 0.25, '0.8s', '2.0s')} />
        <div
          style={{
            position: 'absolute',
            inset: s * 0.38,
            borderRadius: '50%',
            backgroundColor: 'rgba(224, 164, 88, 0.18)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: s * 0.44,
            borderRadius: '50%',
            backgroundColor: 'rgba(181, 80, 46, 0.22)',
            animation: 'orbitPulse 1.8s ease-in-out 0.2s infinite',
          }}
        />
      </div>

      <span
        style={{
          fontSize: 13,
          letterSpacing: '0.06em',
          textTransform: 'uppercase' as const,
          color: '#7A6B63',
          fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
          fontWeight: 500,
        }}
      >
        {label}
      </span>
    </div>
  )
}
