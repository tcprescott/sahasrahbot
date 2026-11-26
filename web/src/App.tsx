import { BrowserRouter, Navigate, Route, useParams } from 'react-router-dom'
import { SentryRoutes } from './telemetry'
import { ApiAccessScreen } from './apiaccess/ApiAccessScreen'
import { ConsentScreen } from './apiaccess/ConsentScreen'
import { AuditScreen } from './audit/AuditScreen'
import { SessionProvider } from './auth/SessionProvider'
import { TooltipProvider } from './components'
import { NamespaceScreen } from './presets/NamespaceScreen'
import { NamespacesScreen } from './presets/NamespacesScreen'
import { MyPresetsScreen } from './presets/MyPresetsScreen'
import { NewPresetScreen } from './presets/NewPresetScreen'
import { PresetScreen } from './presets/PresetScreen'
import { ElectionFormScreen } from './elections/ElectionFormScreen'
import { ElectionsScreen } from './elections/ElectionsScreen'
import { ResultsScreen } from './elections/ResultsScreen'
import { BallotScreen } from './ranked/BallotScreen'
import { ErrorScreen } from './screens/ErrorScreen'
import { HomeScreen } from './screens/HomeScreen'
import { MeScreen } from './screens/MeScreen'
import { NotFoundScreen } from './screens/NotFoundScreen'
import { PurgeScreen } from './screens/PurgeScreen'
import { ServerScreen } from './servers/ServerScreen'
import { ServersScreen } from './servers/ServersScreen'
import { SettingsSection } from './servers/SettingsSection'
import { AppShell } from './shell/AppShell'
import { ThemeProvider } from './theme/ThemeProvider'
import { SubmissionScreen } from './tournament/SubmissionScreen'
import { ModerationScreen } from './triforce/ModerationScreen'
import { TriforcePoolScreen } from './triforce/TriforcePoolScreen'
import { VoiceRolesSection } from './voiceroles/VoiceRolesSection'

/**
 * Page URLs are the ones the old server-rendered pages had, because Discord
 * messages and DMs already sent link to them (ballots, triforce text pools,
 * race settings forms, presets).
 */
export function App() {
  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={400}>
        <SessionProvider>
          <BrowserRouter>
            <SentryRoutes>
              <Route path="oauth/consent" element={<ConsentScreen />} />
              <Route element={<AppShell />}>
                <Route index element={<HomeScreen />} />
                <Route path="me" element={<MeScreen />} />
                <Route path="me/api" element={<ApiAccessScreen />} />
                <Route path="audit" element={<AuditScreen />} />
                <Route path="servers" element={<ServersScreen />} />
                {/* A server's sections (servers/sections.ts): each is a child route here. */}
                <Route path="servers/:guildId" element={<ServerScreen />}>
                  <Route index element={<Navigate to="settings" replace />} />
                  <Route path="settings" element={<SettingsSection />} />
                </Route>
                <Route path="purgeme" element={<PurgeScreen />} />
                <Route path="presets" element={<NamespacesScreen />} />
                <Route path="presets/me" element={<MyPresetsScreen />} />
                <Route path="presets/manage/:namespace" element={<NamespaceScreen />} />
                <Route path="presets/manage/:namespace/:randomizer" element={<NamespaceScreen />} />
                <Route path="presets/manage/:namespace/:randomizer/:preset" element={<PresetScreen />} />
                <Route path="presets/:namespace/create" element={<NewPresetScreen />} />
                <Route path="ranked_choice/:electionId" element={<BallotScreen />} />
                <Route path="elections" element={<ElectionsScreen />} />
                <Route path="elections/new" element={<ElectionFormScreen />} />
                <Route path="elections/:electionId/edit" element={<ElectionFormScreen />} />
                <Route path="elections/:electionId/results" element={<ResultsScreen />} />
                <Route path="triforcetexts/:pool" element={<TriforcePoolScreen />} />
                <Route path="triforcetexts/:pool/moderation" element={<ModerationScreen />} />
                <Route path="submit/:event" element={<SubmissionScreen />} />
                <Route path="servers/:guildId/voice-roles" element={<VoiceRolesSection />} />
                <Route path="error" element={<ErrorScreen />} />
                <Route path="logout" element={<Navigate to="/" replace />} />
                <Route path="presets/:namespace" element={<LegacyNamespaceRedirect />} />
                <Route path="*" element={<NotFoundScreen />} />
              </Route>
            </SentryRoutes>
          </BrowserRouter>
        </SessionProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}

function LegacyNamespaceRedirect() {
  const { namespace = '' } = useParams()
  return <Navigate to={`/presets/manage/${encodeURIComponent(namespace)}`} replace />
}
