import { Outlet } from 'react-router'
import { TabBar } from './TabBar'

/** Phone frame: the screen fills the space above a fixed bottom tab bar. */
export function AppShell() {
  return (
    <div className="mx-auto flex h-dvh w-full max-w-xl flex-col bg-hall">
      <a
        href="#screen"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-fresh focus:px-4 focus:py-3 focus:font-semibold focus:text-fresh-ink"
      >
        Skip to content
      </a>
      <main id="screen" className="pt-safe flex min-h-0 flex-1 flex-col">
        <Outlet />
      </main>
      <TabBar />
    </div>
  )
}
