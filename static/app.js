/* 通用工具：请求、模态框、提示 */
async function api(path, options = {}) {
  const opts = { headers: {}, ...options };
  if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
  return data;
}

function toast(msg, ms = 2600) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), ms);
}

function openModal(title, bodyHTML, footHTML = "") {
  let mask = document.querySelector(".modal-mask");
  if (!mask) {
    mask = document.createElement("div");
    mask.className = "modal-mask";
    document.body.appendChild(mask);
  }
  mask.innerHTML = `<div class="modal">
      <div class="modal-head"><span></span><button class="x" onclick="closeModal()" aria-label="关闭"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="width:16px;height:16px;"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button></div>
      <div class="modal-body"></div>
      <div class="modal-foot"></div>
    </div>`;
  mask.querySelector(".modal-head span").textContent = title;
  mask.querySelector(".modal-body").innerHTML = bodyHTML;
  mask.querySelector(".modal-foot").innerHTML = footHTML;
  mask.classList.add("open");
}

function closeModal() {
  document.querySelector(".modal-mask")?.classList.remove("open");
}

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function val(sel) {
  return document.querySelector(sel)?.value.trim() ?? "";
}

function setVal(sel, v) {
  const el = document.querySelector(sel);
  if (el) el.value = v ?? "";
}

/* 带上传进度与取消能力的请求：返回的 Promise 上挂 .abort() */
function apiUpload(path, file, onProgress) {
  let xhrRef = null;
  const p = new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhrRef = xhr;
    xhr.open("POST", path);
    const fd = new FormData();
    fd.append("file", file);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch (e) { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(data.detail || data.error || xhr.statusText || "上传失败"));
    };
    xhr.onerror = () => reject(new Error("网络错误，上传失败"));
    xhr.onabort = () => reject(new Error("__aborted__"));
    xhr.send(fd);
  });
  p.abort = () => { if (xhrRef) xhrRef.abort(); };
  return p;
}

/* ===== 日期选择器：把带 data-dpick 的文本框替换成「年 + 月」下拉。
   选中的值仍写回原输入框（格式统一为 YYYY年M月），表单收集逻辑零改动。
   data-dpick="year" 表示只要年份；data-min 指定起始年份。 ===== */
function dpParse(v) {
  v = (v ?? "").toString().trim();
  let m;
  if ((m = v.match(/^(\d{4})\s*年\s*(\d{1,2})\s*月$/))) return { y: m[1], m: String(parseInt(m[2], 10)) };
  if ((m = v.match(/^(\d{4})[.\-/](\d{1,2})$/))) return { y: m[1], m: String(parseInt(m[2], 10)) };
  if ((m = v.match(/^(\d{4})\s*年$/))) return { y: m[1], m: "" };
  if (/^(至今|现在)$/.test(v)) return { now: true };
  if (v) return { raw: v };
  return {};
}

function applyDatePicker(input) {
  if (!input || input._dp) return;
  input._dp = true;
  const yearOnly = input.dataset.dpick === "year";
  const min = parseInt(input.dataset.min || "1980", 10);
  const max = new Date().getFullYear() + 4;
  const p0 = dpParse(input.value);

  let yOpts = `<option value="">—— 年</option>`;
  for (let y = max; y >= min; y--) {
    yOpts += `<option value="${y}" ${p0.y === String(y) ? "selected" : ""}>${y}年</option>`;
  }
  if (p0.now) yOpts += `<option value="now" selected>至今</option>`;
  if (p0.raw) yOpts += `<option value="raw" selected>原值：${esc(p0.raw)}</option>`;

  const wrap = document.createElement("span");
  wrap.className = "dp" + (input.disabled ? " off" : "");
  wrap.innerHTML = `<select class="dp-y">${yOpts}</select>` +
    (yearOnly ? "" : (() => {
      let s = `<select class="dp-m"><option value="">— 月</option>`;
      for (let i = 1; i <= 12; i++) s += `<option value="${i}" ${p0.m === String(i) ? "selected" : ""}>${i}月</option>`;
      return s + `</select>`;
    })());

  const ySel = wrap.querySelector(".dp-y");
  const mSel = wrap.querySelector(".dp-m");
  const sync = () => {
    const now = ySel.value === "now", raw = ySel.value === "raw";
    if (mSel) mSel.style.display = (now || raw) ? "none" : "";
    input.value = now ? "至今" : raw ? p0.raw :
      (ySel.value ? (mSel && mSel.value ? `${ySel.value}年${parseInt(mSel.value, 10)}月` : `${ySel.value}年`) : "");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  };
  ySel.addEventListener("change", sync);
  if (mSel) mSel.addEventListener("change", sync);

  input.style.display = "none";
  input.after(wrap);

  /* 外部代码改 input.value 后调用 _dpSync 让下拉跟着刷新 */
  input._dpSync = () => {
    const p = dpParse(input.value);
    if (p.now && ![...ySel.options].some(o => o.value === "now")) {
      ySel.insertAdjacentHTML("beforeend", `<option value="now">至今</option>`);
    }
    if (p.raw && ![...ySel.options].some(o => o.value === "raw")) {
      ySel.insertAdjacentHTML("beforeend", `<option value="raw">原值：${esc(p.raw)}</option>`);
    }
    ySel.value = p.now ? "now" : p.raw ? "raw" : (p.y || "");
    if (p.raw) ySel.selectedOptions[0].textContent = `原值：${p.raw}`;
    if (mSel) mSel.value = p.m || "";
    if (mSel) mSel.style.display = (p.now || p.raw) ? "none" : "";
    wrap.classList.toggle("off", input.disabled);
  };
}

function makeDatePickers(root = document) {
  if (root instanceof Element) { if (root.matches("input[data-dpick]")) applyDatePicker(root); return; }
  (root.querySelectorAll("input[data-dpick]") || []).forEach(applyDatePicker);
}

function refreshDatePickers(root = document) {
  root.querySelectorAll("input[data-dpick]").forEach(inp => inp._dpSync && inp._dpSync());
}
