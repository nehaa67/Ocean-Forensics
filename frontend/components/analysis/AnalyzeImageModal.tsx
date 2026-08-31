'use client';
import { useState } from 'react';
import { CheckCircle2, Database, FileUp, LoaderCircle, Play, X } from 'lucide-react';
import { adaptInvestigation, backendApi } from '../../services/backendService';
import type { ImageAnalysisResult } from '../../services/analysisService';

type UploadKey = 'sentinel' | 'wind' | 'current' | 'ais';
const fields: Array<{ key: UploadKey; label: string; accept: string; hint: string }> = [
  { key: 'sentinel', label: 'Sentinel-1 / GeoTIFF · required', accept: '.zip,.tif,.tiff', hint: 'SAFE ZIP, TIF or TIFF' },
  { key: 'wind', label: 'Wind dataset · optional', accept: '.nc,.nc4,.csv,.json', hint: 'Improves drift reconstruction' },
  { key: 'current', label: 'Ocean current · optional', accept: '.nc,.nc4,.csv,.json', hint: 'Improves movement modelling' },
  { key: 'ais', label: 'AIS records · optional', accept: '.csv,.json', hint: 'Enables vessel attribution' },
];
const legacyDemoNames = new Set([
  '1.oil_spill_image.tif',
  '2.no_oil_image.tif',
  '3.lookalike_image.tif',
]);

export default function AnalyzeImageModal({ onClose, onResult }: { onClose: () => void; onResult: (result: ImageAnalysisResult) => void }) {
  const [mode, setMode] = useState<'sanchi' | 'upload'>('sanchi');
  const [files, setFiles] = useState<Partial<Record<UploadKey, File>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const runSanchi = async () => {
    setLoading(true); setError(''); setMessage('');
    try { const result = await backendApi.runSanchi(); onResult(result); onClose(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to run Sanchi investigation.'); }
    finally { setLoading(false); }
  };
  const submitFiles = async () => {
    if (!files.sentinel) { setError('Add a Sentinel-1 or GeoTIFF file to continue.'); return; }
    setLoading(true); setError(''); setMessage('Creating investigation workspace…');
    try {
      if (legacyDemoNames.has(files.sentinel.name.toLowerCase())) {
        setMessage('Running deterministic GeoTIFF demo analysis…');
        const result = await backendApi.analyzeDemoTiff(files.sentinel);
        onResult(result);
        if (result.detected) onClose();
        else setMessage(result.message ?? 'Analysis completed.');
        return;
      }
      const { analysis_id } = await backendApi.createInvestigation();
      const supplied = fields.filter(({ key }) => files[key]);
      for (const [index, field] of supplied.entries()) {
        setMessage(`Uploading ${field.label.replace(' · required', '').replace(' · optional', '')} (${index + 1}/${supplied.length})…`);
        await backendApi.upload(analysis_id, field.key, files[field.key]!);
      }
      setMessage('Validating supplied datasets…');
      const validation = await backendApi.validate(analysis_id);
      if (!validation.is_valid) throw new Error(validation.errors.join(' '));
      setMessage('Starting forensic investigation…');
      const run = await backendApi.runUploaded(analysis_id);
      if (run.status !== 'completed' || !run.detection || !run.geometry) {
        throw new Error(
          'The backend accepted the files but did not run analysis. Its upload /run endpoint currently returns ready_for_processing without detection results. Use the Sanchi demo for the complete investigation, or ask the backend team to connect processing to this endpoint.',
        );
      }
      onResult(adaptInvestigation(run));
      onClose();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Investigation submission failed.'); }
    finally { setLoading(false); }
  };
  return <div className="modal-backdrop analysis-upload-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="analysis-upload panel integration-modal" role="dialog" aria-modal="true" aria-labelledby="analysis-title">
      <header><div><small>OCEAN FORENSICS API</small><h2 id="analysis-title">Open an investigation</h2><p>Run the historical Sanchi case or submit a complete evidence package.</p></div><button onClick={onClose} aria-label="Close"><X size={17} /></button></header>
      <div className="integration-tabs"><button className={mode === 'sanchi' ? 'active' : ''} onClick={() => { setMode('sanchi'); setError(''); }}><Database size={16} /> Sanchi demo</button><button className={mode === 'upload' ? 'active' : ''} onClick={() => { setMode('upload'); setError(''); }}><FileUp size={16} /> New investigation</button></div>
      {mode === 'sanchi' ? <div className="sanchi-run-card"><small>PREDEFINED HISTORICAL INCIDENT</small><h3>Sanchi · East China Sea</h3><p>Uses the frozen Sentinel-1 model, wind and current grids, historical AIS, backward drift and attribution pipeline.</p><dl><div><dt>Observation</dt><dd>20 Jan 2018 · 09:28 UTC</dd></div><div><dt>Pipeline</dt><dd>Cached verified outputs</dd></div></dl><button className="run-analysis" disabled={loading} onClick={runSanchi}>{loading ? <><LoaderCircle className="spin" size={16} /> Loading investigation…</> : <><Play size={16} /> RUN SANCHI INVESTIGATION <span>→</span></>}</button></div> :
      <div className="evidence-package"><p>A Sentinel-1 scene or GeoTIFF is enough to begin. Add environmental and AIS files only when available for richer drift and attribution results.</p><div className="evidence-file-grid">{fields.map((field) => <label key={field.key} className={files[field.key] ? 'selected' : ''}><input type="file" accept={field.accept} onChange={(event) => setFiles((current) => ({ ...current, [field.key]: event.target.files?.[0] }))} />{files[field.key] ? <CheckCircle2 size={18} /> : <FileUp size={18} />}<span><strong>{field.label}</strong><small>{files[field.key]?.name ?? field.hint}</small></span></label>)}</div><button className="run-analysis" disabled={loading || !files.sentinel} onClick={submitFiles}>{loading ? <><LoaderCircle className="spin" size={16} /> {message}</> : <>ANALYZE SATELLITE SCENE <span>→</span></>}</button></div>}
      {error && <div className="analysis-error">{error}</div>}{!loading && message && <div className="analysis-success"><CheckCircle2 size={16} />{message}</div>}
    </section>
  </div>;
}
