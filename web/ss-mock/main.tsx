import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import '../src/styles/tokens.css'
import '../src/styles/base.css'
import '../src/kit/forms.css'
import '../src/styles/app.css'
import '../src/shell/shell.css'
import '../src/components/components.css'
import { Button, Chip, FormDialog, Icon, PageHeader, Panel, RowMenu, TooltipProvider, type IconName } from '../src/components'
import './mock.css'
import './ss-mock.css'

const params = new URLSearchParams(location.search)
const screen = params.get('s') ?? 'server'
const variant = params.get('v') ?? 'A'

const TABS: { label: string; icon: IconName }[] = [
  { label: 'Home', icon: 'home' },
  { label: 'Presets', icon: 'folder' },
  { label: 'Elections', icon: 'how_to_vote' },
  { label: 'Servers', icon: 'forum' },
  { label: 'Me', icon: 'person' },
]

function Shell({ title, children, label = true }: Readonly<{ title: string; children: ReactNode; label?: boolean }>) {
  const nav = (kind: 'rail' | 'tabbar') => (
    <ul className={`nav nav--${kind}`}>
      {TABS.map((t) => (
        <li key={t.label}>
          <a href="#" className={t.label === 'Servers' ? 'nav__link active' : 'nav__link'}>
            <span className="nav__icon"><Icon name={t.icon} /></span>
            <span className="nav__label">{t.label}</span>
          </a>
        </li>
      ))}
    </ul>
  )
  return (
    <div className="shell">
      <nav className="shell__rail">
        <a className="brand" href="#">
          <img className="brand__mark" src="/sahasrahbot.png" alt="" />
          <span className="brand__name">SahasrahBot</span>
        </a>
        {nav('rail')}
      </nav>
      <div className="shell__main">
        <header className="topbar">
          <span className="topbar__title"><span className="topbar__page">{title}</span></span>
          <div className="topbar__actions"><span className="user-pill"><span className="avatar">TP</span></span></div>
        </header>
        <main className="shell__content">{children}</main>
      </div>
      <nav className="shell__tabbar">{nav('tabbar')}</nav>
      {label && <span className="mk-label">Option {variant}</span>}
    </div>
  )
}

const SERVERS = [
  { name: 'ALTTPR Racing', initials: 'AR', members: 'Admin' },
  { name: 'SMZ3 Community', initials: 'SC', members: 'Admin' },
  { name: 'Prod-like Community 3', initials: 'P3', members: 'Manage Server' },
]

const SECTIONS: { key: string; label: string; icon: IconName; sub: string; soon?: boolean }[] = [
  { key: 'settings', label: 'Settings', icon: 'key', sub: 'Daily posts, holy images, inquiries' },
  { key: 'role-menus', label: 'Role menus', icon: 'person', sub: '3 menus' },
  { key: 'voice-roles', label: 'Voice roles', icon: 'forum', sub: '2 voice channels' },
  { key: 'verification', label: 'Racer verification', icon: 'check_circle', sub: 'Off' },
  { key: 'directory', label: 'Server directory', icon: 'menu_book', sub: 'Listed in 2 groups' },
]

function Picker() {
  return (
    <Shell title="Servers" label={false}>
      <PageHeader title="Servers" lede="The Discord servers you administer that SahasrahBot is in. Pick one to change how the bot behaves there." />
      <div className="ss-servers">
        {SERVERS.map((s) => (
          <Panel key={s.name}>
            <a href="#" className="ss-server">
              <span className="ss-server__icon">{s.initials}</span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span className="ss-server__name">{s.name}</span>
                <span className="mk-sub">You have {s.members}</span>
              </span>
              <Icon name="chevron_right" />
            </a>
          </Panel>
        ))}
      </div>
    </Shell>
  )
}

function ServerHead() {
  return (
    <>
      <div className="ss-crumb"><a href="#">Servers</a><Icon name="chevron_right" size={16} /></div>
      <div className="ss-head">
        <span className="ss-server__icon">AR</span>
        <h1>ALTTPR Racing</h1>
        <select className="input" defaultValue="ALTTPR Racing" aria-label="Switch server">
          {SERVERS.map((s) => <option key={s.name}>{s.name}</option>)}
        </select>
      </div>
    </>
  )
}

function Chips({ items }: Readonly<{ items: { name: string; warn?: boolean }[] }>) {
  return (
    <div className="ss-chips">
      {items.map((c) => (
        <span key={c.name} className={c.warn ? 'ss-chip ss-chip--warn' : 'ss-chip'}>
          {c.warn && <Icon name="warning" size={16} />}#{c.name}<Icon name="close" size={16} />
        </span>
      ))}
      <span className="ss-chips__add">Add a channel…</span>
    </div>
  )
}

function SettingsBody() {
  return (
    <div className="ss-stack">
      <Panel title="Daily challenge">
        <div className="ss-pad">
          <div className="field">
            <span className="field__label">Announce the ALTTPR daily challenge in</span>
            <Chips items={[{ name: 'daily-challenge' }, { name: 'old-dailies', warn: true }]} />
            <span className="field__hint">Each new daily seed is posted here with a thread for discussion. Leave empty to turn it off.</span>
          </div>
          <span className="mk-sub" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <Icon name="warning" size={16} /> #old-dailies no longer exists or the bot can't post there, so nothing is posted in it.
          </span>
        </div>
      </Panel>
      <Panel title="Holy images">
        <div className="ss-pad">
          <div className="field">
            <label className="field__label" htmlFor="holy">Default game for /holyimage</label>
            <select id="holy" className="input" defaultValue="smz3" style={{ maxWidth: 320 }}>
              <option value="z3r">z3r: A Link to the Past Randomizer</option>
              <option value="smz3">smz3: SMZ3</option>
              <option value="sm">sm: Super Metroid Randomizer</option>
            </select>
            <span className="field__hint">Used when someone runs /holyimage here without picking a game. Today: z3r.</span>
          </div>
        </div>
      </Panel>
      <div className="ss-savebar"><span>Unsaved changes</span><Button variant="outline">Discard</Button><Button>Save settings</Button></div>
      <Panel title="Inquiry buttons" actions={<Button variant="outline" icon="add">Post an inquiry button</Button>}>
        <div>
          {[
            ['#modmail', '@Moderators', 'Posted 3 Feb 2025'],
            ['#tournament-help', '@Tournament Admins', 'Posted 12 Oct 2025'],
          ].map(([ch, role, when]) => (
            <div key={ch} className="ss-row">
              <Icon name="forum" />
              <span className="ss-row__text">
                <b>{ch}</b>
                <span className="mk-sub">Opens a private thread with {role} · {when}</span>
              </span>
              <RowMenu label={`More for ${ch}`} items={[
                { label: 'Jump to the message', icon: 'open_in_new', onSelect: () => undefined },
                { label: 'Change role', icon: 'edit', onSelect: () => undefined },
                { label: 'Remove', icon: 'delete', destructive: true, onSelect: () => undefined },
              ]} />
            </div>
          ))}
        </div>
      </Panel>
    </div>
  )
}

function ServerA() {
  return (
    <Shell title="Servers">
      <ServerHead />
      <nav className="detail-tabs" style={{ marginBottom: 'var(--space-3)' }}>
        {SECTIONS.map((s) => <a key={s.key} href="#" className={s.key === 'settings' ? 'active' : ''}>{s.label}</a>)}
      </nav>
      <SettingsBody />
    </Shell>
  )
}

function SideList() {
  return (
    <ul className="ss-side">
      {SECTIONS.map((s) => (
        <li key={s.key}>
          <a href="#" className={s.key === 'settings' ? 'active' : ''}>
            <Icon name={s.icon} />
            <span>{s.label}</span>
          </a>
        </li>
      ))}
    </ul>
  )
}

function ServerB() {
  return (
    <Shell title="Servers">
      <div className="ss-desk-only"><ServerHead /></div>
      <div className="ss-phone-only">
        <div className="ss-crumb"><a href="#">ALTTPR Racing</a><Icon name="chevron_right" size={16} /></div>
        <h1 style={{ margin: '0 0 var(--space-3)', fontSize: '1.375rem' }}>Settings</h1>
      </div>
      <div className="ss-split">
        <div className="ss-sidecol"><Panel><SideList /></Panel></div>
        <SettingsBody />
      </div>
    </Shell>
  )
}

function SectionsB() {
  return (
    <Shell title="Servers">
      <ServerHead />
      <Panel>
        <div>
          {SECTIONS.map((s) => (
            <a key={s.key} href="#" className="ss-row" style={{ color: 'inherit', textDecoration: 'none' }}>
              <Icon name={s.icon} />
              <span className="ss-row__text"><b>{s.label}</b><span className="mk-sub">{s.sub}</span></span>
              <Icon name="chevron_right" />
            </a>
          ))}
        </div>
      </Panel>
    </Shell>
  )
}

function InquiryFields({ checks }: Readonly<{ checks: boolean }>) {
  return (
    <div className="stack" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="field">
        <label className="field__label" htmlFor="ch">Channel</label>
        <select id="ch" className="input" defaultValue="modmail"><option>#modmail</option></select>
        <span className="field__hint">Where the button is posted. Members should be able to see it but not send messages there.</span>
      </div>
      <div className="field">
        <label className="field__label" htmlFor="rl">Who answers</label>
        <select id="rl" className="input" defaultValue="mods"><option value="mods">@Moderators</option></select>
        <span className="field__hint">Pressing the button opens a private thread with the member and this role.</span>
      </div>
      {checks && (
        <ul className="ss-checks" aria-label="Channel checks">
          <li><span className="ok"><Icon name="check_circle" size={18} /></span>SahasrahBot can create private threads in #modmail</li>
          <li><span className="ok"><Icon name="check_circle" size={18} /></span>@Moderators can see #modmail</li>
          <li><span className="bad"><Icon name="error" size={18} /></span>@everyone can send messages in #modmail. Turn that off, or people will post there instead.</li>
        </ul>
      )}
    </div>
  )
}

function InquiryPreview() {
  return (
    <div className="dc">
      <div className="dc__msg">
        <span className="dc__av" />
        <div className="dc__body">
          <div><span className="dc__name">SahasrahBot</span><span className="dc__app">APP</span></div>
          <div style={{ marginTop: 4, lineHeight: 1.4 }}>
            To <b>submit an inquiry</b>, click the 📬 button below, then click "Yes!" in the next message to confirm.<br /><br />
            This will open an inquiry visible to members of <span style={{ color: '#c9cdfb', background: 'rgba(88,101,242,.3)', borderRadius: 3, padding: '0 2px' }}>@Moderators</span><br /><br />Thanks!
          </div>
          <div className="dc__btns"><span className="dc__btn dc__btn--blurple">📬 Open New Inquiry</span></div>
        </div>
      </div>
    </div>
  )
}

function InquiryA() {
  return (
    <Shell title="Servers">
      <ServerHead />
      <SettingsBody />
      <FormDialog open onOpenChange={() => undefined} title="Post an inquiry button" primaryLabel="Post in #modmail"
        description="Members press it to open a private thread with a role, for questions they'd rather not ask in public.">
        <InquiryFields checks />
      </FormDialog>
    </Shell>
  )
}

function InquiryB() {
  return (
    <Shell title="Servers">
      <ServerHead />
      <SettingsBody />
      <FormDialog open size="lg" onOpenChange={() => undefined} title="Post an inquiry button" primaryLabel="Post in #modmail"
        description="Members press it to open a private thread with a role, for questions they'd rather not ask in public.">
        <div className="ss-inq-b">
          <InquiryFields checks />
          <div className="field"><span className="field__label">What members will see</span><InquiryPreview /></div>
        </div>
      </FormDialog>
    </Shell>
  )
}

const SCREENS: Record<string, () => ReactNode> = {
  inquiry: variant === 'B' ? InquiryB : InquiryA,
  picker: Picker,
  server: variant === 'B' ? ServerB : ServerA,
  sections: SectionsB,
}
const Screen = SCREENS[screen]
createRoot(document.getElementById('root')!).render(
  <StrictMode><TooltipProvider><Screen /></TooltipProvider></StrictMode>,
)
