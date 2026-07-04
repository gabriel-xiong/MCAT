# MCAT Speedrun — Tester Quickstart

_Last updated: 2026-07-03._

**Read time: ~2 minutes.** This is the only page you need. It tells you how to
install, what to do for a few days, and how to send your results back. There is
**no account, no sign-in, no internet, and no AI** — everything runs on your own
computer, and you send back a single file when you're done.

> **Nothing to set up.** The app comes **preloaded** — the MCAT deck, the
> practice questions, and the scoring are all already there. You do **not**
> import a deck, load anything, or configure a thing. Just install and study.

---

## 1. Install (Windows) — about 2 minutes

You'll get **two things** from us:

- an installer named **`anki-26.05-win-x64.msi`**, and
- a ZIP named **`MCAT-Speedrun.zip`**.

**Steps:**

1. **Install the app.** Double-click **`anki-26.05-win-x64.msi`** and click
   through (**Next → Next → Finish**). _(If Windows shows a blue "unknown
   publisher" box, see the FAQ below — it's safe.)_
2. **Unzip the folder.** Right-click **`MCAT-Speedrun.zip`** → **Extract All**
   → put it somewhere easy like your **Desktop**.
3. **Open the folder** and **double-click `Start MCAT Speedrun.cmd`**.

**What you'll see on first launch:** the **MCAT Speedrun** home screen, with your
deck already loaded and a dashboard showing **three scores** — Memory,
Performance, and Readiness. They'll say **"not enough data yet"** at first.
**That's normal**, not a bug — they fill in as you study (see §3).

> **Always open MCAT Speedrun from `Start MCAT Speedrun.cmd`** — not the regular
> Anki icon. That launcher opens the special preloaded MCAT profile so
> everything is already there. (If you accidentally open plain Anki, just close
> it and use the `.cmd` instead.)

---

## 2. What to do — ~15–20 min/day for 2–3 days

You're helping us test two things: **flashcard memory** and **exam-question
performance**. Please spread your studying over **2–3 different days** — not all
in one sitting. The memory score is about how well you remember things **over
time**, so same-day cramming doesn't give us a useful signal.

Each day, roughly 15–20 minutes:

1. **Review flashcards (this is the main thing).** Click **Study Flashcards** and
   go through your due cards. Rate them honestly (Again / Hard / Good / Easy).
   Do **as many as you reasonably can** — think dozens over the whole period, not
   five. More reviews across more days = a more trustworthy result.
2. **Try Practice Questions (optional but great).** Click **Practice Questions**
   to answer exam-style multiple-choice questions. A topic only unlocks for
   practice **after you've reviewed its flashcards a bit** (about 3+ cards seen
   and 5+ rated Good/Easy), so do some reviews first and more topics will open
   up.

That's it — study like you normally would, just consistently across a couple of
days.

---

## 3. The three scores (and why they're blank at first)

The dashboard shows **three separate scores**. They measure different things and
are **never blended together**:

- **Memory** — how well the app predicts your flashcard recall over time.
- **Performance** — your accuracy on the exam-style practice questions.
- **Readiness** — an honest MCAT-style range estimate (roughly 472–528), only
  shown once there's enough coverage to mean something.

**"Not enough data / no score yet" is expected early on.** The app is designed
to be **honest**: it would rather say "I don't know yet" than show you a made-up
number. So don't worry if a score is blank on day 1 — keep studying and it will
appear once there's enough to report. **Nothing is broken.**

---

## 4. Send your data back — one file

When you've studied over your 2–3 days, send us your results. **No syncing, no
account** — you just export **one file** and email/upload it.

1. On the home screen, click **"Export my data"** (the wide button at the
   bottom).
2. If it asks, type your **name or initials** so we can tell whose file it is
   (you can also leave it blank and click OK). This label is saved **inside** the
   file, so a rename won't lose it.
3. It saves to your **Desktop** as
   **`MCAT-data_<you>_<date>.perf_bundle.json`** and shows you the exact
   location with an **"Open folder"** button.
4. **Email or upload that single `.json` file** to the study group. That's the
   whole job.

> **Send your own file, as-is.** Don't merge it with anyone else's, don't rename
> it to match a friend's, and don't combine multiple people into one file —
> **one file per person.** Merging destroys the per-person attribution we need.

**Your privacy:** the file contains only your card-review history and practice
answers — **no name beyond the initials you chose, no email, no personal
details, nothing about your computer.** It never leaves your machine until you
choose to send it.

---

## 5. Android (phone) — optional

If we also send you the phone version, you'll get **two files**:

- an app file (an **`.apk`**, e.g. `AnkiDroid-…-release.apk`), and
- a deck file (**`mcat-deck.apkg`**).

**Steps:**

1. **Install the app.** Open the `.apk` on your phone and allow the install (you
   may need to tap **"allow from this source"** — this is expected for an app
   installed outside the Play Store).
2. **Open it**, tap through the intro, then **open `mcat-deck.apkg`** (tap it in
   your Downloads or the link we sent) → choose **AnkiDroid** → confirm import.
3. **Review flashcards** on the deck. It's the **same three scores**; the
   dashboard is under **⋮ (top-right) → MCAT: Dashboard**. On the phone you
   mainly do flashcard reviews — Performance/Readiness may say "not enough data,"
   which is expected (the practice questions are on the desktop version).

**Send phone data back:** home screen → **⋮ → Export collection** → keep
**Collection** selected → **Export** → **Share** to your email/Drive, and send us
the **`.colpkg`** file. (The phone doesn't have the desktop "Export my data"
button; the `.colpkg` carries your reviews.)

---

## 6. FAQ & troubleshooting

**Windows says "Windows protected your PC" / "unknown publisher."**
That's Windows SmartScreen being cautious about an app that isn't from a big
store — it's not a virus warning. To proceed: click **"More info"**, then
**"Run anyway"**. (This app is a research prototype we built ourselves, which is
why it isn't code-signed by a big publisher.)

**The `.cmd` won't open / nothing happens / it says "Could not find Anki."**
Make sure you ran the **`anki-26.05-win-x64.msi`** installer first (Step 1). The
launcher looks for the installed Anki; if the app isn't installed yet it will
tell you and stop. Install the MSI, then double-click `Start MCAT Speedrun.cmd`
again.

**Windows blocks the `.cmd` as a script.**
Right-click `Start MCAT Speedrun.cmd` → **Properties** → if there's an
**"Unblock"** checkbox at the bottom, tick it and click OK, then try again.

**Why is there no score yet? Is it broken?**
No — that's by design. The scores only appear once there's enough study data to
report an honest number. Keep reviewing over a couple of days and they'll show
up. A blank score early on is normal.

**Do I need an account or to sign in?**
No. There's no account, no login, and no sync to any server. Everything is local.

**Is my data private?**
Yes. Everything stays on your computer. The only thing that leaves is the one
`.json` file **you** choose to export and send, and it contains just your study
history and practice answers — no personal information.

**Do I need internet or an API key / AI?**
No. AI is **off** and no key is included. All three scores and the built-in
question explanations work fully offline.

**You sent me a new build — how do I update?**
Just install the new `.msi` over the old one and use the new `MCAT-Speedrun`
folder's `Start MCAT Speedrun.cmd`. Your existing study data stays in your
current base folder, so **export your data first** if you've already studied,
then switch to the new build.

---

## Cover message — ready to paste (builder sends this)

> **Subject: Want to help me test my MCAT study app? (~15–20 min/day, 2–3 days)**
>
> Hey! I built a little MCAT study app (an Anki fork with three separate scores —
> memory, exam performance, and a readiness estimate) and I'd love your help
> testing it. It's a prototype, so it's rough around the edges, but it's genuinely
> useful for review.
>
> **What I need:** about **15–20 minutes a day for 2–3 days** of real flashcard
> review (and a few practice questions if you like). Spreading it over a couple of
> days matters — that's what lets the memory score actually calibrate.
>
> **Setup is 2 clicks and there's no account, no sign-in, and no internet needed.**
> Everything runs on your computer.
>
> 1. Download link: **[PASTE DOWNLOAD LINK]** — you'll get an installer
>    (`anki-26.05-win-x64.msi`) and a zip (`MCAT-Speedrun.zip`).
> 2. Run the installer, unzip the folder, and double-click
>    **`Start MCAT Speedrun.cmd`**.
> 3. Study for a couple of days, then click **"Export my data"** and email me the
>    one file it makes. That's it!
>
> Full 2-minute instructions are in the zip (and here: **[PASTE QUICKSTART LINK]**).
> Heads up: Windows may show an "unknown publisher" warning — that's normal for a
> homemade app; click **More info → Run anyway**. Some scores will say "not enough
> data yet" at first — that's expected, they fill in as you study.
>
> Thank you so much — this really helps! 🙏
