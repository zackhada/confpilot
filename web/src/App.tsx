import { BrowserRouter, Route, Routes } from 'react-router'
import { LiveScreen } from '@/live/LiveScreen'
import { ComingSoon } from '@/screens/ComingSoon'
import { AppShell } from '@/shell/AppShell'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<LiveScreen />} />
          <Route path="recap" element={<ComingSoon title="Recap">Your recap appears after a talk.</ComingSoon>} />
          <Route path="cards" element={<ComingSoon title="Cards">Saved terms become flashcards.</ComingSoon>} />
          <Route path="ask" element={<ComingSoon title="Ask">Search what you heard.</ComingSoon>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
