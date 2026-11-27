import type { RoleMenuStyle } from '../api/client'

const CUSTOM = /^<(a?):([A-Za-z0-9_~]+):(\d+)>$/

/** An emoji as Discord draws it: Unicode as text, a custom one (`<:name:id>`) as its image. */
export function Emoji({ text, size = 20 }: Readonly<{ text?: string | null; size?: number }>) {
  if (!text) return null
  const custom = CUSTOM.exec(text)
  if (!custom) {
    return (
      <span className="rm-emoji" style={{ fontSize: size }}>
        {text}
      </span>
    )
  }
  const [, animated, name, id] = custom
  return (
    <img
      className="rm-emoji rm-emoji--custom"
      src={`https://cdn.discordapp.com/emojis/${id}.${animated ? 'gif' : 'webp'}?size=48`}
      alt={`:${name}:`}
      width={size}
      height={size}
    />
  )
}

export interface PreviewOption {
  key: string | number
  label: string
  emoji?: string | null
  description?: string | null
}

export interface PreviewMenu {
  title: string
  description: string
  style: RoleMenuStyle
  singleChoice: boolean
  options: PreviewOption[]
}

/** What the menu will look like in Discord (its dark theme), as it's edited. */
export function DiscordPreview({ menu }: Readonly<{ menu: PreviewMenu }>) {
  const { style, options } = menu
  return (
    <figure className="dc" aria-label="Preview in Discord">
      <div className="dc__msg">
        <img className="dc__av" src="/sahasrahbot.png" alt="" />
        <div className="dc__body">
          <div>
            <span className="dc__name">SahasrahBot</span>
            <span className="dc__app">APP</span>
          </div>
          <div className="dc__embed">
            <div className="dc__title">{menu.title.trim() || 'Untitled menu'}</div>
            {menu.description.trim() && <div className="dc__desc">{menu.description}</div>}
            {style === 'reactions' && options.length > 0 && (
              <div className="dc__list">
                <div className="dc__field">{menu.singleChoice ? 'React to pick one role' : 'React to pick a role'}</div>
                {options.map((o) => (
                  <div key={o.key}>
                    <Emoji text={o.emoji} size={18} /> <b>{o.label || 'Unnamed role'}</b>
                    {o.description && ` – ${o.description}`}
                  </div>
                ))}
              </div>
            )}
            {style !== 'reactions' && menu.singleChoice && (
              <div className="dc__foot">You can have one of these roles at a time.</div>
            )}
          </div>
          {style === 'reactions' && (
            <div className="dc__row">
              {options.filter((o) => o.emoji).map((o) => (
                <span key={o.key} className="dc__react">
                  <Emoji text={o.emoji} size={16} /> 1
                </span>
              ))}
            </div>
          )}
          {style === 'buttons' && (
            <div className="dc__row">
              {options.map((o) => (
                <span key={o.key} className="dc__btn">
                  <Emoji text={o.emoji} size={18} /> {o.label || 'Unnamed role'}
                </span>
              ))}
            </div>
          )}
          {style === 'dropdown' && (
            <div className="dc__select">
              <span>{menu.singleChoice ? 'Pick a role to add or remove' : 'Pick roles to add or remove'}</span>
              <span aria-hidden="true">⌄</span>
            </div>
          )}
        </div>
      </div>
    </figure>
  )
}
