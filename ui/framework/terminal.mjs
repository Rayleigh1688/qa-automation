// Presentation only: preserve plain text for files, pipes and NO_COLOR.
export function styled(text, kind, stream = process.stdout) {
  if ('NO_COLOR' in process.env || process.env.TERM === 'dumb' || !stream.isTTY) return String(text);
  const codes = { PASS: '1;32', FAIL: '1;31', FAILED: '1;31', ERROR: '1;31', BLOCKED: '1;31',
    INTERRUPTED: '1;31', WARN: '1;33', SKIPPED: '1;33', NOT_RUN: '1;33', PATH: '4;36' };
  const code = codes[String(kind).toUpperCase()];
  return code ? `\x1b[${code}m${text}\x1b[0m` : String(text);
}
