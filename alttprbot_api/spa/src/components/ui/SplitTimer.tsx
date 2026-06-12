import { useEffect, useRef, useState } from 'react';

const pad = (n: number, l = 2) => String(n).padStart(l, '0');

/** Live speedrun-style split timer, counting up from mount. */
export function SplitTimer() {
  const [clock, setClock] = useState('00:00:00');
  const [centis, setCentis] = useState('.00');
  const [delta, setDelta] = useState('▲ −0:00.4 ahead of best');
  const [ahead, setAhead] = useState(true);
  const startRef = useRef<number>(performance.now());

  useEffect(() => {
    let raf = 0;
    const tick = (now: number) => {
      const t = (now - startRef.current) / 1000;
      const h = Math.floor(t / 3600);
      const m = Math.floor((t % 3600) / 60);
      const s = Math.floor(t % 60);
      const cs = Math.floor((t * 100) % 100);
      setClock(`${pad(h)}:${pad(m)}:${pad(s)}`);
      setCentis(`.${pad(cs)}`);
      const swing = Math.sin(t * 0.7) * 1.4;
      const isAhead = swing <= 0;
      setAhead(isAhead);
      setDelta(
        `${isAhead ? '▲ −' : '▼ +'}0:0${Math.abs(swing).toFixed(1)}${isAhead ? ' ahead of best' : ' behind best'}`,
      );
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="splitclock reveal d3" aria-hidden="true">
      <span className="label">Session uptime · live</span>
      <span className="time">
        <span>{clock}</span>
        <span className="ms">{centis}</span>
      </span>
      <span className="delta" style={{ color: ahead ? 'var(--teal)' : 'var(--crimson)' }}>
        {delta}
      </span>
    </div>
  );
}
