function readLength(bytes, state, additional) {
  if (additional < 24) return additional;
  const sizes = { 24: 1, 25: 2, 26: 4, 27: 8 };
  const size = sizes[additional];
  if (!size) throw new Error(`unsupported CBOR length: ${additional}`);
  let value = 0;
  for (let index = 0; index < size; index += 1) {
    value = (value * 256) + bytes[state.offset];
    state.offset += 1;
  }
  return value;
}

function decodeOne(bytes, state) {
  if (state.offset >= bytes.length) throw new Error("unexpected end of CBOR");
  const initial = bytes[state.offset];
  state.offset += 1;
  const major = initial >> 5;
  const additional = initial & 0x1f;

  if (major === 7) {
    if (additional === 20) return false;
    if (additional === 21) return true;
    if (additional === 22 || additional === 23) return null;
    if (additional === 26) {
      const value = new DataView(bytes.buffer, bytes.byteOffset + state.offset, 4).getFloat32(0);
      state.offset += 4;
      return value;
    }
    if (additional === 27) {
      const value = new DataView(bytes.buffer, bytes.byteOffset + state.offset, 8).getFloat64(0);
      state.offset += 8;
      return value;
    }
    throw new Error(`unsupported CBOR simple value: ${additional}`);
  }

  const length = readLength(bytes, state, additional);
  if (major === 0) return length;
  if (major === 1) return -1 - length;
  if (major === 2) {
    const value = bytes.slice(state.offset, state.offset + length);
    state.offset += length;
    return value;
  }
  if (major === 3) {
    const value = new TextDecoder().decode(bytes.slice(state.offset, state.offset + length));
    state.offset += length;
    return value;
  }
  if (major === 4) {
    return Array.from({ length }, () => decodeOne(bytes, state));
  }
  if (major === 5) {
    const value = {};
    for (let index = 0; index < length; index += 1) {
      value[String(decodeOne(bytes, state))] = decodeOne(bytes, state);
    }
    return value;
  }
  throw new Error(`unsupported CBOR major type: ${major}`);
}

export function decodeCbor(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  return decodeOne(bytes, { offset: 0 });
}
