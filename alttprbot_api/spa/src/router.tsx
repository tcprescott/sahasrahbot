import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { HomePage } from './pages/HomePage';
import { PresetsListPage } from './pages/presets/PresetsListPage';
import { AsyncLeaderboardPage } from './pages/async-tournament/AsyncLeaderboardPage';
import { AsyncDashboardPage } from './pages/async-tournament/AsyncDashboardPage';
import { AsyncPlayerPage } from './pages/async-tournament/AsyncPlayerPage';
import { AsyncReattemptPage } from './pages/async-tournament/AsyncReattemptPage';
import { AsyncQueuePage } from './pages/async-tournament/AsyncQueuePage';
import { AsyncReviewPage } from './pages/async-tournament/AsyncReviewPage';
import { AsyncPoolsPage } from './pages/async-tournament/AsyncPoolsPage';
import { AsyncPermalinkPage } from './pages/async-tournament/AsyncPermalinkPage';
import { TournamentSubmitPage } from './pages/tournament/TournamentSubmitPage';
import { TriforceTextsPage } from './pages/TriforceTextsPage';
import { TriforceTextsModerationPage } from './pages/TriforceTextsModerationPage';
import { RankedChoicePage } from './pages/RankedChoicePage';
import { PresetNamespacePage } from './pages/presets/PresetNamespacePage';
import { PresetViewPage } from './pages/presets/PresetViewPage';
import { PresetCreatePage } from './pages/presets/PresetCreatePage';
import { ProfilePage } from './pages/ProfilePage';
import { RaceTimeVerifiedPage } from './pages/RaceTimeVerifiedPage';
import { PurgeMePage } from './pages/PurgeMePage';
import { ErrorPage } from './pages/ErrorPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/presets', element: <PresetsListPage /> },
      { path: '/presets/:namespace/create', element: <PresetCreatePage /> },
      { path: '/presets/manage/:namespace', element: <PresetNamespacePage /> },
      { path: '/presets/manage/:namespace/:randomizer', element: <PresetNamespacePage /> },
      { path: '/presets/manage/:namespace/:randomizer/:preset', element: <PresetViewPage /> },
      { path: '/async/leaderboard/:id', element: <AsyncLeaderboardPage /> },
      { path: '/async/races/:id', element: <AsyncDashboardPage /> },
      { path: '/async/races/:id/reattempt', element: <AsyncReattemptPage /> },
      { path: '/async/races/:id/queue', element: <AsyncQueuePage /> },
      { path: '/async/races/:id/review/:raceId', element: <AsyncReviewPage /> },
      { path: '/async/pools/:id', element: <AsyncPoolsPage /> },
      { path: '/async/permalink/:id/:pid', element: <AsyncPermalinkPage /> },
      { path: '/async/player/:tournamentId/:userId', element: <AsyncPlayerPage /> },
      { path: '/submit/:event', element: <TournamentSubmitPage /> },
      { path: '/triforcetexts/:pool', element: <TriforceTextsPage /> },
      { path: '/triforcetexts/:pool/moderation', element: <TriforceTextsModerationPage /> },
      { path: '/ranked_choice/:id', element: <RankedChoicePage /> },
      { path: '/me', element: <ProfilePage /> },
      { path: '/purgeme', element: <PurgeMePage /> },
      { path: '/racetime/verified', element: <RaceTimeVerifiedPage /> },
      { path: '/error', element: <ErrorPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
