# STEP 36: Voice Accessibility (Input + Output) For Low-Literacy UX

## Goal
Support rural / low-literacy users by adding **voice-assisted actions**:
- “speak/type” a simple send command
- get **voice feedback** after transaction outcome

## What Was Implemented

### 1) Voice Input (Command Parsing)
User can enter a simple command such as:
- `Send 500 to Ramesh`

System parses:
- amount
- recipient

Then triggers the same secure pipeline:
auth -> device trust -> risk engine -> decision.

### 2) Mic Record Button (Speech-to-Text)
We added a “Record” option.
Important constraint:
- This depends on the browser permission + SpeechRecognition availability.
- If permission is denied or unsupported, typed parsing still works.

### 3) Voice Output (Feedback)
After transaction evaluation, portal gives a short voice feedback message like:
- “Transaction successful.”
- “Transaction is under review.”
- “Transaction blocked for safety.”

This is shown as text and can be spoken using browser TTS.

## Where To See It
- Customer dashboard: `/dashboard/customer`
- Section: “Send Money (Offline-First)” -> Voice Send / Record

## Key Files
- UI handlers: `src/ui/app.py`
- Customer templates: `src/ui/templates/customer_dashboard.html`
- JS voice helpers live inside the customer templates (browser-side)

