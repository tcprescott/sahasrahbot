import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { HomePage } from './pages/HomePage';
import { PresetsListPage } from './pages/presets/PresetsListPage';
import { AsyncLeaderboardPage } from './pages/async-tournament/AsyncLeaderboardPage';
import { TournamentSubmitPage } from './pages/tournament/TournamentSubmitPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/presets', element: <PresetsListPage /> },
      { path: '/async/leaderboard/:id', element: <AsyncLeaderboardPage /> },
      { path: '/submit/:event', element: <TournamentSubmitPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
