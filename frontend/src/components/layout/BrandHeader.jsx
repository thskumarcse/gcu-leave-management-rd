import logo from '../../assets/logo.png'

export default function BrandHeader({ right }) {
  return (
    <header className="border-b border-ink-200 bg-ink-950">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-3">
          <img
            src={logo}
            alt="Girijananda Chowdhury University emblem"
            className="h-14 w-14 shrink-0 rounded-full object-cover"
          />
          <div>
            <p className="text-sm font-medium tracking-wide text-ink-300">
              Girijananda Chowdhury University
            </p>
            <h1 className="font-display text-xl font-semibold text-white">
              Leave Management System
            </h1>
          </div>
        </div>
        {right ? <div className="text-sm text-ink-300">{right}</div> : null}
      </div>
    </header>
  )
}
