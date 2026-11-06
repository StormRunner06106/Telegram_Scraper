// Edit these defaults to customize a fresh workspace. The Settings UI uses the
// same state and persists overrides in localStorage. "Restore defaults" clears
// those overrides, including saved column widths and sidebar visibility.
export const DEFAULT_STATE = Object.freeze({
  copyOnClick: true,
  copyOnDrag: false,
  sidebarVisible: true,
  selectedFile: "",
  columnWidths: Object.freeze({
    is_read: 96, link: 300, email: 240, telegramId: 190,
    blog: 240, years: 80, company: 200, nameMatch: 140,
  }),
});

const STORAGE_KEY = "gscraper.ui.v1";
const listeners = new Set();
export const clampWidth = (width) => Math.min(1200, Math.max(64, Math.round(Number(width)) || 180));

function normalize(value) {
  const next = {...DEFAULT_STATE, columnWidths: {...DEFAULT_STATE.columnWidths}};
  if (!value || typeof value !== "object") return next;
  for (const key of ["copyOnClick", "copyOnDrag", "sidebarVisible"]) {
    if (typeof value[key] === "boolean") next[key] = value[key];
  }
  if (typeof value.selectedFile === "string") next.selectedFile = value.selectedFile;
  if (value.columnWidths && typeof value.columnWidths === "object") {
    for (const [key, width] of Object.entries(value.columnWidths)) {
      if (Number.isFinite(width)) Object.defineProperty(next.columnWidths, key, {value: clampWidth(width), enumerable: true, writable: true, configurable: true});
    }
  }
  return next;
}

let saved;
try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { /* Storage may be disabled. */ }
let state = normalize(saved);

export function getState() {
  return {...state, columnWidths: {...state.columnWidths}};
}

export function updateState(patch) {
  state = normalize({...state, ...patch, columnWidths: {...state.columnWidths, ...patch.columnWidths}});
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* Keep session preferences. */ }
  listeners.forEach((listener) => listener(getState()));
}

export function resetState() {
  state = normalize({selectedFile: state.selectedFile});
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* Keep session preferences. */ }
  listeners.forEach((listener) => listener(getState()));
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function columnWidth(field) {
  const widths = state.columnWidths;
  return Object.hasOwn(widths, field) ? widths[field] : 180;
}
