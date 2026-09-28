(() => {
  "use strict";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Rotating flower petals ---------- */
  (function flower() {
    const g = document.getElementById("petals");
    if (!g) return;
    const petals = 8;
    for (let i = 0; i < petals; i++) {
      const a = (i / petals) * Math.PI * 2;
      const x = 50 + Math.cos(a) * 22;
      const y = 50 + Math.sin(a) * 22;
      const el = document.createElementNS("http://www.w3.org/2000/svg", "ellipse");
      el.setAttribute("cx", x.toFixed(2));
      el.setAttribute("cy", y.toFixed(2));
      el.setAttribute("rx", "16");
      el.setAttribute("ry", "6");
      el.setAttribute("transform", `rotate(${(a * 180) / Math.PI} ${x.toFixed(2)} ${y.toFixed(2)})`);
      g.appendChild(el);
    }
  })();

  /* ---------- Fade-in on scroll/load ---------- */
  (function fade() {
    const items = document.querySelectorAll("[data-fade]");
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    items.forEach((el) => io.observe(el));
  })();

  /* ---------- WebGL halftone particle light field ---------- */
  const FRAG = `
    precision mediump float;
    uniform vec2 u_res;
    uniform float u_time;
    uniform vec2 u_mouse;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
    void main() {
      vec2 uv = gl_FragCoord.xy / u_res;
      vec2 asp = vec2(u_res.x / u_res.y, 1.0);
      float t = u_time * 0.08;
      // slow flowing scalar field
      float f = 0.0;
      f += sin((uv.x * 3.0 + t) * 3.14159) * 0.5 + 0.5;
      f += sin((uv.y * 2.4 - t * 1.3) * 3.14159) * 0.5 + 0.5;
      f += sin((uv.x + uv.y) * 4.0 + t * 2.0) * 0.5 + 0.5;
      f /= 3.0;
      // mouse attraction: brighten toward pointer
      float md = distance(uv * asp, u_mouse * asp);
      float glow = smoothstep(0.55, 0.0, md);
      f = mix(f, 1.0, glow * 0.65);
      // halftone grid
      float cells = mix(34.0, 60.0, uv.y);
      vec2 g = uv * cells * asp;
      vec2 cell = fract(g) - 0.5;
      vec2 id = floor(g);
      float jitter = hash(id) * 0.35;
      float radius = clamp(f * 0.52 - 0.06 + jitter * 0.1, 0.0, 0.5);
      float d = length(cell);
      float dot = smoothstep(radius, radius - 0.06, d);
      // copper -> warm white by intensity
      vec3 copper = vec3(0.72, 0.45, 0.20);
      vec3 warm = vec3(0.96, 0.90, 0.80);
      vec3 col = mix(copper, warm, smoothstep(0.35, 0.95, f + glow * 0.4));
      vec3 bg = vec3(0.02, 0.02, 0.02);
      gl_FragColor = vec4(mix(bg, col, dot * (0.35 + f * 0.65)), 1.0);
    }
  `;
  const VERT = `
    attribute vec2 a_pos;
    void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }
  `;

  const canvas = document.getElementById("field");
  if (!canvas) return;
  const mouse = { x: 0.5, y: 0.55, tx: 0.5, ty: 0.55 };
  let activeCtx = null;

  function trackPointer() {
    canvas.addEventListener("pointermove", (e) => {
      const r = canvas.getBoundingClientRect();
      mouse.tx = (e.clientX - r.left) / r.width;
      mouse.ty = 1.0 - (e.clientY - r.top) / r.height;
    });
    canvas.addEventListener("pointerleave", () => {
      mouse.tx = 0.5;
      mouse.ty = 0.55;
    });
  }

  function fit(gl) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const r = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.floor(r.width * dpr));
    const h = Math.max(1, Math.floor(r.height * dpr));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      if (gl) gl.viewport(0, 0, w, h);
    }
    return [w, h];
  }

  function startWebGL() {
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    if (!gl) return false;
    activeCtx = gl;
    const compile = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) return null;
      return s;
    };
    const vs = compile(gl.VERTEX_SHADER, VERT);
    const fs = compile(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return false;
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a_pos");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const uRes = gl.getUniformLocation(prog, "u_res");
    const uTime = gl.getUniformLocation(prog, "u_time");
    const uMouse = gl.getUniformLocation(prog, "u_mouse");
    const start = performance.now();

    function frame(now) {
      const [w, h] = fit(gl);
      mouse.x += (mouse.tx - mouse.x) * 0.05;
      mouse.y += (mouse.ty - mouse.y) * 0.05;
      gl.uniform2f(uRes, w, h);
      gl.uniform1f(uTime, reduceMotion ? 0 : (now - start) / 1000);
      gl.uniform2f(uMouse, mouse.x, mouse.y);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!reduceMotion) requestAnimationFrame(frame);
    }
    trackPointer();
    requestAnimationFrame(frame);
    return true;
  }

  /* ---------- 2D canvas fallback ---------- */
  function start2D() {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    activeCtx = null;
    const start = performance.now();
    function frame(now) {
      const [w, h] = fit(null);
      const t = reduceMotion ? 0 : (now - start) / 1000;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#050505";
      ctx.fillRect(0, 0, w, h);
      const step = Math.max(14, w / 48);
      mouse.x += (mouse.tx - mouse.x) * 0.05;
      mouse.y += (mouse.ty - mouse.y) * 0.05;
      const mx = mouse.x * w;
      const my = (1 - mouse.y) * h;
      for (let y = step / 2; y < h; y += step) {
        for (let x = step / 2; x < w; x += step) {
          const wave = (Math.sin(x * 0.01 + t) + Math.cos(y * 0.012 - t * 1.2)) * 0.5 + 0.5;
          const d = Math.hypot(x - mx, y - my);
          const glow = Math.max(0, 1 - d / (w * 0.4));
          const f = Math.min(1, wave * 0.7 + glow * 0.6);
          const r = f * (step * 0.42);
          if (r < 0.4) continue;
          const c = Math.round(120 + f * 130);
          ctx.fillStyle = `rgb(${c}, ${Math.round(70 + f * 90)}, ${Math.round(32 + f * 60)})`;
          ctx.beginPath();
          ctx.arc(x, y, r, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      if (!reduceMotion) requestAnimationFrame(frame);
    }
    trackPointer();
    requestAnimationFrame(frame);
  }

  if (!startWebGL()) start2D();
  window.addEventListener("resize", () => fit(activeCtx), { passive: true });

  /* ---------- Live A2A node tester ---------- */
  (function tester() {
    const input = document.getElementById("msg-input");
    const btn = document.getElementById("msg-send");
    const out = document.getElementById("msg-output");
    if (!input || !btn || !out) return;

    async function send() {
      const text = input.value.trim();
      if (!text) {
        out.textContent = "请输入一条消息。";
        return;
      }
      btn.disabled = true;
      out.textContent = "正在连接幻16桥接节点…";
      const body = {
        jsonrpc: "2.0",
        id: Date.now(),
        method: "message/send",
        params: {
          message: {
            role: "user",
            parts: [{ kind: "text", text }],
            messageId: "web-" + Math.random().toString(36).slice(2, 12),
            kind: "message",
          },
          configuration: { acceptedOutputModes: ["text/plain"], blocking: true },
        },
      };
      try {
        const res = await fetch("/functions/v1/app", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(body),
        });
        const ct = res.headers.get("content-type") || "";
        if (res.status === 401 || res.status === 403) {
          out.textContent =
            "访问被拒绝（" + res.status + "）。该节点为私有 —— 需以公开受众发布后方可访问。";
          return;
        }
        if (!ct.includes("application/json")) {
          out.textContent =
            "该节点端点在当前环境尚未上线（返回非 JSON 响应）。函数部署后即可响应。";
          return;
        }
        const data = await res.json();
        if (data && data.result && Array.isArray(data.result.parts)) {
          const reply = data.result.parts.map((p) => p.text || "").join(" ").trim();
          out.textContent = "agent → " + reply;
        } else if (data && data.error) {
          out.textContent = "错误 " + data.error.code + "：" + data.error.message;
        } else {
          out.textContent = JSON.stringify(data, null, 2);
        }
      } catch (err) {
        out.textContent = "请求失败：" + (err && err.message ? err.message : "网络错误");
      } finally {
        btn.disabled = false;
      }
    }

    btn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
  })();
})();

/* ---------- 04 视频归档：文件夹渲染（数据驱动 /videos.json） ---------- */
(function archiveFolders() {
  const row = document.getElementById("folderRow");
  if (!row) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  fetch("/videos.json")
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error("http " + r.status))))
    .then((man) => {
      const groups = {};
      (man.entries || []).forEach((e) => {
        const g = e.kind === "kdocs" ? "文档夹" : e.kind === "video" ? "视频夹" : "哔哩哔哩夹";
        (groups[g] = groups[g] || []).push(e);
      });
      Object.keys(groups).forEach((gname) => {
        const items = groups[gname];
        const folder = document.createElement("div");
        folder.className = "folder";
        const cover = document.createElement("div");
        cover.className = "folder-cover";
        cover.setAttribute("role", "button");
        cover.setAttribute("tabindex", "0");
        cover.setAttribute("aria-expanded", "false");
        cover.innerHTML =
          '<span class="folder-count">' + items.length + ' 件</span>' +
          '<span class="folder-title">' + gname + "</span>";
        const docs = document.createElement("div");
        docs.className = "folder-docs";
        items.forEach((e) => {
          const flag = e.status === "login-walled" ? ' <span class="doc-flag">[需登录]</span>' : e.status === "reserved" ? ' <span class="doc-flag">[预留]</span>' : "";
          const note = e.note ? '<span class="doc-note">' + e.note + (e.date ? " · " + e.date : "") + "</span>" : "";
          if (e.url) {
            docs.insertAdjacentHTML("beforeend", '<a href="' + e.url + '" target="_blank" rel="noopener">' + e.title + flag + note + "</a>");
          } else {
            docs.insertAdjacentHTML("beforeend", '<span class="doc">' + e.title + flag + note + "</span>");
          }
        });
        const toggle = () => {
          const open = folder.classList.toggle("open");
          cover.setAttribute("aria-expanded", open ? "true" : "false");
        };
        cover.addEventListener("click", toggle);
        cover.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(); }
        });
        folder.appendChild(cover);
        folder.appendChild(docs);
        row.appendChild(folder);
        if (reduce) folder.classList.add("open");
      });
      const stamp = document.createElement("p");
      stamp.className = "archive-hint";
      stamp.textContent = "清单更新：" + (man.updated || "未知") + " · 条目 " + ((man.entries || []).length) + " 件";
      row.parentNode.appendChild(stamp);
    })
    .catch(() => {
      row.textContent = "归档清单 /videos.json 暂不可读。";
    });
})();
