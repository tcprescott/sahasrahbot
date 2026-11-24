import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Button, Icon, PageHeader, type IconName } from '../components'
import { useSession } from '../auth/SessionProvider'
import { DOCS_URL } from '../shell/tabs'

const INVITE_URL =
  'https://discord.com/api/oauth2/authorize?client_id=572269659290861578&permissions=0&scope=bot%20applications.commands'
const GITHUB_URL = 'https://github.com/tcprescott/sahasrahbot'

function Tile({ icon, title, children, actions }: { icon: IconName; title: string; children: ReactNode; actions: ReactNode }) {
  return (
    <section className="tile">
      <h2>
        <Icon name={icon} />
        {title}
      </h2>
      <p>{children}</p>
      <div className="t-actions">{actions}</div>
    </section>
  )
}

export function HomeScreen() {
  const { user } = useSession()
  return (
    <>
      <PageHeader
        title={user ? `Hi, ${user.name}` : 'SahasrahBot'}
        lede="Seeds, races and tournaments for A Link to the Past Randomizer, Super Metroid, SMZ3 and friends, on Discord and racetime.gg."
      />
      <div className="tile-grid">
        <Tile
          icon="folder"
          title="Presets"
          actions={
            <>
              <Button asChild>
                <Link to="/presets/me">My presets</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/presets">Browse</Link>
              </Button>
            </>
          }
        >
          Upload your own randomizer settings and roll them in Discord as <span className="code">namespace/preset</span>.
        </Tile>
        <Tile
          icon="link"
          title="racetime.gg account"
          actions={
            <Button asChild variant="outline">
              <a href="/racetime/verification/initiate">Link racetime.gg</a>
            </Button>
          }
        >
          Tell SahasrahBot which racetime.gg account is yours, so tournament races can invite you to their rooms.
        </Tile>
        <Tile
          icon="add"
          title="Add SahasrahBot to your server"
          actions={
            <Button asChild variant="outline">
              <a href={INVITE_URL} target="_blank" rel="noreferrer">
                Invite to Discord
              </a>
            </Button>
          }
        >
          Roll seeds with slash commands, run daily races, and open race rooms for your tournament automatically.
        </Tile>
        <Tile
          icon="menu_book"
          title="Commands and presets"
          actions={
            <>
              <Button asChild variant="outline">
                <a href={DOCS_URL} target="_blank" rel="noreferrer">
                  Read the docs
                </a>
              </Button>
              <Button asChild variant="ghost">
                <a href={GITHUB_URL} target="_blank" rel="noreferrer">
                  GitHub
                </a>
              </Button>
            </>
          }
        >
          Every command, the built-in presets, and how to use SahasrahBot for a racetime.gg tournament.
        </Tile>
      </div>
    </>
  )
}
