import { useId } from 'react'
import type { Branch, Rollable, RollChoices } from './rolling'

function Toggle({ title, desc, checked, onChange }: Readonly<{ title: string; desc: string; checked: boolean; onChange: (on: boolean) => void }>) {
  const id = useId()
  return (
    <div className="seed-opt">
      <label className="seed-opt__text" htmlFor={id}>
        <b>{title}</b>
        <span>{desc}</span>
      </label>
      <input
        id={id}
        type="checkbox"
        role="switch"
        className="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </div>
  )
}

/** The options the Discord commands take, shown only where they apply to `randomizer`. */
export function RollOptions({
  randomizer,
  value,
  onChange,
}: Readonly<{ randomizer: Rollable; value: RollChoices; onChange: (next: RollChoices) => void }>) {
  const set = (patch: Partial<RollChoices>) => onChange({ ...value, ...patch })
  const alttpr = randomizer === 'alttpr'
  const siteId = useId()
  return (
    <div className="seed-opts">
      <Toggle
        title="Race seed"
        desc={randomizer === 'alttprmystery' ? 'No spoiler log.' : 'No spoiler log, and tournament settings.'}
        checked={value.race}
        onChange={(race) => set({ race })}
      />
      {alttpr && <Toggle title="Hints" desc="Telepathic tiles and stones give hints." checked={value.hints} onChange={(hints) => set({ hints })} />}
      {(alttpr || randomizer === 'alttprmystery') && (
        <Toggle
          title="Allow quickswap"
          desc="Swap items with L and R."
          checked={value.allowQuickswap}
          onChange={(allowQuickswap) => set({ allowQuickswap })}
        />
      )}
      {randomizer === 'smz3' && (
        <Toggle title="Spoiler race" desc="Make a spoiler log to share." checked={value.spoilerRace} onChange={(spoilerRace) => set({ spoilerRace })} />
      )}
      {alttpr && (
        <div className="seed-opt">
          <label className="seed-opt__text" htmlFor={siteId}>
            <b>Site</b>
            <span>Which alttpr.com rolls it.</span>
          </label>
          <select id={siteId} className="input seed-opt__select" value={value.branch} onChange={(e) => set({ branch: e.target.value as Branch })}>
            <option value="live">Live</option>
            <option value="beeta">Beeta</option>
            <option value="tournament">Tournament</option>
          </select>
        </div>
      )}
    </div>
  )
}
