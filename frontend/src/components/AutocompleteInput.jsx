import { useState, useEffect, useRef, useMemo } from 'react';

/**
 * AutocompleteInput — Country-selector style instant filtering.
 *
 * Receives the full `allNames` list from the parent (pre-loaded once).
 * Filters entirely in-memory as the user types — zero network lag.
 *
 * Props:
 *   id          — unique HTML id for the input
 *   label       — visible label above the input
 *   placeholder — input placeholder text
 *   icon        — emoji/icon for the label
 *   allNames    — string[] — the full list loaded from /api/hardware/all
 *   value       — controlled confirmed value (empty while typing)
 *   onChange    — (confirmedValue: string) => void
 */
export default function AutocompleteInput({
  id,
  label,
  placeholder,
  icon,
  allNames = [],
  value,
  onChange,
}) {
  const [inputText,  setInputText]  = useState(value || '');
  const [open,       setOpen]       = useState(false);
  const [activeIdx,  setActiveIdx]  = useState(-1);
  const wrapRef    = useRef(null);
  const listRef    = useRef(null);
  const inputRef   = useRef(null);

  /* ── Instant local filter — runs on every keystroke with no delay ── */
  const filtered = useMemo(() => {
    const q = inputText.trim().toLowerCase();
    if (!q) return [];
    // Match anywhere in the name, sort: starts-with first, then contains
    const startsWith = [];
    const contains   = [];
    for (const name of allNames) {
      const n = name.toLowerCase();
      if (n.startsWith(q))     startsWith.push(name);
      else if (n.includes(q))  contains.push(name);
    }
    return [...startsWith, ...contains].slice(0, 12); // max 12 items
  }, [inputText, allNames]);

  /* Show/hide dropdown based on filtered results */
  useEffect(() => {
    setOpen(filtered.length > 0);
    setActiveIdx(-1);
  }, [filtered]);

  /* Scroll active item into view */
  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      const li = listRef.current.querySelectorAll('li')[activeIdx];
      li?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIdx]);

  /* Close on outside click */
  useEffect(() => {
    function handler(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  function confirmSelection(name) {
    setInputText(name);
    onChange(name);
    setOpen(false);
    setActiveIdx(-1);
  }

  function handleKeyDown(e) {
    if (!open && e.key !== 'ArrowDown') return;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setOpen(true);
        setActiveIdx((i) => Math.min(i + 1, filtered.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (activeIdx >= 0) confirmSelection(filtered[activeIdx]);
        break;
      case 'Escape':
        setOpen(false);
        break;
      case 'Tab':
        // Accept the top suggestion on Tab
        if (filtered.length > 0) {
          e.preventDefault();
          confirmSelection(filtered[0]);
        }
        break;
    }
  }

  /* Highlight the matched part of the text in each suggestion */
  function highlight(name) {
    const q = inputText.trim();
    if (!q) return name;
    const idx = name.toLowerCase().indexOf(q.toLowerCase());
    if (idx < 0) return name;
    return (
      <>
        {name.slice(0, idx)}
        <mark className="ac-highlight">{name.slice(idx, idx + q.length)}</mark>
        {name.slice(idx + q.length)}
      </>
    );
  }

  const isConfirmed = value && value === inputText;

  return (
    <div className="ac-wrap" ref={wrapRef}>
      <label className="ac-label" htmlFor={id}>
        <span className="ac-icon">{icon}</span>
        {label}
        {isConfirmed && <span className="ac-confirmed">✓</span>}
      </label>

      <div className={`ac-box ${open ? 'ac-box--open' : ''} ${isConfirmed ? 'ac-box--confirmed' : ''}`}>
        <input
          id={id}
          ref={inputRef}
          className="ac-input"
          type="text"
          autoComplete="off"
          spellCheck={false}
          placeholder={placeholder}
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            onChange(''); // clear confirmed value while user is still typing
          }}
          onFocus={() => { if (filtered.length > 0) setOpen(true); }}
          onKeyDown={handleKeyDown}
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-list`}
          aria-activedescendant={activeIdx >= 0 ? `${id}-opt-${activeIdx}` : undefined}
        />

        {/* Clear button */}
        {inputText && (
          <button
            type="button"
            className="ac-clear"
            aria-label="Clear"
            onClick={() => {
              setInputText('');
              onChange('');
              setOpen(false);
              inputRef.current?.focus();
            }}
          >
            ×
          </button>
        )}
      </div>

      {/* Dropdown list */}
      {open && (
        <ul
          id={`${id}-list`}
          ref={listRef}
          role="listbox"
          className="ac-dropdown"
          aria-label={label}
        >
          {filtered.map((name, i) => (
            <li
              key={name}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === activeIdx}
              className={`ac-item ${i === activeIdx ? 'ac-item--active' : ''}`}
              onMouseDown={(e) => {
                e.preventDefault(); // prevent blur before click registers
                confirmSelection(name);
              }}
              onMouseEnter={() => setActiveIdx(i)}
            >
              <span className="ac-item-name">{highlight(name)}</span>
            </li>
          ))}

          {/* Footer hint */}
          <li className="ac-footer" aria-hidden>
            {filtered.length} result{filtered.length !== 1 ? 's' : ''} — ↑↓ navigate · Enter/Tab to select
          </li>
        </ul>
      )}

      {/* No results hint */}
      {inputText.length >= 2 && !open && !isConfirmed && allNames.length > 0 && (
        <p className="ac-no-results">No matches for &ldquo;{inputText}&rdquo;</p>
      )}
    </div>
  );
}
