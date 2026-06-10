/**
 * Validates files before upload.
 * Returns { valid, errors } where errors = [{ name, reason }]
 */
const MAX_MB = 25;
const MAX_BYTES = MAX_MB * 1024 * 1024;

export function validateFiles(files, acceptedExts = null) {
  const valid = [];
  const errors = [];
  const seen = new Set();

  for (const file of files) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (seen.has(file.name)) {
      errors.push({ name: file.name, reason: 'Duplicate file' });
      continue;
    }
    seen.add(file.name);

    if (acceptedExts && !acceptedExts.includes(ext)) {
      errors.push({ name: file.name, reason: `Unsupported type (${ext})` });
      continue;
    }

    if (file.size > MAX_BYTES) {
      errors.push({ name: file.name, reason: `Too large (${(file.size / 1024 / 1024).toFixed(1)} MB — max ${MAX_MB} MB)` });
      continue;
    }

    if (file.size === 0) {
      errors.push({ name: file.name, reason: 'Empty file' });
      continue;
    }

    valid.push(file);
  }

  return { valid, errors };
}

/** Recursively collect files from a FileSystemEntry (for folder drops) */
export async function readFolderEntries(dataTransferItems) {
  const files = [];

  async function readEntry(entry) {
    if (entry.isFile) {
      await new Promise(res => entry.file(f => { files.push(f); res(); }));
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      await new Promise(res => {
        reader.readEntries(async entries => {
          for (const e of entries) await readEntry(e);
          res();
        });
      });
    }
  }

  for (const item of dataTransferItems) {
    const entry = item.webkitGetAsEntry?.();
    if (entry) await readEntry(entry);
  }

  return files;
}
