import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router'
import { LiveScreen } from '@/live/LiveScreen'
import { Ask } from '@/screens/Ask'
import { Cards } from '@/screens/Cards'
import { Recap } from '@/screens/Recap'
import { AppShell } from '@/shell/AppShell'

// The projector view (and its QR code library) stays out of the phone bundle.
const StageView = lazy(() => import('@/stage/StageView').then((m) => ({ default: m.StageView })))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<LiveScreen />} />
          <Route path="recap" element={<Recap />} />
          <Route path="cards" element={<Cards />} />
          <Route path="ask" element={<Ask />} />
        </Route>
        <Route
          path="stage"
          element={
            <Suspense fallback={null}>
              <StageView />
            </Suspense>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
