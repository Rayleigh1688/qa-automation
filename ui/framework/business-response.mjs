import { decodeCbor } from './cbor-decoder.mjs';

// Content-Type is unreliable in FAT/UAT; prefer JSON when the bytes are JSON.
export function decodeBusinessBody(bytes) {
  const buffer = Buffer.from(bytes);
  try { return JSON.parse(buffer.toString('utf8')); } catch { /* CBOR fallback */ }
  return decodeCbor(buffer);
}

export async function requireBusinessResponse(response) {
  const body = decodeBusinessBody(await response.body());
  if (!response.ok() || body?.status !== true) {
    throw new Error(`business response rejected: ${new URL(response.url()).pathname} HTTP ${response.status()}, status=${String(body?.status)}`);
  }
  return body;
}

export function readBusinessRequest(request) {
  if (request.method() === 'GET') return Object.fromEntries(new URL(request.url()).searchParams);
  return decodeBusinessBody(request.postDataBuffer());
}
