import {getState, updateState, resetState, subscribe, columnWidth, clampWidth} from "./state.js";

const $ = (id) => document.getElementById(id);
let files = [];
let table = null;
let loadVersion = 0;
let fileVersion = 0;
let toastTimer;
let dragCell = null;
let selectionWasDragged = false;
let copyingFallback = false;
const rowReadActions = new WeakMap();
const columns = () => table ? ["is_read", ...table.fields.filter((field) => field !== "is_read")] : [];

function error(message) {
  $("error-message").textContent = message;
  $("error-banner").hidden = false;
}

function toast(message) {
  clearTimeout(toastTimer);
  $("toast").textContent = message;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 1800);
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"X-GScraper-UI": "1", ...(body === undefined ? {} : {"Content-Type": "application/json"})},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The request could not be completed.");
  return result;
}

async function copy(value, onCopied) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
    } else {
      const focused = document.activeElement;
      const selection = window.getSelection();
      const ranges = Array.from({length: selection.rangeCount}, (_, i) => selection.getRangeAt(i).cloneRange());
      const input = document.createElement("textarea");
      input.value = value;
      input.className = "sr-only";
      document.body.append(input);
      input.select();
      let copied;
      copyingFallback = true;
      try {
        copied = document.execCommand("copy");
      } finally {
        copyingFallback = false;
        input.remove();
        focused?.focus({preventScroll: true});
        selection.removeAllRanges();
        ranges.forEach((range) => selection.addRange(range));
      }
      if (!copied) throw new Error("Clipboard unavailable");
    }
    toast("Copied to clipboard");
  } catch {
    error("Could not copy. Allow clipboard access for this local page, or select text and use Ctrl+C / Cmd+C.");
    return;
  }
  onCopied?.();
}

function selectedRowReaders() {
  const selection = window.getSelection();
  const element = $("contacts");
  if (!selection || selection.isCollapsed || !element.contains(selection.anchorNode) || !element.contains(selection.focusNode)) return [];
  const ranges = Array.from({length: selection.rangeCount}, (_, index) => selection.getRangeAt(index));
  return Array.from(element.tBodies[0].rows)
    .filter((tr) => Array.from(tr.querySelectorAll("td[data-copy]")).some((cell) => ranges.some((range) => range.intersectsNode(cell))))
    .map((tr) => rowReadActions.get(tr))
    .filter(Boolean);
}

function renderFiles() {
  const query = $("file-search").value.toLowerCase();
  const list = $("file-list");
  list.replaceChildren();
  $("file-count").textContent = files.length;
  for (const file of files.filter((item) => item.name.toLowerCase().includes(query))) {
    const button = document.createElement("button");
    button.className = "file-button";
    button.classList.toggle("active", file.name === getState().selectedFile);
    button.setAttribute("aria-current", file.name === getState().selectedFile ? "page" : "false");
    button.title = file.name;
    const icon = document.createElement("span");
    icon.className = "file-icon";
    icon.textContent = "▤";
    const label = document.createElement("span");
    label.className = "file-label";
    const name = document.createElement("strong");
    name.textContent = file.name.split("/").pop();
    const detail = document.createElement("small");
    const folder = file.name.includes("/") ? file.name.slice(0, file.name.lastIndexOf("/")) : "Output";
    detail.textContent = `${folder} · ${Math.max(1, Math.round(file.size / 1024))} KB`;
    label.append(name, detail);
    button.append(icon, label);
    button.addEventListener("click", () => loadTable(file.name));
    list.append(button);
  }
  if (!list.childElementCount) {
    const message = document.createElement("p");
    message.className = "muted";
    message.textContent = query ? "No matching files." : "No CSV files yet. Refresh after a scrape.";
    list.append(message);
  }
}

async function refreshFiles() {
  const version = ++fileVersion;
  try {
    const result = await api("/api/files");
    if (version !== fileVersion) return;
    files = result.files;
    $("directory").textContent = result.directory;
    renderFiles();
    if (!files.some((file) => file.name === getState().selectedFile) || !table) {
      const selected = files.find((file) => file.name === getState().selectedFile) || files[0];
      if (selected) await loadTable(selected.name);
      else {
        ++loadVersion;
        table = null;
        updateState({selectedFile: ""});
        $("file-title").textContent = "Select a CSV";
        $("refresh-table").disabled = true;
        renderTable();
      }
    }
  } catch (failure) { error(failure.message); }
}

async function loadTable(name) {
  const version = ++loadVersion;
  table = null;
  updateState({selectedFile: name});
  renderFiles();
  $("file-title").textContent = name.split("/").pop();
  $("file-title").title = name;
  $("row-search").value = "";
  $("refresh-table").disabled = true;
  $("error-banner").hidden = true;
  renderTable("Loading CSV…");
  try {
    const result = await api(`/api/table?name=${encodeURIComponent(name)}`);
    if (version !== loadVersion) return;
    table = result;
    renderTable();
    renderColumnSettings();
  } catch (failure) {
    if (version === loadVersion) { error(failure.message); renderTable("Could not open this CSV. Refresh to try again."); }
  } finally {
    if (version === loadVersion) $("refresh-table").disabled = false;
  }
}

function linkFor(field, value) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (field === "telegramId" && /^@?[a-z\d_]+$/i.test(trimmed)) return `https://t.me/${trimmed.replace(/^@/, "")}`;
  if (field === "email" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return `mailto:${encodeURIComponent(trimmed).replace(/%40/g, "@")}`;
  let candidate = trimmed;
  if (["blog", "link"].includes(field) && /^(?:www\.)?[a-z\d.-]+\.[a-z]{2,}(?:[/:?#]|$)/i.test(candidate)) candidate = `https://${candidate}`;
  try {
    const url = new URL(candidate);
    if (["http:", "https:"].includes(url.protocol)) return url.href;
  } catch { /* Ordinary text, not a link. */ }
  return null;
}

function updateCounts() {
  const total = table?.rows.length || 0;
  const shown = $("contacts").tBodies[0].rows.length;
  $("row-count").textContent = shown === total ? total.toLocaleString() : `${shown.toLocaleString()} / ${total.toLocaleString()}`;
  $("read-count").textContent = (table?.rows.filter((row) => row.is_read).length || 0).toLocaleString();
}

function paintRead(row, tr, checkbox) {
  tr.classList.toggle("is-read", row.is_read);
  checkbox.checked = row.saving ? row.pendingRead : row.is_read;
  checkbox.disabled = Boolean(row.saving);
}

async function setRead(row, value, tr, checkbox, source) {
  if (row.saving) {
    row.nextRead = value;
    return;
  }
  if (row.is_read === value) { paintRead(row, tr, checkbox); return; }
  row.saving = true;
  row.pendingRead = value;
  paintRead(row, tr, checkbox);
  try {
    await api("/api/read", {name: source.name, index: row.index, key: row.key, is_read: value});
    row.is_read = value;
    row.values.is_read = String(value);
    toast(value ? "Marked as read · Saved to CSV" : "Marked as unread · Saved to CSV");
  } catch (failure) { error(`Could not save ${source.name}: ${failure.message}`); }
  finally {
    row.saving = false;
    paintRead(row, tr, checkbox);
    if (table === source) {
      // Search may have rebuilt the row while the save was in flight.
      const current = $("contacts").tBodies[0].querySelector(`tr[data-index="${row.index}"]`);
      if (current) paintRead(row, current, current.querySelector("input"));
      updateCounts();
    }
    const nextRead = row.nextRead;
    delete row.nextRead;
    if (typeof nextRead === "boolean" && nextRead !== row.is_read) setRead(row, nextRead, tr, checkbox, source);
  }
}

function renderTable(message) {
  const element = $("contacts");
  const group = element.querySelector("colgroup");
  const head = element.tHead;
  const body = element.tBodies[0];
  group.replaceChildren(); head.replaceChildren(); body.replaceChildren();
  if (!table) {
    element.hidden = true;
    $("empty-state").hidden = false;
    $("empty-state").querySelector("h2").textContent = message || "Your contacts, in one place.";
    $("empty-state").querySelector("p").textContent = message ? "" : "Select a CSV from the sidebar to start reviewing.";
    updateCounts();
    return;
  }
  element.hidden = false;
  const source = table;
  const headerRow = document.createElement("tr");
  for (const field of columns()) {
    const col = document.createElement("col");
    col.dataset.field = field;
    group.append(col);
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = field;
    th.title = field;
    const handle = document.createElement("span");
    handle.className = "resize-handle";
    handle.tabIndex = 0;
    handle.setAttribute("role", "separator");
    handle.setAttribute("aria-orientation", "vertical");
    handle.setAttribute("aria-label", `Resize ${field}`);
    handle.setAttribute("aria-valuemin", "64");
    handle.setAttribute("aria-valuemax", "1200");
    handle.dataset.field = field;
    handle.addEventListener("pointerdown", (event) => startResize(event, field));
    handle.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      updateState({columnWidths: {[field]: columnWidth(field) + (event.key === "ArrowRight" ? 10 : -10)}});
    });
    th.append(handle);
    headerRow.append(th);
  }
  head.append(headerRow);
  const query = $("row-search").value.toLocaleLowerCase();
  const fragment = document.createDocumentFragment();
  for (const row of table.rows) {
    if (query && !Object.values(row.values).some((value) => value.toLocaleLowerCase().includes(query))) continue;
    const tr = document.createElement("tr");
    tr.dataset.index = row.index;
    const readCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.setAttribute("aria-label", `Mark row ${row.index + 1} as read`);
    const markRead = () => setRead(row, true, tr, checkbox, source);
    rowReadActions.set(tr, markRead);
    checkbox.addEventListener("change", () => setRead(row, checkbox.checked, tr, checkbox, source));
    paintRead(row, tr, checkbox);
    readCell.append(checkbox);
    tr.append(readCell);
    for (const field of columns().slice(1)) {
      const td = document.createElement("td");
      const value = row.values[field] || "";
      td.title = value;
      td.dataset.copy = value;
      td.tabIndex = 0;
      const href = linkFor(field, value);
      if (href) {
        const anchor = document.createElement("a");
        anchor.href = href;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.draggable = false;
        anchor.textContent = value.replace(/[\r\n\t]+/g, " ");
        const openLink = (event) => {
          if (selectionWasDragged && event.detail !== 0) { event.preventDefault(); return; }
          // Opening with Ctrl/Cmd, middle-click or keyboard also records a read.
          if (event.type === "auxclick" && event.button !== 1) return;
          markRead();
          if (event.type === "auxclick" && getState().copyOnClick) copy(value, markRead);
        };
        anchor.addEventListener("click", openLink);
        anchor.addEventListener("auxclick", openLink);
        // Browser context-menu actions do not dispatch an open event. Interaction
        // with that link still counts as read (including "Open in new tab").
        anchor.addEventListener("contextmenu", markRead);
        td.append(anchor);
      } else td.textContent = value.replace(/[\r\n\t]+/g, " ");
      td.addEventListener("click", (event) => {
        if (selectionWasDragged && event.detail !== 0) return;
        if (getState().copyOnClick) copy(value, markRead);
      });
      td.addEventListener("keydown", (event) => {
        if (event.target === td && ["Enter", " "].includes(event.key)) {
          event.preventDefault();
          if (getState().copyOnClick) copy(value, markRead);
        }
      });
      tr.append(td);
    }
    fragment.append(tr);
  }
  body.append(fragment);
  $("empty-state").hidden = Boolean(body.rows.length);
  $("empty-state").querySelector("h2").textContent = query ? "No matching rows" : "This CSV has no rows yet";
  $("empty-state").querySelector("p").textContent = query ? "Try a different search." : "Refresh after new contacts are saved.";
  applyWidths();
  updateCounts();
}

function applyWidths(override = {}) {
  let total = 0;
  for (const col of $("contacts").querySelectorAll("col")) {
    const width = Object.hasOwn(override, col.dataset.field) ? override[col.dataset.field] : columnWidth(col.dataset.field);
    col.style.width = `${width}px`;
    total += width;
  }
  $("contacts").style.width = `${total}px`;
  for (const handle of document.querySelectorAll(".resize-handle")) handle.setAttribute("aria-valuenow", Object.hasOwn(override, handle.dataset.field) ? override[handle.dataset.field] : columnWidth(handle.dataset.field));
}

function startResize(event, field) {
  if (event.button !== 0) return;
  event.preventDefault();
  const handle = event.currentTarget;
  const start = event.clientX;
  const initial = columnWidth(field);
  let width = initial;
  handle.setPointerCapture(event.pointerId);
  document.body.classList.add("resizing");
  const move = (moveEvent) => { width = clampWidth(initial + moveEvent.clientX - start); applyWidths({[field]: width}); };
  const finish = () => {
    handle.removeEventListener("pointermove", move);
    handle.removeEventListener("pointerup", finish);
    handle.removeEventListener("lostpointercapture", finish);
    document.body.classList.remove("resizing");
    updateState({columnWidths: {[field]: width}});
  };
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", finish);
  handle.addEventListener("lostpointercapture", finish);
}

function renderColumnSettings() {
  $("column-settings").replaceChildren();
  for (const field of columns()) {
    const label = document.createElement("label");
    label.className = "column-setting";
    const text = document.createElement("span");
    text.textContent = field;
    text.title = field;
    const input = document.createElement("input");
    input.type = "number";
    input.min = 64; input.max = 1200; input.step = 1;
    input.value = columnWidth(field);
    input.dataset.widthField = field;
    input.setAttribute("aria-label", `${field} column width`);
    input.addEventListener("change", () => updateState({columnWidths: {[field]: clampWidth(input.value)}}));
    label.append(text, input);
    $("column-settings").append(label);
  }
}

function applyState(state) {
  $("sidebar").hidden = !state.sidebarVisible;
  $("toggle-sidebar").setAttribute("aria-expanded", String(state.sidebarVisible));
  $("copy-on-click").checked = state.copyOnClick;
  $("copy-on-drag").checked = state.copyOnDrag;
  $("show-sidebar").checked = state.sidebarVisible;
  document.body.classList.toggle("no-click-copy", !state.copyOnClick);
  const hints = [];
  if (state.copyOnClick) hints.push("Click a cell to copy");
  if (state.copyOnDrag) hints.push("Drag to select and copy");
  hints.push("Copy text or open a link to mark as read");
  $("copy-hint").textContent = hints.join(" · ");
  applyWidths();
  for (const input of document.querySelectorAll("[data-width-field]")) input.value = columnWidth(input.dataset.widthField);
}

$("contacts").addEventListener("pointerdown", (event) => {
  dragCell = event.button === 0 ? event.target.closest("td[data-copy]") : null;
  selectionWasDragged = false;
});
document.addEventListener("pointerup", () => {
  if (!dragCell) return;
  const selection = window.getSelection();
  selectionWasDragged = Boolean(selection && !selection.isCollapsed && $("contacts").contains(selection.anchorNode) && $("contacts").contains(selection.focusNode));
  if (selectionWasDragged && getState().copyOnDrag) {
    const readers = selectedRowReaders();
    copy(selection.toString(), () => readers.forEach((markRead) => markRead()));
  }
  dragCell = null;
});
document.addEventListener("copy", (event) => {
  if (copyingFallback || !event.isTrusted) return;
  const readers = selectedRowReaders();
  // Preserve native keyboard/context-menu copying. Wait until other handlers
  // have had the opportunity to cancel it; selection alone never marks a row.
  setTimeout(() => {
    if (!event.defaultPrevented) readers.forEach((markRead) => markRead());
  }, 0);
});
$("toggle-sidebar").addEventListener("click", () => updateState({sidebarVisible: !getState().sidebarVisible}));
$("refresh-files").addEventListener("click", refreshFiles);
$("refresh-table").addEventListener("click", () => loadTable(getState().selectedFile));
$("file-search").addEventListener("input", renderFiles);
$("row-search").addEventListener("input", () => renderTable());
$("dismiss-error").addEventListener("click", () => { $("error-banner").hidden = true; });
$("open-settings").addEventListener("click", () => { renderColumnSettings(); $("settings-dialog").showModal(); });
for (const id of ["close-settings", "done-settings"]) $(id).addEventListener("click", () => $("settings-dialog").close());
$("copy-on-click").addEventListener("change", (event) => updateState({copyOnClick: event.target.checked}));
$("copy-on-drag").addEventListener("change", (event) => updateState({copyOnDrag: event.target.checked}));
$("show-sidebar").addEventListener("change", (event) => updateState({sidebarVisible: event.target.checked}));
$("reset-settings").addEventListener("click", resetState);
subscribe(applyState);
applyState(getState());
refreshFiles();
