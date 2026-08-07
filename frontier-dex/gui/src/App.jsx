import React, { useState } from 'react';

const API = '/api/decompile';

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [opts, setOpts] = useState({
    proof: true,
    neural: true,
    cache: true,
  });

  async function decompile() {
    if (!file) return;
    setLoading(true);
    const form = new FormData();
    form.append('dex', file);
    form.append('options', JSON.stringify(opts));
    try {
      const res = await fetch(API, { method: 'POST', body: form });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  }

  return (
    <div style={{ fontFamily: 'system-ui', maxWidth: 960, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Frontier-DEX</h1>
      <p>Formally verified Android DEX decompiler — Frontier Syntax v2.0</p>
      <div style={{ marginBottom: '1rem' }}>
        <input type="file" accept=".dex" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <label><input type="checkbox" checked={opts.proof} onChange={(e) => setOpts({ ...opts, proof: e.target.checked })} /> Proof</label>
        <label><input type="checkbox" checked={opts.neural} onChange={(e) => setOpts({ ...opts, neural: e.target.checked })} /> Neural</label>
        <label><input type="checkbox" checked={opts.cache} onChange={(e) => setOpts({ ...opts, cache: e.target.checked })} /> Cache</label>
      </div>
      <button onClick={decompile} disabled={!file || loading}>
        {loading ? 'Decompiling…' : 'Decompile'}
      </button>
      {result && (
        <pre style={{ background: '#111', color: '#0f0', padding: '1rem', marginTop: '1rem', overflow: 'auto' }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
