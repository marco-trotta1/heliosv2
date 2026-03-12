const state = {
  files: [],
  filteredFiles: [],
  activeFile: null,
};

const fileList = document.querySelector("#file-list");
const fileSearch = document.querySelector("#file-search");
const activeFileLabel = document.querySelector("#active-file");
const codeContent = document.querySelector("#code-content");
const copyButton = document.querySelector("#copy-button");

async function loadManifest() {
  const response = await fetch("repo-manifest.json");
  if (!response.ok) {
    throw new Error("Unable to load repository manifest.");
  }
  return response.json();
}

async function loadFile(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Unable to load ${path}`);
  }
  return response.text();
}

function renderFileList() {
  fileList.innerHTML = "";
  for (const path of state.filteredFiles) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `file-button${path === state.activeFile ? " active" : ""}`;
    button.textContent = path;
    button.addEventListener("click", () => showFile(path));
    fileList.appendChild(button);
  }
}

function applyFilter() {
  const query = fileSearch.value.trim().toLowerCase();
  state.filteredFiles = state.files.filter((path) => path.toLowerCase().includes(query));
  renderFileList();
}

async function showFile(path) {
  state.activeFile = path;
  renderFileList();
  activeFileLabel.textContent = path;
  codeContent.textContent = "Loading file…";
  try {
    const contents = await loadFile(path);
    codeContent.textContent = contents;
  } catch (error) {
    codeContent.textContent = String(error);
  }
}

copyButton.addEventListener("click", async () => {
  if (!state.activeFile) {
    return;
  }
  try {
    await navigator.clipboard.writeText(codeContent.textContent);
    copyButton.textContent = "Copied";
    window.setTimeout(() => {
      copyButton.textContent = "Copy File";
    }, 1200);
  } catch (error) {
    copyButton.textContent = "Copy Failed";
    window.setTimeout(() => {
      copyButton.textContent = "Copy File";
    }, 1200);
  }
});

fileSearch.addEventListener("input", applyFilter);

async function init() {
  try {
    const manifest = await loadManifest();
    state.files = manifest.files;
    state.filteredFiles = [...state.files];
    renderFileList();
    const defaultFile = state.files.includes("README.md") ? "README.md" : state.files[0];
    if (defaultFile) {
      await showFile(defaultFile);
    }
  } catch (error) {
    activeFileLabel.textContent = "Viewer Error";
    codeContent.textContent = String(error);
  }
}

init();
