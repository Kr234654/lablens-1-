import { useCallback, useRef, useState } from 'react';
import { API_URL } from '../config';

let counter = 0;
const nextId = () => `m${++counter}`;

// A follow-up chat about one analysed report. The browser holds the values and history;
// the server never stores anything between requests.
export default function useReportChat(result, language) {
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const historyRef = useRef([]);

  const send = useCallback(async (question) => {
    const clean = question.trim();
    if (!clean || sending) return;

    const userMsg = { id: nextId(), role: 'user', text: clean };
    setMessages((list) => [...list, userMsg]);
    setSending(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: clean,
          values: result.values,
          summary: result.summary.text,
          history: historyRef.current,
          language,
        }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error(body?.detail || 'Something went wrong. Please try again.');

      historyRef.current = [...historyRef.current, { role: 'user', text: clean }, { role: 'bot', text: body.answer }].slice(-12);
      setMessages((list) => [...list, { id: nextId(), role: 'bot', text: body.answer, source: body.source, citations: body.citations || [] }]);
    } catch (err) {
      setMessages((list) => [...list, {
        id: nextId(), role: 'bot', isError: true,
        text: err instanceof TypeError ? 'I cannot reach the server right now.' : err.message,
      }]);
    } finally {
      setSending(false);
    }
  }, [result, language, sending]);

  return { messages, sending, send };
}
