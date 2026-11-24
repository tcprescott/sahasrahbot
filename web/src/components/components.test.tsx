import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { readStored, writeStored } from '../lib/storage'
import { CountBadge, FormDialog } from '.'

describe('CountBadge', () => {
  it('shows nothing for zero and caps at 99+', () => {
    const { container, rerender } = render(<CountBadge count={0} label="0 waiting" />)
    expect(container.textContent).toBe('')
    rerender(<CountBadge count={150} label="150 waiting" />)
    expect(screen.getByLabelText('150 waiting').textContent).toBe('99+')
  })
})

describe('FormDialog', () => {
  const dialog = (onOpenChange = vi.fn()) =>
    render(
      <FormDialog open onOpenChange={onOpenChange} title="Edit" primaryLabel="Save" onPrimary={() => {}} extra={[{ label: 'Reset', onSelect: () => {} }]}>
        body
      </FormDialog>,
    )

  it('closes on Cancel', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    dialog(onOpenChange)
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('test_known_issue: the extra actions ⋮ never opens', async () => {
    // The ⋮ is a non-modal Radix menu inside a modal Radix dialog. Pressing it (or
    // Enter on it) leaves it closed; checked in Chromium too, not just jsdom. No
    // screen passes `extra` yet, so nobody hits it today. Fixing it means changing this test.
    const user = userEvent.setup()
    dialog()
    const more = screen.getByRole('button', { name: 'More options' })
    await user.click(more)
    more.focus()
    await user.keyboard('{Enter}')
    expect(more.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('menuitem', { name: 'Reset' })).toBeNull()
  })
})

describe('storage', () => {
  it('survives storage that throws, as in private mode', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError')
    })
    expect(readStored('k')).toBeNull()
    expect(() => writeStored('k', 'v')).not.toThrow()
  })

  it('uses session storage when asked', () => {
    writeStored('k', 'v', 'session')
    expect(readStored('k', 'session')).toBe('v')
    expect(readStored('k')).toBeNull()
    writeStored('k', null, 'session')
    expect(readStored('k', 'session')).toBeNull()
  })
})
