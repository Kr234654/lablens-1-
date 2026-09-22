import { useMemo, useState } from 'react';
import { AlertIcon, ArrowLeft, CheckCircle } from './Icons';
import ValueCard from './ValueCard';

const GROUP_ORDER = ['Blood count', 'Sugar', 'Cholesterol', 'Kidney', 'Liver', 'Thyroid', 'Vitamins & minerals', 'Electrolytes'];
const FILTERS = [
  { id: 'flagged', label: 'Worth a look' },
  { id: 'all', label: 'All results' },
];

// Turns **bold** and "- " bullets from the AI/summary text into simple HTML-free React nodes.
function SummaryText({ text }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split('\n').filter(Boolean);
        const isList = lines.length > 0 && lines.every((l) => l.trim().startsWith('- '));
        const renderInline = (line) => line.split(/(\*\*[^*]+\*\*)/g).map((chunk, j) => (
          chunk.startsWith('**') && chunk.endsWith('**') ? <strong key={j}>{chunk.slice(2, -2)}</strong> : chunk
        ));
        if (isList) {
          return <ul key={i}>{lines.map((l, j) => <li key={j}>{renderInline(l.replace(/^- /, ''))}</li>)}</ul>;
        }
        if (lines.length === 1 && /^\*\*[^*]+\*\*$/.test(lines[0].trim())) {
          return <h4 key={i}>{lines[0].trim().slice(2, -2)}</h4>;
        }
        return <p key={i}>{lines.map((l, j) => <span key={j}>{renderInline(l)}{j < lines.length - 1 && <br />}</span>)}</p>;
      })}
    </>
  );
}

export default function ResultsView({ result, onAsk, onReset }) {
  const [filter, setFilter] = useState('flagged');
  const { values, counts, summary, disclaimer, mode } = result;

  const grouped = useMemo(() => {
    const shown = filter === 'flagged' ? values.filter((v) => v.status !== 'normal') : values;
    const byGroup = {};
    shown.forEach((v) => { (byGroup[v.group] ??= []).push(v); });
    return GROUP_ORDER.filter((g) => byGroup[g]).map((g) => [g, byGroup[g]]);
  }, [values, filter]);

  const flaggedCount = counts.low + counts.high;

  return (
    <div className="results">
      <button type="button" className="link-back" onClick={onReset}>
        <ArrowLeft width={16} height={16} /> Analyse another report
      </button>

      <div className="card summary-card">
        <div className="summary-head">
          <div className={`summary-badge ${flaggedCount ? 'is-flagged' : 'is-ok'}`}>
            {flaggedCount ? <AlertIcon width={20} height={20} /> : <CheckCircle width={20} height={20} />}
          </div>
          <div>
            <h2>{flaggedCount ? `${flaggedCount} value${flaggedCount > 1 ? 's' : ''} worth a look` : 'Everything looks within range'}</h2>
            <p>{values.length} values read · {counts.normal} normal · {flaggedCount} out of range{counts.unknown ? ` · ${counts.unknown} need the report's own range` : ''}</p>
          </div>
        </div>

        <div className="summary-text">
          <SummaryText text={summary.text} />
        </div>
        {mode === 'basic' && (
          <p className="mode-note">Basic mode: this explanation is rule-based. Add an AI key on the server for a more personal explanation.</p>
        )}
        <p className="disclaimer">{disclaimer}</p>
      </div>

      <div className="card">
        <div className="results-toolbar">
          <h3>Your values</h3>
          <div className="segmented">
            {FILTERS.map((f) => (
              <button key={f.id} type="button" className={filter === f.id ? 'is-active' : ''} onClick={() => setFilter(f.id)}>
                {f.label}{f.id === 'flagged' && flaggedCount ? ` (${flaggedCount})` : ''}
              </button>
            ))}
          </div>
        </div>

        {grouped.length === 0 ? (
          <p className="empty-note">Nothing outside the usual range here. Switch to "All results" to see everything.</p>
        ) : (
          grouped.map(([group, items]) => (
            <div key={group} className="value-group">
              <h4 className="group-title">{group}</h4>
              <div className="value-list">
                {items.map((v) => <ValueCard key={v.key} v={v} onAsk={onAsk} />)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
