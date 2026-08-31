import path from "node:path";

export const reuseP0Auth = process.env.CLIENT_REUSE_P0_AUTH === "true";
export const p0StorageStatePath = path.resolve(
  process.env.CLIENT_P0_STORAGE_STATE_PATH || "ui/results/client-p0-storage-state.json",
);
