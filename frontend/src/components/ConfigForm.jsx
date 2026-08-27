import { useState, useEffect } from 'react';
import AutocompleteInput from './AutocompleteInput';
import { fetchAllHardware } from '../api';

const GAMES = [
  'Apex Legends','Airmech Strike','Battlefield4','Battletech',
  'Call Of Duty Ww2','Counter Strike Global Offensive','Destiny2','Dota2',
  'Far Cry5','Fortnite','Frostpunk','Grand Theft Auto5',
  'League Of Legends','Overwatch','Path Of Exile','Player Unknowns Battlegrounds',
  'Rainbow Six Siege','Sea Of Thieves','Starcraft2','Total War3 Kingdoms',
  'Warframe','Way Out','World Of Tanks',
];
const RESOLUTIONS = [
  { value: '1080p', label: '1080p — Full HD' },
  { value: '1440p', label: '1440p — 2K / QHD' },
  { value: '4k',    label: '4K — Ultra HD' },
];
const SETTINGS = [
  { value: 'low',   label: 'Low' },
  { value: 'med',   label: 'Medium' },
  { value: 'high',  label: 'High' },
  { value: 'ultra', label: 'Ultra' },
  { value: 'max',   label: 'Max / Epic' },
];

export default function ConfigForm({ onSubmit, loading }) {
  const [cpuName,    setCpuName]    = useState('');
  const [gpuName,    setGpuName]    = useState('');
  const [gameName,   setGameName]   = useState('');
  const [resolution, setResolution] = useState('1080p');
  const [setting,    setSetting]    = useState('high');
  const [errors,     setErrors]     = useState({});
  const [cpuList,    setCpuList]    = useState([]);
  const [gpuList,    setGpuList]    = useState([]);
  const [hwStatus,   setHwStatus]   = useState('loading');

  useEffect(() => {
    fetchAllHardware()
      .then(({ cpus, gpus }) => { setCpuList(cpus); setGpuList(gpus); setHwStatus('ready'); })
      .catch(() => setHwStatus('error'));
  }, []);

  function validate() {
    const e = {};
    if (!cpuName.trim()) e.cpu  = 'Select a CPU from suggestions';
    if (!gpuName.trim()) e.gpu  = 'Select a GPU from suggestions';
    if (!gameName)       e.game = 'Choose a game';
    return e;
  }

  function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setErrors({});
    onSubmit({ cpuName, gpuName, gameName, resolution, setting });
  }

  return (
    <form className="config-form" onSubmit={handleSubmit} noValidate>

      {/* Hardware status */}
      <div className={`hw-banner hw-banner--${hwStatus}`}>
        {hwStatus === 'loading' && <><span className="hw-spinner" />Loading hardware database…</>}
        {hwStatus === 'ready'   && <>✓ {cpuList.length} CPUs · {gpuList.length} GPUs ready</>}
        {hwStatus === 'error'   && <>⚠ Cannot reach Django on :8000</>}
      </div>

      {/* CPU */}
      <AutocompleteInput
        id="cpu-input"
        label="Processor (CPU)"
        placeholder="Type to filter, e.g. i9-9900K…"
        icon="⚙"
        allNames={cpuList}
        value={cpuName}
        onChange={setCpuName}
      />
      {errors.cpu && <p className="form-error" style={{marginTop:'-10px'}}>{errors.cpu}</p>}

      {/* GPU */}
      <AutocompleteInput
        id="gpu-input"
        label="Graphics Card (GPU)"
        placeholder="Type to filter, e.g. RTX 2080 Ti…"
        icon="▣"
        allNames={gpuList}
        value={gpuName}
        onChange={setGpuName}
      />
      {errors.gpu && <p className="form-error" style={{marginTop:'-10px'}}>{errors.gpu}</p>}

      {/* Game */}
      <div className="form-field">
        <label className="field-label" htmlFor="game-select">
          <span className="field-icon">◈</span>Game Title
        </label>
        <select id="game-select" className="field-select" value={gameName}
          onChange={(e) => setGameName(e.target.value)}>
          <option value="">— Select a game —</option>
          {GAMES.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
        {errors.game && <p className="form-error">{errors.game}</p>}
      </div>

      {/* Resolution + Setting side by side */}
      <div className="form-row-2">
        <div className="form-field">
          <label className="field-label" htmlFor="res-select">
            <span className="field-icon">⬡</span>Resolution
          </label>
          <select id="res-select" className="field-select" value={resolution}
            onChange={(e) => setResolution(e.target.value)}>
            {RESOLUTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>

        <div className="form-field">
          <label className="field-label" htmlFor="setting-select">
            <span className="field-icon">◉</span>Quality
          </label>
          <select id="setting-select" className="field-select" value={setting}
            onChange={(e) => setSetting(e.target.value)}>
            {SETTINGS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      <button
        type="submit"
        id="predict-btn"
        className="predict-btn"
        disabled={loading || hwStatus === 'loading'}
        aria-busy={loading}
      >
        {loading
          ? <><span className="btn-spinner" />Analyzing…</>
          : <>⚡ Predict FPS</>
        }
      </button>

    </form>
  );
}
