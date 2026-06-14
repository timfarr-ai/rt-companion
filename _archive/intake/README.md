# Intake — how to hand me Discord (and other) source material

Goal: get canonical **emails, contracts/LOIs, and terminology** into the repo in a form that's
(a) easy for me to scaffold into the 5-strategy assets, and (b) **stays defensible** (every item
keeps its provenance, so we can always point to where it came from).

## The one rule: capture the RAW content + where it came from
- **Paste the exact text** — don't summarise, don't clean it up. I use it verbatim.
- **Stamp the source** — channel/thread, who posted it (is it a staff/leader post?), the date, and a
  link or screenshot if you have one. That stamp is what makes it "proof," not just text.

## Where to put things
- **Text** (email templates, terminology, message bodies, pasted Google-Doc contents) → append a block
  to `COLLECTED.md` using the template in that file.
- **Files** (a real contract/LOI as PDF or DOCX, an image, an exported doc) → drop the file in
  `intake/files/` and add a short block in `COLLECTED.md` pointing to the filename.

## By content type — easiest path
| You found… | Best handover |
|---|---|
| A message / pinned post (text) | Copy the text → paste into a `COLLECTED.md` block |
| A **contract / LOI** as a PDF | Download the PDF → `intake/files/` (I can read PDFs directly) |
| A contract as a **Google Doc** | *File → Download → PDF* into `files/`, **or** paste the text into a block. A bare Doc link isn't durable — capture the content. |
| A `.docx` | Either drop the .docx in `files/` **and** paste its text, or export to PDF |
| A screenshot of text | Fine as a backup, but **also paste the text** if you can — text beats an image for me |

## What to prioritise (from the proof audit)
🔴 **Contracts first** — we have *zero* contract documents; this is the hard gap. Then 🟡 **emails**,
then 🟡 **terminology**. The checklist in `COLLECTED.md` shows exactly what's missing per strategy.

When you've added material, just tell me "intake updated" and I'll process it.
