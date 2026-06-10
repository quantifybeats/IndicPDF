import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FileActionRow from '../FileActionRow.jsx';

const baseProps = {
  file: new File(['data'], 'video.mp4', { type: 'video/mp4' }),
  outputFormat: '', status: 'idle', downloadUrl: null,
  formats: ['mp4', 'webm', 'avi'],
  onFormatChange: vi.fn(), onRemove: vi.fn(),
};

describe('FileActionRow', () => {
  it('renders filename', () => {
    render(<FileActionRow {...baseProps} />);
    expect(screen.getByText('video.mp4')).toBeInTheDocument();
  });

  it('shows spinner when converting', () => {
    render(<FileActionRow {...baseProps} status="converting" />);
    expect(screen.getByTestId('converting-spinner')).toBeInTheDocument();
  });

  it('shows done badge', () => {
    render(<FileActionRow {...baseProps} status="done" downloadUrl="blob:test" />);
    expect(screen.getByText('✓ Done')).toBeInTheDocument();
  });

  it('shows download link when done', () => {
    render(<FileActionRow {...baseProps} status="done" downloadUrl="blob:test" />);
    expect(screen.getByRole('link', { name: /download/i })).toBeInTheDocument();
  });

  it('shows error badge', () => {
    render(<FileActionRow {...baseProps} status="error" />);
    expect(screen.getByText('✗ Error')).toBeInTheDocument();
  });
});
