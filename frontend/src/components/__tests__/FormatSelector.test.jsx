import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FormatSelector from '../FormatSelector.jsx';

const formats = ['mp4', 'webm', 'avi'];

describe('FormatSelector', () => {
  it('renders a select with all format options', () => {
    render(<FormatSelector formats={formats} value="" onChange={() => {}} disabled={false} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    formats.forEach(f => expect(screen.getByText(f.toUpperCase())).toBeInTheDocument());
  });

  it('calls onChange with selected value', () => {
    const onChange = vi.fn();
    render(<FormatSelector formats={formats} value="" onChange={onChange} disabled={false} />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'webm' } });
    expect(onChange).toHaveBeenCalledWith('webm');
  });

  it('is disabled when disabled prop is true', () => {
    render(<FormatSelector formats={formats} value="mp4" onChange={() => {}} disabled={true} />);
    expect(screen.getByRole('combobox')).toBeDisabled();
  });
});
