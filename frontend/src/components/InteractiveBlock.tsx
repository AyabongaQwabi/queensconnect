import { useState, FormEvent } from 'react';
import type { InteractiveSpec } from '../App';

type InteractiveBlockProps = {
  spec: InteractiveSpec;
  onSelect: (value: string) => void;
  disabled?: boolean;
};

export function InteractiveBlock({
  spec,
  onSelect,
  disabled = false,
}: InteractiveBlockProps) {
  const [dropdownValue, setDropdownValue] = useState('');
  const [radioValue, setRadioValue] = useState('');
  const [checkboxValues, setCheckboxValues] = useState<Set<string>>(new Set());

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (spec.type === 'dropdown' && dropdownValue) {
      onSelect(dropdownValue);
      setDropdownValue('');
    }
    if (spec.type === 'radio' && radioValue) {
      onSelect(radioValue);
      setRadioValue('');
    }
    if (spec.type === 'checkboxes' && checkboxValues.size > 0) {
      onSelect(Array.from(checkboxValues).join(', '));
      setCheckboxValues(new Set());
    }
  };

  if (spec.type === 'link') {
    return (
      <div className='mt-3 flex flex-wrap gap-2'>
        {spec.options.map((opt) => (
          <a
            key={opt.value}
            href={opt.value}
            target='_blank'
            rel='noopener noreferrer'
            className='rounded-xl border border-[#7c3aed] bg-[#ede9fe] text-[#5b21b6] hover:bg-[#ddd6fe] disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium transition-colors no-underline inline-block'
          >
            {opt.label}
          </a>
        ))}
      </div>
    );
  }

  if (spec.type === 'buttons') {
    return (
      <div className='mt-3 flex flex-wrap gap-2'>
        {spec.label && (
          <p className='w-full text-sm font-medium text-gray-700 mb-1'>
            {spec.label}
          </p>
        )}
        {spec.options.map((opt) => (
          <button
            key={opt.value}
            type='button'
            disabled={disabled}
            onClick={() => onSelect(opt.value)}
            className='rounded-xl border border-[#7c3aed] bg-[#ede9fe] text-[#5b21b6] hover:bg-[#ddd6fe] disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium transition-colors'
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  if (spec.type === 'dropdown') {
    return (
      <form onSubmit={handleSubmit} className='mt-3 space-y-2'>
        {spec.label && (
          <label className='block text-sm font-medium text-gray-700'>
            {spec.label}
          </label>
        )}
        <div className='flex flex-wrap gap-2 items-end'>
          <select
            value={dropdownValue}
            onChange={(e) => setDropdownValue(e.target.value)}
            disabled={disabled}
            className='rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-2 focus:ring-[#ede9fe] min-w-[140px]'
            aria-label={spec.label ?? spec.name}
          >
            <option value=''>Select…</option>
            {spec.options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            type='submit'
            disabled={disabled || !dropdownValue}
            className='rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-2 text-sm transition-colors'
          >
            {spec.submitLabel ?? 'Continue'}
          </button>
        </div>
      </form>
    );
  }

  if (spec.type === 'radio') {
    return (
      <form onSubmit={handleSubmit} className='mt-3 space-y-2'>
        {spec.label && (
          <p className='text-sm font-medium text-gray-700'>{spec.label}</p>
        )}
        <div className='space-y-1.5'>
          {spec.options.map((opt) => (
            <label
              key={opt.value}
              className='flex items-center gap-2 cursor-pointer'
            >
              <input
                type='radio'
                name={spec.name}
                value={opt.value}
                checked={radioValue === opt.value}
                onChange={() => setRadioValue(opt.value)}
                disabled={disabled}
                className='text-[#7c3aed] focus:ring-[#7c3aed]'
              />
              <span className='text-sm text-gray-800'>{opt.label}</span>
            </label>
          ))}
        </div>
        <button
          type='submit'
          disabled={disabled || !radioValue}
          className='mt-2 rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-2 text-sm transition-colors'
        >
          {spec.submitLabel ?? 'Continue'}
        </button>
      </form>
    );
  }

  if (spec.type === 'checkboxes') {
    const toggle = (value: string) => {
      setCheckboxValues((prev) => {
        const next = new Set(prev);
        if (next.has(value)) next.delete(value);
        else next.add(value);
        return next;
      });
    };
    return (
      <form onSubmit={handleSubmit} className='mt-3 space-y-2'>
        {spec.label && (
          <p className='text-sm font-medium text-gray-700'>{spec.label}</p>
        )}
        <div className='space-y-1.5'>
          {spec.options.map((opt) => (
            <label
              key={opt.value}
              className='flex items-center gap-2 cursor-pointer'
            >
              <input
                type='checkbox'
                checked={checkboxValues.has(opt.value)}
                onChange={() => toggle(opt.value)}
                disabled={disabled}
                className='rounded text-[#7c3aed] focus:ring-[#7c3aed]'
              />
              <span className='text-sm text-gray-800'>{opt.label}</span>
            </label>
          ))}
        </div>
        <button
          type='submit'
          disabled={disabled || checkboxValues.size === 0}
          className='mt-2 rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-2 text-sm transition-colors'
        >
          {spec.submitLabel ?? 'Continue'}
        </button>
      </form>
    );
  }

  return null;
}
