import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FormatSelector from '../FormatSelector.jsx';

const formats = ['mp4', 'webm', 'avi'];

describe('FormatSelector', () => {
  it('renders trigger button and opens popover on click', () => {
    render(<FormatSelector formats={formats} value="" onChange={() => {}} disabled={false} />);
    
    // Checks that the initial trigger button renders
    const trigger = screen.getByRole('button');
    expect(trigger).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/search/i)).not.toBeInTheDocument();

    // Click to open popover
    fireEvent.click(trigger);
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    
    // Shows category and matching formats
    expect(screen.getAllByText('Video')[0]).toBeInTheDocument();
  });

  it('calls onChange with selected value when an allowed format is clicked', () => {
    const onChange = vi.fn();
    render(<FormatSelector formats={formats} value="" onChange={onChange} disabled={false} />);
    
    // Open dropdown
    fireEvent.click(screen.getByRole('button'));
    
    // Find and click the 'WEBM' format button (which is in formats allowed list)
    const webmButton = screen.getByRole('button', { name: 'WEBM' });
    expect(webmButton).toBeInTheDocument();
    
    fireEvent.click(webmButton);
    expect(onChange).toHaveBeenCalledWith('webm');
  });

  it('is disabled when disabled prop is true', () => {
    render(<FormatSelector formats={formats} value="mp4" onChange={() => {}} disabled={true} />);
    const trigger = screen.getByRole('button');
    expect(trigger).toBeDisabled();
  });
});
