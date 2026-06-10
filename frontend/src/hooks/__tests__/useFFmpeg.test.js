import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFFmpegInstance = {
  load: vi.fn().mockResolvedValue(undefined),
  on: vi.fn(),
  writeFile: vi.fn().mockResolvedValue(undefined),
  exec: vi.fn().mockResolvedValue(undefined),
  readFile: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3])),
  deleteFile: vi.fn().mockResolvedValue(undefined),
};

vi.mock('@ffmpeg/ffmpeg', () => ({
  FFmpeg: vi.fn().mockImplementation(function () {
    return mockFFmpegInstance;
  }),
}));

vi.mock('@ffmpeg/util', () => ({
  fetchFile: vi.fn().mockResolvedValue(new Uint8Array()),
  toBlobURL: vi.fn(url => Promise.resolve(url)),
}));

describe('useFFmpeg', () => {
  beforeEach(() => vi.clearAllMocks());

  it('starts with loaded=false and loading=false', async () => {
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    expect(result.current.loaded).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  it('sets loaded=true after load()', async () => {
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    await act(async () => { await result.current.load(); });
    expect(result.current.loaded).toBe(true);
  });

  it('does not reload if already loaded', async () => {
    const { FFmpeg } = await import('@ffmpeg/ffmpeg');
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    await act(async () => { await result.current.load(); });
    await act(async () => { await result.current.load(); });
    const instance = FFmpeg.mock.results[0].value;
    expect(instance.load).toHaveBeenCalledTimes(1);
  });

  it('convertFile returns a Blob', async () => {
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    await act(async () => { await result.current.load(); });
    const mockFile = new File(['data'], 'test.mp4', { type: 'video/mp4' });
    let blob;
    await act(async () => { blob = await result.current.convertFile(mockFile, 'webm'); });
    expect(blob).toBeInstanceOf(Blob);
  });
});
