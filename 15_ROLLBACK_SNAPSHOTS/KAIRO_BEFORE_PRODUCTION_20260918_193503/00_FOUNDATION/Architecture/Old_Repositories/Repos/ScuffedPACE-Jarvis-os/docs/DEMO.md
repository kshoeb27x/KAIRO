# JARVIS OS — Three-Minute Demo Script

## Setup (before the audience arrives)

1. `npm install` (once), then `npm run dev`.
2. Open http://127.0.0.1:5173 in Chrome (best voice support).
3. Optional: delete `.data/` first for a completely fresh state — the JARVIS
   OS project reseeds automatically.
4. Mock mode needs no configuration. Status strip should read
   **Demo Provider (no real model)** — this is honest labeling, not an error.
5. If you'll use voice, click the mic once beforehand to grant microphone
   permission so the demo isn't interrupted by the browser prompt.

## The story (≈3 minutes)

Each step can be spoken (hold the mic button) or typed — the quick-command
chips under the input contain every line.

1. **Activation.** The dashboard greets Farhan; the sphere idles calmly; the
   Active Project card shows **JARVIS OS** (labeled Demo seed).

2. **Fast answer.** Ask: *“What are we building today?”*
   → Activity rail shows: request received → routed to project specialist →
   memory checked → Demo Provider responding. The answer uses real project
   memory from SQLite.

3. **Project request.** Ask: *“Break tonight's build into the next three
   steps.”* → Same honest routing; a concrete three-step answer.

4. **Tool request + permission gate.** Ask: *“Draft an email telling my
   collaborator the prototype will be ready tomorrow.”*
   → Rail shows the simulated mail tool drafting; the sphere pauses amber; an
   approval card presents the exact server-stored draft, labeled
   **Simulated**. Approve (records `simulated_completed`) or cancel — point
   out that nothing is ever actually sent, and a duplicate decision would be
   rejected by the server.

5. **Deep reasoning.** Ask: *“Evaluate whether this architecture will scale to
   multiple businesses.”* → Rail shows deep-reasoning routing; in mock mode
   the response says outright that it is simulated. (With an Anthropic key
   configured, this is a real Claude answer.)

6. **Memory.** Say: *“Remember that I prefer approval before any external
   action.”* → Rail shows **Preference saved** — only after the database
   write actually succeeded. Open **Memory** in the left nav to inspect it
   (and show that Forget archives rather than destroys).

7. **Persistence.** Refresh the page. The conversation, active project,
   settings, and memory all survive — SQLite is the source of truth, not
   browser storage.

## Expected states on the sphere

idle (calm) → listening (ring follows your mic level) → routing/thinking
(paths accelerate, nodes converge) → executing (energy outward) → permission
(paused, amber) → speaking (pulses on real speech boundaries) → idle.

## Recovery moves

- **Anything hangs or talks too long:** press Esc (or Stop) — interruption
  cancels the request, recognition, and speech, and returns to Ready.
- **Error banner appears:** it says what failed and nothing was sent; click
  Recover and continue.
- **No microphone / permission denied:** the banner says so; continue typing —
  every demo line works typed.
- **Server not running:** the app says the server is unreachable; start
  `npm run dev` and click Recover.
