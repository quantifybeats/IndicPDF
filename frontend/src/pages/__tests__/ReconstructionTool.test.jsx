import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ReconstructionTool, { validateFiles } from '../ReconstructionTool';

vi.mock('axios');

describe('validateFiles', () => {
  it('rejects oversized files client-side before upload', () => {
    const big = new File([''], 'big.pdf', { type: 'application/pdf' });
    Object.defineProperty(big, 'size', { value: 26 * 1024 * 1024 });
    const { accepted, rejected } = validateFiles([big]);
    expect(accepted).toHaveLength(0);
    expect(rejected[0].reason).toMatch(/25 MB/);
  });

  it('rejects unsupported extensions and accepts supported ones', () => {
    const exe = new File(['x'], 'tool.exe');
    const pdf = new File(['x'], 'శాసనం.pdf');
    const { accepted, rejected } = validateFiles([exe, pdf]);
    expect(accepted.map((f) => f.name)).toEqual(['శాసనం.pdf']);
    expect(rejected[0].file.name).toBe('tool.exe');
  });

  it('caps at 10 files', () => {
    const files = Array.from({ length: 12 }, (_, i) => new File(['x'], `f${i}.pdf`));
    const { accepted, rejected } = validateFiles(files);
    expect(accepted).toHaveLength(10);
    expect(rejected).toHaveLength(2);
  });
});

describe('ReconstructionTool', () => {
  it('renders dropzone and language selector', () => {
    render(
      <MemoryRouter>
        <ReconstructionTool />
      </MemoryRouter>
    );
    expect(screen.getByText(/Document Reconstruction/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/language/i)).toBeInTheDocument();
  });
});
