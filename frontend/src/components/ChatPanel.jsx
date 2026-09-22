import { useEffect, useRef, useState } from 'react';
import { SendIcon } from './Icons';

const SUGGESTIONS = ['What should I ask my doctor?', 'What foods might help?', 'Which result needs the most attention?'];

export default function ChatPanel({ chat, askQueue }) {
  const { messages, sending, send } = chat;
  const [value, setValue] = useState('');
  const listRef = useRef(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages.length, sending]);

  // A "Ask about this" click from a value card lands here.
  useEffect(() => {
    if (askQueue.value) {
      send(`What does my ${askQueue.value} mean?`);
      askQueue.clear();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [askQueue.value]);

  const submit = (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    send(value);
    setValue('');
  };

  return (
    <div className="card chat-card">
      <h3>Ask about your report</h3>
      <p className="chat-sub">Ask in your own words. The assistant only sees the values from this report.</p>

      <div className="chat-list" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="suggestion" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`chat-row ${m.role === 'user' ? 'chat-row-user' : ''}`}>
            <div className={`chat-bubble ${m.role === 'user' ? 'bubble-user' : 'bubble-bot'} ${m.isError ? 'bubble-error' : ''}`}>
              {m.text}
              {m.citations?.length > 0 && (
                <div className="citations">
                  <span>Sources:</span>
                  {m.citations.map((c) => <span key={c.title} className="citation-chip">{c.title}</span>)}
                </div>
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="chat-row">
            <div className="chat-bubble bubble-bot typing"><span /><span /><span /></div>
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={submit}>
        <input
          value={value} onChange={(e) => setValue(e.target.value)} placeholder="Ask a question about your report"
          maxLength={500} aria-label="Ask a question about your report"
        />
        <button type="submit" className="send" disabled={!value.trim() || sending} aria-label="Send">
          <SendIcon width={18} height={18} />
        </button>
      </form>
    </div>
  );
}
