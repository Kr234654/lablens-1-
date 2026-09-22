import { useState } from 'react';
import { API_URL } from '../config';
import Dropzone from './Dropzone';
import PersonForm from './PersonForm';
import { ShieldIcon, SparkleIcon } from './Icons';

const TABS = [{ id: 'pdf', label: 'Upload PDF' }, { id: 'text', label: 'Paste text' }];

export default function UploadCard({ onResult }) {
  const [tab, setTab] = useState('pdf');
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [fileError, setFileError] = useState(null);
  const [person, setPerson] = useState({ age: '', sex: '', language: 'English' });
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState('');
  const [error, setError] = useState('');

  const run = async (formData, label) => {
    setLoading(true);
    setLoadingLabel(label);
    setError('');
    try {
      const res = await fetch(`${API_URL}/api/analyze`, { method: 'POST', body: formData });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error(body?.detail || `The server returned an error (${res.status}).`);
      onResult(body);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? 'I cannot reach the server right now. Please check your connection and try again.'
          : err.message,
      );
    } finally {
      setLoading(false);
    }
  };

  const buildForm = () => {
    const form = new FormData();
    if (person.age) form.set('age', person.age);
    if (person.sex) form.set('sex', person.sex);
    form.set('language', person.language);
    return form;
  };

  const submit = (e) => {
    e.preventDefault();
    const form = buildForm();
    if (tab === 'pdf') {
      if (!file) { setError('Please choose a PDF file first.'); return; }
      form.set('file', file);
      run(form, 'Reading your PDF');
    } else {
      if (!text.trim()) { setError('Please paste the results table first.'); return; }
      form.set('text', text);
      run(form, 'Reading your report');
    }
  };

  const tryDemo = () => {
    const form = buildForm();
    form.set('use_sample', 'true');
    run(form, 'Loading the sample report');
  };

  return (
    <div className="card upload-card">
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'is-active' : ''} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <form onSubmit={submit}>
        {tab === 'pdf' ? (
          <Dropzone file={file} error={fileError} onFile={(f, err) => { setFile(f); setFileError(err); }} />
        ) : (
          <textarea
            className="text-input" rows={8} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={'Paste the results table from your report, for example:\nHemoglobin  11.2  g/dL  12.0 - 15.0\nFasting Glucose  108  mg/dL  70 - 99'}
          />
        )}
        {fileError && <p className="field-error">{fileError}</p>}

        <PersonForm {...person} onChange={(patch) => setPerson((p) => ({ ...p, ...patch }))} />

        {error && <p className="field-error">{error}</p>}

        <div className="upload-actions">
          <button type="submit" className="btn btn-accent" disabled={loading}>
            {loading ? loadingLabel + '…' : 'Explain my report'}
          </button>
          <button type="button" className="btn btn-outline" onClick={tryDemo} disabled={loading}>
            <SparkleIcon width={16} height={16} /> Try a sample report
          </button>
        </div>
      </form>

      <p className="privacy-note"><ShieldIcon width={15} height={15} /> Your report is analysed to show these results and is not stored on our server.</p>
    </div>
  );
}
