import * as RT from '@radix-ui/react-tooltip'
import type { ReactNode } from 'react'

export const TooltipProvider = RT.Provider

export function Tooltip({ content, children }: { content: string; children: ReactNode }) {
  return (
    <RT.Root delayDuration={400}>
      <RT.Trigger asChild>{children}</RT.Trigger>
      <RT.Portal>
        <RT.Content className="tooltip" sideOffset={6}>
          {content}
        </RT.Content>
      </RT.Portal>
    </RT.Root>
  )
}
