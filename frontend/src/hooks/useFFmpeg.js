import { useState, useRef } from 'react';
import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';

const FFMPEG_CORE_URL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/umd';

const MIME_TYPES = {
  mp4: 'video/mp4', webm: 'video/webm', avi: 'video/x-msvideo',
  mov: 'video/quicktime', mkv: 'video/x-matroska',
  mp3: 'audio/mpeg', wav: 'audio/wav', flac: 'audio/flac',
  aac: 'audio/aac', ogg: 'audio/ogg',
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
  gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp',
};

export function useFFmpeg() {
  const ffmpegRef = useRef(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const load = async () => {
    if (loaded) return;
    setLoading(true);
    setProgress(0);
    if (!ffmpegRef.current) ffmpegRef.current = new FFmpeg();
    const ffmpeg = ffmpegRef.current;
    ffmpeg.on('progress', ({ progress: p }) => setProgress(Math.round(p * 100)));
    await ffmpeg.load({
      coreURL: await toBlobURL(`${FFMPEG_CORE_URL}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${FFMPEG_CORE_URL}/ffmpeg-core.wasm`, 'application/wasm'),
    });
    setLoaded(true);
    setLoading(false);
  };

  const convertFile = async (file, outputFormat) => {
    const ffmpeg = ffmpegRef.current;
    const inputExt = file.name.split('.').pop().toLowerCase();
    const inputName = `input.${inputExt}`;
    const outputName = `output.${outputFormat}`;
    await ffmpeg.writeFile(inputName, await fetchFile(file));
    await ffmpeg.exec(['-i', inputName, outputName]);
    const data = await ffmpeg.readFile(outputName);
    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);
    const mimeType = MIME_TYPES[outputFormat] || 'application/octet-stream';
    return new Blob([data.buffer], { type: mimeType });
  };

  return { loaded, loading, progress, load, convertFile };
}
