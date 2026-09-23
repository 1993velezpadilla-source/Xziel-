const $ = (id) => document.getElementById(id);
const state = {
  files: [],
  job: null,
  source: null,
  logs: [],
  currentStage: "queued"
};

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 2600);
}

function setFiles(files) {
  state.files = Array.from(files || []);
  $("fileCount").textContent = state.files.length;
  const thumbs = $("thumbs");
  thumbs.replaceChildren();
  state.files.slice(0, 20).forEach((file) => {
    const img = document.createElement("img");
    img.className = "thumb";
    img.alt = file.name;
    img.src = URL.createObjectURL(file);
    thumbs.appendChild(img);
  });
}

function setProgress(stage, progress, status) {
  state.currentStage = stage || state.currentStage;
  $("stageLabel").textContent = (stage || "idle").replaceAll("_", " ");
  $("progressText").textContent = `${progress ?? 0}%`;
  $("progressBar").style.width = `${progress ?? 0}%`;
  $("jobStatus").textContent = (status || "idle").toUpperCase();

  const order = ["planning","viewforge","generating","judge","refinement","mesh_doctor","retopo","gameprep","portable","qa"];
  const current = order.indexOf(stage);
  document.querySelectorAll("#stageStrip span").forEach((el) => {
    const idx = order.indexOf(el.dataset.stage);
    el.classList.toggle("active", idx === current);
    el.classList.toggle("done", current > idx || stage === "complete");
  });
}

function appendLog(line) {
  if (!line) return;
  state.logs.push(line);
  if (state.logs.length > 500) state.logs.shift();
  $("log").textContent = state.logs.join("\n");
  $("log").scrollTop = $("log").scrollHeight;
}

function showModel(url, label, meta="") {
  if (!url) return;
  const viewer = $("viewer");
  viewer.src = url + (url.includes("?") ? "&" : "?") + "v=" + Date.now();
  $("emptyState").style.display = "none";
  $("modelLabel").textContent = label || "HAYUYA model";
  $("modelMeta").textContent = meta || "Interactive GLB";
}

function renderCandidates(job) {
  const list = $("candidates");
  const candidates = job?.candidates || [];
  $("candidateCount").textContent = candidates.length;
  list.replaceChildren();
  if (!candidates.length) {
    const empty = document.createElement("div");
    empty.className = "muted-card";
    empty.textContent = "Candidates will appear here.";
    list.appendChild(empty);
    return;
  }
  candidates.forEach((candidate) => {
    const card = document.createElement("div");
    card.className = "candidate-card";
    const row = document.createElement("div");
    row.className = "card-row";
    const title = document.createElement("div");
    title.className = "card-title";
    title.textContent = candidate.label;
    if (candidate.is_champion) {
      const crown = document.createElement("span");
      crown.className = "crown";
      crown.textContent = "  👑";
      title.appendChild(crown);
    }
    const score = document.createElement("div");
    score.className = "score";
    score.textContent = candidate.score == null ? "—" : candidate.score.toFixed(2);
    row.append(title, score);
    card.appendChild(row);

    const sub = document.createElement("div");
    sub.className = "card-sub";
    sub.textContent = candidate.url ? "Tap to inspect in 3D" : "Mesh path captured";
    card.appendChild(sub);
    if (candidate.url) {
      card.addEventListener("click", () => showModel(candidate.url, candidate.label, "Live Arena candidate"));
    }
    list.appendChild(card);
  });
}

function renderJobs(jobs) {
  const list = $("jobs");
  list.replaceChildren();
  if (!jobs.length) {
    const empty = document.createElement("div");
    empty.className = "muted-card";
    empty.textContent = "No jobs in this Studio session.";
    list.appendChild(empty);
    return;
  }
  jobs.slice(0, 10).forEach((job) => {
    const card = document.createElement("div");
    card.className = "job-card";
    card.innerHTML = `<div class="card-row"><div class="card-title">${job.id}</div><div class="score">${job.progress}%</div></div><div class="card-sub">${job.profile} · ${job.stage} · ${job.status}</div>`;
    card.addEventListener("click", () => attachJob(job.id));
    list.appendChild(card);
  });
}

async function refreshJobs() {
  try {
    const res = await fetch("/api/jobs", {cache:"no-store"});
    renderJobs(await res.json());
  } catch (err) {
    appendLog("Studio API error: " + err);
  }
}

async function refreshJob() {
  if (!state.job?.id) return;
  const res = await fetch(`/api/jobs/${state.job.id}`, {cache:"no-store"});
  if (!res.ok) return;
  state.job = await res.json();
  setProgress(state.job.stage, state.job.progress, state.job.status);
  renderCandidates(state.job);
  if (state.job.final_model_url) {
    showModel(state.job.final_model_url, "Final Champion", `${state.job.profile} · ${state.job.portable_target}`);
  }
}

function handleEvent(event) {
  if (event.kind === "log") appendLog(event.line);
  if (event.kind === "stage") setProgress(event.stage, event.progress, event.status);
  if (event.kind === "candidate") refreshJob();
  if (event.kind === "champion") {
    appendLog(`👑 Champion: ${event.label} score=${event.score}`);
    refreshJob();
  }
  if (event.kind === "model" && event.url) {
    showModel(event.url, "Final Champion", "HAYUYA final");
  }
  if (event.kind === "error") toast(event.message || "Job failed");
}

async function attachJob(jobId) {
  if (state.source) state.source.close();
  state.logs = [];
  $("log").textContent = "";
  const res = await fetch(`/api/jobs/${jobId}`, {cache:"no-store"});
  if (!res.ok) return;
  state.job = await res.json();
  setProgress(state.job.stage, state.job.progress, state.job.status);
  renderCandidates(state.job);
  if (state.job.final_model_url) showModel(state.job.final_model_url, "Final Champion");

  const source = new EventSource(`/api/jobs/${jobId}/events`);
  state.source = source;
  source.onmessage = (msg) => {
    try { handleEvent(JSON.parse(msg.data)); } catch {}
  };
  source.onerror = () => {
    if (state.job?.status === "complete" || state.job?.status === "failed") source.close();
  };
  toast("Attached to " + jobId);
}

async function startJob() {
  if (!state.files.length) {
    toast("Choose at least one photo.");
    return;
  }
  const btn = $("runButton");
  btn.disabled = true;
  btn.textContent = "Starting…";

  const body = new FormData();
  state.files.forEach((file) => body.append("images", file, file.name));
  body.append("profile", $("profile").value);
  body.append("mode", $("mode").value);
  body.append("portable_target", $("tier").value);

  try {
    const res = await fetch("/api/jobs", {method:"POST", body});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not start job");
    await attachJob(data.id);
    await refreshJobs();
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate 3D";
  }
}

$("images").addEventListener("change", (e) => setFiles(e.target.files));
$("runButton").addEventListener("click", startJob);
$("refreshJobs").addEventListener("click", refreshJobs);
$("clearLog").addEventListener("click", () => { state.logs=[]; $("log").textContent=""; });
$("resetView").addEventListener("click", () => {
  const viewer = $("viewer");
  viewer.cameraOrbit = "0deg 75deg auto";
  viewer.cameraTarget = "auto auto auto";
});
$("autoRotate").addEventListener("click", () => {
  const viewer = $("viewer");
  viewer.autoRotate = !viewer.autoRotate;
  $("autoRotate").classList.toggle("active", viewer.autoRotate);
});

const dz = $("dropzone");
["dragenter","dragover"].forEach((name) => dz.addEventListener(name, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
["dragleave","drop"].forEach((name) => dz.addEventListener(name, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
dz.addEventListener("drop", (e) => setFiles(e.dataTransfer.files));

(async () => {
  try {
    const info = await (await fetch("/api/info")).json();
    $("serverStatus").textContent = info.mobile_ready ? "LAN READY" : "LOCAL";
  } catch {
    $("serverStatus").textContent = "OFFLINE";
    $("serverStatus").classList.remove("online");
  }
  refreshJobs();
  setInterval(() => {
    refreshJobs();
    if (state.job?.id) refreshJob();
  }, 3500);
})();
