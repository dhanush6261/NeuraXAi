const chatBox = document.getElementById("chat-box");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

/* ---------- Global state ---------- */
let controller = null;
let isGenerating = false;
let shouldAutoScroll = true;

/* Memory toggle (default ON) */
let memoryEnabled = true;

/* ---------- Detect manual scroll ---------- */
chatBox.addEventListener("scroll", () => {
  const nearBottom =
    chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 80;
  shouldAutoScroll = nearBottom;
});

/* ---------- Utils ---------- */
function scrollBottom(force = false) {
  if (force || shouldAutoScroll) {
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}

/* ---------- Auto-grow textarea ---------- */
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 200) + "px";
});

/* ---------- Button state ---------- */
function setButtonState(state) {
  if (state === "stop") {
    sendBtn.innerText = "⏹";
    sendBtn.style.background = "#ef4444";
  } else {
    sendBtn.innerText = "➤";
    sendBtn.style.background = "#19c37d";
  }
}

/* ---------- AI text formatter ---------- */
function formatAIResponse(text) {

  const codeBlocks = [];
  let tempText = text.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (_, lang, code) => {
      const id = codeBlocks.length;
      codeBlocks.push({ lang: lang || "code", code });
      return `[[CODE_${id}]]`;
    }
  );

  tempText = tempText
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  tempText = tempText.replace(/(?:^|\n)[*-] (.*)/g, "<li>$1</li>");
  tempText = tempText.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");

  tempText = tempText.replace(/\n/g, "<br>");

  codeBlocks.forEach((b, i) => {
    const safeCode = b.code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    tempText = tempText.replace(
      `[[CODE_${i}]]`,
      `
      <div class="code-block">
        <div class="code-header">
          <span class="code-lang">${b.lang}</span>
          <button class="copy-btn" onclick="copyCode(this)">Copy</button>
        </div>
        <pre><code>${safeCode}</code></pre>
      </div>
      `
    );
  });

  return tempText;
}

/* ---------- Copy code ---------- */
function copyCode(btn) {
  const code = btn.closest(".code-block").querySelector("code").innerText;
  navigator.clipboard.writeText(code);
  btn.innerText = "Copied!";
  setTimeout(() => (btn.innerText = "Copy"), 1500);
}

/* ---------- Message creator ---------- */
function addMessage(text, cls, isAI = false) {
  const div = document.createElement("div");
  div.className = "message " + cls;

  if (isAI) {
    div.innerHTML = formatAIResponse(text);
  } else {
    div.innerText = text;
  }

  chatBox.appendChild(div);
  scrollBottom(true);
  return div;
}

/* ---------- Send / Stop ---------- */
async function sendMessage() {

  if (isGenerating) {
    controller.abort();
    isGenerating = false;
    setButtonState("send");
    return;
  }

  const msg = input.value.trim();
  if (!msg) return;

  addMessage(msg, "user");
  input.value = "";
  input.style.height = "auto";

  const aiDiv = addMessage("", "ai", true);

  controller = new AbortController();
  isGenerating = true;
  setButtonState("stop");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        memory: memoryEnabled
      }),
      signal: controller.signal
    });

    if (!response.ok) {
      let message = response.statusText || "The chat request failed.";
      try {
        const error = await response.json();
        if (typeof error?.error === "string") {
          message = error.error;
        }
      } catch (err) {
        if (err.name === "AbortError") throw err;
      }
      aiDiv.textContent = message;
    } else {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        fullText += decoder.decode(value, { stream: true });
        aiDiv.innerHTML = formatAIResponse(fullText);
        scrollBottom();
      }
    }

  } catch (err) {
    if (err.name === "AbortError") {
      aiDiv.innerHTML += "<br><em>Generation stopped</em>";
    } else {
      aiDiv.textContent = "Could not complete the chat request. Try again.";
    }
  }

  isGenerating = false;
  setButtonState("send");
}

/* ---------- Events ---------- */
sendBtn.onclick = sendMessage;

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.shiftKey) return;

  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});
