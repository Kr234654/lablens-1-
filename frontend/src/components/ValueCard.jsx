import { useState } from 'react';
import { ChevronDown } from './Icons';

const STATUS_LABEL = { normal: 'Normal', low: 'Low', high: 'High', unknown: 'Check range' };

const fmt = (x) => (x === null || x === undefined ? '' : Number.isInteger(x) ? x.toLocaleString() : x);

function rangeText(v) {
  if (v.low != null && v.high != null) return `${fmt(v.low)} – ${fmt(v.high)} ${v.unit}`;
  if (v.high != null) return `below ${fmt(v.high)} ${v.unit}`;
  if (v.low != null) return `above ${fmt(v.low)} ${v.unit}`;
  return 'see report';
}

// Position (0 to 100%) of the value along a low-to-high bar, for the mini gauge.
function gaugePercent(v) {
  const { value, low, high } = v;
  if (low == null && high == null) return 50;
  const lo = low ?? high - Math.abs(high) * 0.4 - 1;
  const hi = high ?? low + Math.abs(low) * 0.4 + 1;
  const span = hi - lo || 1;
  const pad = span * 0.25;
  return Math.max(2, Math.min(98, ((value - (lo - pad)) / (span + pad * 2)) * 100));
}

export default function ValueCard({ v, onAsk }) {
  const [open, setOpen] = useState(v.status !== 'normal');
  const flagged = v.status === 'low' || v.status === 'high';

  return (
    <div className={`value-card status-${v.status}`}>
      <button type="button" className="value-head" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <div className="value-head-main">
          <span className={`status-dot dot-${v.status}`} />
          <span className="value-name">{v.name}</span>
          <span className={`status-pill pill-${v.status}`}>{STATUS_LABEL[v.status]}</span>
        </div>
        <div className="value-head-right">
          <span className="value-num">{fmt(v.value)} <small>{v.unit}</small></span>
          <ChevronDown className={`chev ${open ? 'is-open' : ''}`} width={18} height={18} />
        </div>
      </button>

      {v.low != null || v.high != null ? (
        <div className="gauge" aria-hidden="true">
          <div className="gauge-track">
            {v.low != null && v.high != null && <div className="gauge-good" />}
          </div>
          <div className="gauge-dot" style={{ left: `${gaugePercent(v)}%` }} />
        </div>
      ) : null}

      {open && (
        <div className="value-body">
          <p className="value-about">{v.about}</p>
          <p className="value-range">Usual range: {rangeText(v)}{v.range_source === 'report' ? ' (from your report)' : ''}</p>
          {flagged && v.note && <p className="value-note">{v.note}</p>}
          {onAsk && (
            <button type="button" className="ask-link" onClick={() => onAsk(v.name)}>
              Ask the assistant about this →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
