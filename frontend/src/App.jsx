import { useState } from 'react';
import ChatPanel from './components/ChatPanel';
import { LensMark } from './components/Icons';
import ResultsView from './components/ResultsView';
import UploadCard from './components/UploadCard';
import useReportChat from './hooks/useReportChat';

export default function App() {
  const [result, setResult] = useState(null);
  const [language, setLanguage] = useState('English');
  const [askValue, setAskValue] = useState(null);
  const chat = useReportChat(result, language);

  const reset = () => setResult(null);

  return (
    <>
      <header className="site-header">
        <div className="wrap site-header-inner">
          <a href="#" className="brand" onClick={(e) => { e.preventDefault(); reset(); }}>
            <LensMark /> LabLens
          </a>
          <p className="tagline">Understand your blood report, in plain language</p>
        </div>
      </header>

      <main className="wrap main">
        {!result ? (
          <div className="intro">
            <h1>Upload your blood report. We will explain what it means.</h1>
            <p className="intro-sub">
              LabLens reads the values from your report, checks them against usual ranges, and explains
              them in plain language. Nothing is diagnosed, and this never replaces your doctor.
            </p>
            <UploadCard onResult={(r) => { setResult(r); setLanguage('English'); }} />
          </div>
        ) : (
          <div className="results-layout">
            <ResultsView result={result} onReset={reset} onAsk={(name) => setAskValue(name)} />
            <ChatPanel chat={chat} askQueue={{ value: askValue, clear: () => setAskValue(null) }} />
          </div>
        )}
      </main>

      <footer className="site-footer">
        <div className="wrap">
          <p>LabLens is an educational demo project. It does not store your report and is not a medical device.</p>
        </div>
      </footer>
    </>
  );
}
