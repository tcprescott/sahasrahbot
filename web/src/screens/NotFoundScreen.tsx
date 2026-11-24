import { Link } from 'react-router-dom'
import { EmptyState } from '../components'

export function NotFoundScreen() {
  return (
    <EmptyState icon="search" title="There's nothing here">
      That link may be old, or mistyped. <Link to="/">Go to the home page</Link>.
    </EmptyState>
  )
}
