import type { ReactNode } from 'react'
import { Banner, Button, EmptyState, Spinner } from '../components'
import { ApiError } from './client'
import type { QueryState } from './useQuery'

/**
 * The three states of a screen's data: a labelled spinner while it loads, an
 * error banner with Try again when it fails (a 404 reads as "not found"), and
 * the screen once it's there.
 */
export function Loaded<T>({
  query,
  label,
  notFound = "This page doesn't exist, or it's gone.",
  children,
}: Readonly<{
  query: QueryState<T>
  label: string
  notFound?: string
  children: (data: T) => ReactNode
}>) {
  if (query.data !== undefined) return <>{children(query.data)}</>
  if (query.error) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return <EmptyState icon="search" title="Not found">{query.error.message || notFound}</EmptyState>
    }
    if (query.error instanceof ApiError && query.error.status === 403) {
      return <EmptyState icon="cancel" title="You can't open this">{query.error.message}</EmptyState>
    }
    return (
      <Banner tone="error" action={<Button variant="outline" size="sm" onClick={query.reload}>Try again</Button>}>
        {query.error.message}
      </Banner>
    )
  }
  return <Spinner label={label} />
}
