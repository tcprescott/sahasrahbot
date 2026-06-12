import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '../../components/ui/Badge';
import '../../styles/presets.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Shape returned by GET /presets/api/<randomizer>/list */
interface PresetsListResponse {
  global: string[];
  namespaces: Array<{ name: string; presets: string[] }>;
}

/** Shape returned by GET /presets/api/<randomizer>?preset=<name> */
interface PresetDetailResponse {
  preset: string;
  randomizer: string;
  data: Record<string, unknown> | string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RANDOMIZERS = [
  { id: 'alttpr',         label: 'ALTTPR'  },
  { id: 'smz3',           label: 'SMZ3'    },
  { id: 'sm',             label: 'SM'      },
  { id: 'alttprmystery',  label: 'Mystery' },
  { id: 'ctjets',         label: 'CT Jets' },
] as const;

type RandomizerId = typeof RANDOMIZERS[number]['id'];

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchPresetList(randomizer: RandomizerId): Promise<PresetsListResponse> {
  const r = await fetch(`/presets/api/${randomizer}/list`);
  if (!r.ok) throw new Error(`Failed to load presets (${r.status})`);
  return r.json() as Promise<PresetsListResponse>;
}

async function fetchPresetDetail(
  randomizer: RandomizerId,
  preset: string,
): Promise<PresetDetailResponse> {
  const r = await fetch(`/presets/api/${randomizer}?preset=${encodeURIComponent(preset)}`);
  if (!r.ok) throw new Error(`Failed to load preset detail (${r.status})`);
  return r.json() as Promise<PresetDetailResponse>;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SkeletonBlock({ w = '100%', h = '1rem' }: { w?: string; h?: string }) {
  return <div className="skel" style={{ width: w, height: h }} />;
}

/** Lightweight YAML-like renderer from a nested object or raw YAML string */
function YamlPreview({ data }: { data: Record<string, unknown> | string }) {
  function renderLines(obj: Record<string, unknown>, indent = 0): string[] {
    const pad = '  '.repeat(indent);
    const lines: string[] = [];
    for (const [k, v] of Object.entries(obj)) {
      if (v === null || v === undefined) {
        lines.push(`${pad}${k}: ~`);
      } else if (typeof v === 'object' && !Array.isArray(v)) {
        lines.push(`${pad}${k}:`);
        lines.push(...renderLines(v as Record<string, unknown>, indent + 1));
      } else if (Array.isArray(v)) {
        lines.push(`${pad}${k}:`);
        for (const item of v as unknown[]) {
          lines.push(`${pad}  - ${String(item)}`);
        }
      } else {
        lines.push(`${pad}${k}: ${String(v)}`);
      }
    }
    return lines;
  }

  const lines = typeof data === 'string'
    ? data.split('\n').filter((l) => !l.startsWith('---'))
    : renderLines(data);

  return (
    <div className="codeblock">
      <pre><code>
        {lines.map((line, i) => {
          const m = line.match(/^(\s*)([^:]+):(.*)/);
          if (!m) return <span key={i}>{line}{'\n'}</span>;
          const [, spaces, key, rest] = m;
          return (
            <span key={i}>
              {spaces}<span className="k">{key}</span>:{rest ? <span className="v">{rest}</span> : ''}
              {'\n'}
            </span>
          );
        })}
      </code></pre>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Selected preset detail panel
// ---------------------------------------------------------------------------

interface DetailPanelProps {
  randomizer: RandomizerId;
  presetName: string;
  namespace: string | null;
}

function PresetDetailPanel({ randomizer, presetName, namespace }: DetailPanelProps) {
  const qualifiedName = namespace ? `${namespace}/${presetName}` : presetName;

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['preset-detail', randomizer, qualifiedName],
    queryFn: () => fetchPresetDetail(randomizer, qualifiedName),
    staleTime: 60_000,
  });

  const downloadHref = namespace
    ? `/presets/download/${namespace}/${randomizer}/${presetName}`
    : null;

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <div className="yaml-name">{presetName}</div>
          <div className="rand-tag" style={{ marginTop: '.2rem' }}>{randomizer}</div>
        </div>
        <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
          {downloadHref && (
            <a
              className="btn btn-ghost btn-sm"
              href={downloadHref}
              download={`${qualifiedName}.yaml`}
            >
              ⬇ Download
            </a>
          )}
          {namespace && (
            <a
              className="btn btn-ghost btn-sm"
              href={`/presets/manage/${namespace}/${randomizer}/${presetName}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              View ↗
            </a>
          )}
        </div>
      </div>
      <div className="panel-body">
        {isLoading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.7rem' }}>
            {[75, 55, 85, 60, 70, 50].map((pct, i) => (
              <SkeletonBlock key={i} w={`${pct}%`} h=".85rem" />
            ))}
          </div>
        )}
        {isError && (
          <div className="state-box">
            <div className="state-icon">⚠</div>
            <p>{error instanceof Error ? error.message : 'Failed to load preset.'}</p>
          </div>
        )}
        {!isLoading && data && (typeof data.data === 'string' ? data.data.trim().length > 0 : Object.keys(data.data ?? {}).length > 0) && (
          <YamlPreview data={data.data} />
        )}
        {!isLoading && data && (typeof data.data === 'string' ? data.data.trim().length === 0 : Object.keys(data.data ?? {}).length === 0) && (
          <div className="state-box">
            <div className="state-icon">◇</div>
            <p>No detail available for this preset.</p>
          </div>
        )}
        <p style={{ marginTop: '1rem', color: 'var(--ink-faint)', fontSize: '.82rem' }}>
          Use{' '}
          <code style={{ fontFamily: "'Space Mono', monospace", color: 'var(--teal)' }}>
            /{randomizer} preset:{qualifiedName}
          </code>{' '}
          in Discord to roll this preset.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

/** A single row in the preset list: either a global preset or a namespace+preset pair. */
interface PresetRow {
  namespace: string | null;
  presetName: string;
}

export function PresetsListPage() {
  const [randomizer, setRandomizer] = useState<RandomizerId>('alttpr');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<PresetRow | null>(null);
  const [activeNs, setActiveNs] = useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['presets-list', randomizer],
    queryFn: () => fetchPresetList(randomizer),
    staleTime: 60_000,
  });

  function switchRandomizer(r: RandomizerId) {
    setRandomizer(r);
    setSelected(null);
    setActiveNs(null);
    setSearch('');
  }

  const totalCount = useMemo(() => {
    if (!data) return 0;
    return (
      data.global.length +
      data.namespaces.reduce((acc, ns) => acc + ns.presets.length, 0)
    );
  }, [data]);

  const visibleRows = useMemo<PresetRow[]>(() => {
    if (!data) return [];
    const q = search.toLowerCase().trim();
    let rows: PresetRow[] = [];

    if (activeNs === null || activeNs === '__global__') {
      rows = [...rows, ...data.global.map((p) => ({ namespace: null, presetName: p }))];
    }

    if (activeNs !== '__global__') {
      const nsList =
        activeNs !== null
          ? data.namespaces.filter((ns) => ns.name === activeNs)
          : data.namespaces;
      for (const ns of nsList) {
        for (const p of ns.presets) {
          rows.push({ namespace: ns.name, presetName: p });
        }
      }
    }

    if (q) {
      rows = rows.filter(
        (r) =>
          r.presetName.toLowerCase().includes(q) ||
          (r.namespace?.toLowerCase().includes(q) ?? false),
      );
    }

    return rows;
  }, [data, activeNs, search]);

  const nsCards = data?.namespaces ?? [];

  function handleNsClick(nsName: string) {
    setActiveNs((prev) => (prev === nsName ? null : nsName));
    setSelected(null);
  }

  function isRowSelected(row: PresetRow) {
    return (
      selected !== null &&
      selected.namespace === row.namespace &&
      selected.presetName === row.presetName
    );
  }

  return (
    <>
      {/* ======== PAGE HEAD ======== */}
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <span>Presets</span>
          </nav>
          <h1 className="ph-title reveal d2">
            Preset Library{' '}
            {!isLoading && data && (
              <span style={{ verticalAlign: 'middle', fontSize: '.55em' }}>
                <Badge tone="gold">{totalCount}</Badge>
              </span>
            )}
          </h1>
          <p className="ph-sub reveal d3">
            Browse community preset namespaces and inspect their YAML, or sign in to manage your own.
          </p>
        </div>
      </section>

      {/* ======== BODY ======== */}
      <section className="block">
        <div className="wrap">

          {/* Randomizer filter tabs */}
          <div className="rand-tabs" role="tablist" aria-label="Randomizer filter">
            {RANDOMIZERS.map((r) => (
              <button
                key={r.id}
                role="tab"
                aria-selected={randomizer === r.id}
                className={`rand-tab${randomizer === r.id ? ' active' : ''}`}
                onClick={() => switchRandomizer(r.id)}
              >
                {r.label}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="search-row">
            <input
              type="search"
              className="search-input"
              placeholder="Search presets…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search presets"
            />
            {search && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setSearch('')}
              >
                ✕ Clear
              </button>
            )}
          </div>

          {/* Loading skeleton: namespace grid */}
          {isLoading && (
            <div className="ns-grid">
              {Array.from({ length: 6 }, (_, i) => (
                <div key={i} className="ns-card" style={{ pointerEvents: 'none' }}>
                  <div className="skel" style={{ width: 38, height: 38, borderRadius: 9, flexShrink: 0 }} />
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '.4rem' }}>
                    <SkeletonBlock w="70%" h=".8rem" />
                    <SkeletonBlock w="40%" h=".65rem" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Error state */}
          {!isLoading && isError && (
            <div className="panel" style={{ marginBottom: '2rem' }}>
              <div className="state-box">
                <div className="state-icon">⚠</div>
                <p>{error instanceof Error ? error.message : 'Failed to load presets.'}</p>
                <button className="btn btn-ghost btn-sm" onClick={() => void refetch()}>
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Loaded state */}
          {!isLoading && data && (
            <>
              {/* Namespace picker */}
              <div className="ns-grid onscroll">
                {/* Global pseudo-namespace */}
                {data.global.length > 0 && (
                  <button
                    className={`ns-card${activeNs === '__global__' ? ' active' : ''}`}
                    onClick={() => handleNsClick('__global__')}
                  >
                    <span className="ns-glyph">★</span>
                    <span>
                      <div className="ns-name">global</div>
                      <div className="ns-count">{data.global.length} preset{data.global.length !== 1 ? 's' : ''}</div>
                    </span>
                  </button>
                )}

                {nsCards.map((ns) => (
                  <button
                    key={ns.name}
                    className={`ns-card${activeNs === ns.name ? ' active' : ''}`}
                    onClick={() => handleNsClick(ns.name)}
                  >
                    <span className="ns-glyph">{ns.name[0].toUpperCase()}</span>
                    <span>
                      <div className="ns-name">{ns.name}</div>
                      <div className="ns-count">{ns.presets.length} preset{ns.presets.length !== 1 ? 's' : ''}</div>
                    </span>
                  </button>
                ))}
              </div>

              {/* Preset list + detail split */}
              <div className="presets-split onscroll">

                {/* Left: preset table */}
                <div className="panel">
                  <div className="panel-head">
                    <h3>
                      {activeNs === '__global__'
                        ? 'Global Presets'
                        : activeNs !== null
                          ? (
                            <>
                              {activeNs}{' '}
                              <span style={{ color: 'var(--ink-faint)', fontFamily: 'Hanken Grotesk, sans-serif', fontWeight: 400, fontSize: '.85rem' }}>
                                / presets
                              </span>
                            </>
                          )
                          : 'All Presets'}
                    </h3>
                    <Badge tone="teal">{visibleRows.length}</Badge>
                  </div>

                  {visibleRows.length === 0 ? (
                    <div className="state-box">
                      <div className="state-icon">◇</div>
                      <p>
                        {search
                          ? `No presets match "${search}".`
                          : 'No presets found for this randomizer.'}
                      </p>
                    </div>
                  ) : (
                    <div className="table-wrap" style={{ border: 'none', borderRadius: 0 }}>
                      <table className="data" style={{ minWidth: 0 }}>
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Namespace</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {visibleRows.map((row) => {
                            const key = `${row.namespace ?? '__global__'}/${row.presetName}`;
                            return (
                              <tr
                                key={key}
                                className={isRowSelected(row) ? 'selected' : undefined}
                              >
                                <td className="preset-path">
                                  {row.namespace && (
                                    <span className="ns-part">{row.namespace}/</span>
                                  )}
                                  {row.presetName}
                                </td>
                                <td>
                                  {row.namespace
                                    ? <span className="rand-tag">{row.namespace}</span>
                                    : <Badge tone="gold">global</Badge>
                                  }
                                </td>
                                <td>
                                  <button
                                    className="preset-view-btn"
                                    onClick={() => setSelected(row)}
                                    aria-label={`View ${row.presetName}`}
                                  >
                                    view →
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Right: detail panel */}
                {selected ? (
                  <PresetDetailPanel
                    randomizer={randomizer}
                    presetName={selected.presetName}
                    namespace={selected.namespace}
                  />
                ) : (
                  <div className="panel">
                    <div className="state-box" style={{ minHeight: 200 }}>
                      <div className="state-icon">◈</div>
                      <p>Select a preset from the list to inspect its YAML.</p>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

        </div>
      </section>
    </>
  );
}
