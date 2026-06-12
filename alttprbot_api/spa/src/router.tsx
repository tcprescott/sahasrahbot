import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { HomePage } from './pages/HomePage';
import { PresetsListPage } from './pages/presets/PresetsListPage';
import { AsyncLeaderboardPage } from './pages/async-tournament/AsyncLeaderboardPage';
import { AsyncDashboardPage } from './pages/async-tournament/AsyncDashboardPage';
import { AsyncPlayerPage } from './pages/async-tournament/AsyncPlayerPage';
import { TournamentSubmitPage } from './pages/tournament/TournamentSubmitPage';
import { ProfilePage } from './pages/ProfilePage';
import { RaceTimeVerifiedPage } from './pages/RaceTimeVerifiedPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/presets', element: <PresetsListPage /> },
      { path: '/async/leaderboard/:id', element: <AsyncLeaderboardPage /> },
      { path: '/async/races/:id', element: <AsyncDashboardPage /> },
      { path: '/async/player/:tournamentId/:userId', element: <AsyncPlayerPage /> },
      { path: '/submit/:event', element: <TournamentSubmitPage /> },
      { path: '/me', element: <ProfilePage /> },
      { path: '/racetime/verified', element: <RaceTimeVerifiedPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
