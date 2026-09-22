const LANGUAGES = ['English', 'Hindi', 'Hinglish'];

export default function PersonForm({ age, sex, language, onChange }) {
  return (
    <div className="person-form">
      <label>
        <span>Age (optional)</span>
        <input
          type="number" min="1" max="120" placeholder="e.g. 34" value={age}
          onChange={(e) => onChange({ age: e.target.value })}
        />
      </label>
      <label>
        <span>Sex (optional)</span>
        <select value={sex} onChange={(e) => onChange({ sex: e.target.value })}>
          <option value="">Prefer not to say</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
        </select>
      </label>
      <label>
        <span>Explain in</span>
        <select value={language} onChange={(e) => onChange({ language: e.target.value })}>
          {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </label>
    </div>
  );
}
