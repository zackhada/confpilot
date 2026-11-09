import { BrowserRouter, Route, Routes } from 'react-router'
import { LiveScreen } from '@/live/LiveScreen'
import { Ask } from '@/screens/Ask'
import { Cards } from '@/screens/Cards'
import { Recap } from '@/screens/Recap'
import { AppShell } from '@/shell/AppShell'
import { StageView } from '@/stage/StageView'

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
        <Route path="stage" element={<StageView />} />
      </Routes>
    </BrowserRouter>
  )
}
