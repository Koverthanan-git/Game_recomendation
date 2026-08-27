import { useState, useEffect, useRef, useMemo } from 'react';

export default function AutocompleteInput({
  id, label, placeholder, icon, allNames = [], value, onChange,
}) {
  const [text,      setText]      = useState(value || '');
  const [open,      setOpen]      = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const wrapRef  = useRef(null);
  const listRef  = useRef(null);
  const inputRef = useRef(null);

  /* Instant local filter — starts-with first, then contains */
  const filtered = useMemo(() => {
    const q = text.trim().toLowerCase();
    if (!q) return [];
    const sw = [], cont = [];
    for (const n of allNames) {
      const nl = n.toLowerCase();
      if (nl.startsWith(q)) sw.push(n);
      else if (nl.includes(q)) cont.push(n);
    }
    return [...sw, ...cont].slice(0, 10);
  }, [text, allNames]);

  useEffect(() => { setOpen(filtered.length > 0); setActiveIdx(-1); }, [filtered]);

  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      listRef.current.querySelectorAll('li')[activeIdx]?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIdx]);

  useEffect(() => {
    const h = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  function confirm(name) {
    setText(name); onChange(name); setOpen(false); setActiveIdx(-1);
  }

  function handleKeyDown(e) {
    if (!open && e.key !== 'ArrowDown') return;
    if (e.key === 'ArrowDown')  { e.preventDefault(); setOpen(true); setActiveIdx(i => Math.min(i + 1, filtered.length - 1)); }
    else if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter')     { e.preventDefault(); if (activeIdx >= 0) confirm(filtered[activeIdx]); }
    else if (e.key === 'Tab' && filtered.length) { e.preventDefault(); confirm(filtered[0]); }
    else if (e.key === 'Escape')    setOpen(false);
  }

  /* Highlight matched substring */
  function highlight(name) {
    const q = text.trim();
    if (!q) return name;
    const idx = name.toLowerCase().indexOf(q.toLowerCase());
    if (idx < 0) return name;
    return <>{name.slice(0, idx)}<span className="ac-match">{name.slice(idx, idx + q.length)}</span>{name.slice(idx + q.length)}</>;
  }

  const confirmed = value && value.toLowerCase() === text.toLowerCase();

  return (
    <div className="form-field" ref={wrapRef}>
      <label className="field-label" htmlFor={id}>
        <span className="field-icon">{icon}</span>{label}
        {confirmed && <span style={{ marginLeft: 'auto', color: 'var(--green)', fontSize: '.7rem' }}>✓ set</span>}
      </label>

      <div className="field-input-wrap" style={{ position: 'relative' }}>
        <input
          id={id}
          ref={inputRef}
          className={`field-input ${confirmed ? 'field-input--confirmed' : ''}`}
          type="text"
          autoComplete="off"
          spellCheck={false}
          placeholder={placeholder}
          value={text}
          onChange={(e) => { setText(e.target.value); onChange(''); }}
          onFocus={() => { if (filtered.length) setOpen(true); }}
          onKeyDown={handleKeyDown}
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-list`}
        />
        {text && (
          <button
            type="button"
            className="field-clear-btn"
            onClick={() => { setText(''); onChange(''); setOpen(false); inputRef.current?.focus(); }}
          >×</button>
        )}

        {open && (
          <ul id={`${id}-list`} ref={listRef} role="listbox" className="ac-dropdown">
            {filtered.map((name, i) => (
              <li
                key={name}
                role="option"
                aria-selected={i === activeIdx}
                className={`ac-item ${i === activeIdx ? 'ac-item--active' : ''}`}
                onMouseDown={(e) => { e.preventDefault(); confirm(name); }}
                onMouseEnter={() => setActiveIdx(i)}
              >
                {highlight(name)}
              </li>
            ))}
            <li className="ac-footer-hint" aria-hidden>
              {filtered.length} match{filtered.length !== 1 ? 'es' : ''} · ↑↓ · Enter/Tab
            </li>
          </ul>
        )}
      </div>

      {text.length >= 2 && !open && !confirmed && allNames.length > 0 && (
        <p className="ac-no-results">No match for "{text}"</p>
      )}
    </div>
  );
}
