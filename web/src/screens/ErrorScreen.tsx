import { Link, useSearchParams } from 'react-router-dom'
import { Banner, Button, PageHeader } from '../components'
import { loginUrl } from '../api/client'

const TITLES: Record<string, string> = {
  '400': "That didn't work",
  '403': "You can't do that",
  '404': 'Not found',
  '500': 'Something went wrong',
}

/** Where the server sends sign-in and racetime-linking failures (/error?code=…&message=…). */
export function ErrorScreen() {
  const [params] = useSearchParams()
  const code = params.get('code') ?? '500'
  const message = params.get('message') ?? 'Something went wrong on our side. Try again later.'
  return (
    <>
      <PageHeader title={TITLES[code] ?? 'Something went wrong'} />
      <Banner tone="error">{message}</Banner>
      <div className="t-actions">
        <Button asChild variant="outline">
          <Link to="/">Home</Link>
        </Button>
        <Button asChild>
          <a href={loginUrl('/me')}>Sign in again</a>
        </Button>
      </div>
    </>
  )
}
