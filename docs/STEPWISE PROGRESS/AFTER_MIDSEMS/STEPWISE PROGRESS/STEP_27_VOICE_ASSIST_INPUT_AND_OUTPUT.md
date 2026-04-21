# STEP 05: Voice Assist (Input + Output) for Low-Literacy Users

## Goal
Support rural users who may struggle with reading/typing:
- voice-assisted transaction input
- voice feedback for outcomes (success/held/blocked)

## What Was Implemented

### Voice Input (Text + Optional Mic Record)
On customer dashboard, user can:
- type a command like “Send 500 to Ramesh”
- or use a mic record button (browser SpeechRecognition if available)

Parsed into:
- amount
- recipient

### Voice Output (Feedback)
After a transaction is created, dashboard provides:
- a **Voice Feedback** button to read the outcome:
  - “Transaction saved successfully”
  - “Transaction is under review”
  - “Transaction was blocked”

It also speaks simple “Reason: …” text (localized).

### Safety Guidance Voice
If the fraud engine attaches safety guidance, it is shown as a list (and can be read aloud).

## Key Files
- Voice parsing + feedback: `src/ui/templates/customer_home.html`
- Voice message builder: `src/ui/app.py` (`_build_customer_voice_feedback`)

## Demo Tips
1. Create a low-risk transaction (shows success voice)
2. Create a high-risk transaction (shows held/block voice)
3. Click “Voice Feedback” to demonstrate accessibility.

