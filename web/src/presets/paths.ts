const enc = encodeURIComponent

export const namespacePath = (ns: string, randomizer?: string) => {
  const base = `/presets/manage/${enc(ns)}`
  return randomizer ? `${base}/${enc(randomizer)}` : base
}

export const presetPath = (ns: string, randomizer: string, name: string) =>
  `/presets/manage/${enc(ns)}/${enc(randomizer)}/${enc(name)}`

export const downloadPath = (ns: string, randomizer: string, name: string) =>
  `/presets/download/${enc(ns)}/${enc(randomizer)}/${enc(name)}`

/** The API's path parameters for one preset. */
export const presetParams = (ns: string, randomizer: string, name: string) => ({
  params: { path: { namespace: ns, randomizer, preset: name } },
})
