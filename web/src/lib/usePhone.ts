import { useEffect, useState } from 'react'

/** Whether the layout is the phone one (below 768px), tracking resizes. */
export function usePhone(): boolean {
  const query = '(max-width: 767.98px)'
  const [phone, setPhone] = useState(() => typeof matchMedia === 'function' && matchMedia(query).matches)
  useEffect(() => {
    if (typeof matchMedia !== 'function') return
    const media = matchMedia(query)
    const on = () => setPhone(media.matches)
    media.addEventListener('change', on)
    return () => media.removeEventListener('change', on)
  }, [])
  return phone
}
