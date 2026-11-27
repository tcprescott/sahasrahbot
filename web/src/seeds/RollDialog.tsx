import { useState } from 'react'
import { Banner, Button, Dialog } from '../components'
import { RollOptions } from './RollOptions'
import { DEFAULT_CHOICES, rollSeed, type Rollable, type RollChoices, type Seed } from './rolling'
import { SeedCard } from './SeedCard'

/** The preset page's "Roll a seed": options first, then the seed in the same dialog. */
export function RollDialog({
  open,
  onOpenChange,
  randomizer,
  preset,
  onRolled,
}: Readonly<{ open: boolean; onOpenChange: (open: boolean) => void; randomizer: Rollable; preset: string; onRolled?: () => void }>) {
  const [choices, setChoices] = useState<RollChoices>(DEFAULT_CHOICES)
  const [seed, setSeed] = useState<Seed | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  const close = (next: boolean) => {
    if (!next) {
      setSeed(null)
      setError(undefined)
    }
    onOpenChange(next)
  }

  const roll = async () => {
    setBusy(true)
    setError(undefined)
    try {
      setSeed(await rollSeed(randomizer, preset, choices))
      onRolled?.()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={close}
      title={seed ? 'Your seed' : `Roll ${preset}`}
      size="md"
      footer={
        seed ? (
          <>
            <span className="dialog__spacer" />
            <Button variant="ghost" onClick={() => setSeed(null)}>
              Roll another
            </Button>
            <Button onClick={() => close(false)}>Done</Button>
          </>
        ) : (
          <>
            <span className="dialog__spacer" />
            <Button variant="ghost" onClick={() => close(false)}>
              Cancel
            </Button>
            <Button onClick={() => void roll()} busy={busy} busyLabel="Rolling">
              Roll
            </Button>
          </>
        )
      }
    >
      {error && <Banner tone="error">{error}</Banner>}
      {seed ? <SeedCard seed={seed} /> : <RollOptions randomizer={randomizer} value={choices} onChange={setChoices} />}
      {busy && <p className="seed-hint">Rolling takes a few seconds.</p>}
    </Dialog>
  )
}
