# Customer Portal Deep Dive

## Main Responsibilities

The customer portal is responsible for onboarding, login, transaction creation, safety settings, transaction visibility, and user-facing fraud transparency.

## Registration

The customer registration flow:

- creates the user locally
- hashes phone and PIN
- stores title, first name, and last name
- captures face image
- computes a lightweight face hash
- enrolls the device
- attempts to establish a server JWT session too

## Login

The customer login flow:

- checks local PIN and lockout rules
- checks device status
- verifies face hash
- may refresh face hash on trusted device if mismatch is likely due to demo conditions
- redirects to dashboard with role and trust cookies set

## Dashboard

The dashboard includes:

- demo balance
- transaction counters
- mini statement
- notifications
- alerts
- sync status
- risk/behavior summary
- safety state (trusted contact, freeze)

## Send Money

The customer can create a transaction via:

- standard form flow
- AJAX JSON flow
- voice flow

All of these route into the same local transaction creation pipeline.

## History and Detail Views

History is PIN-protected and decrypts transaction contents only after key derivation. Transaction signatures are verified. If integrity fails, the system refuses to display the decrypted payload and marks the transaction as compromised.

## Safety Features

- trusted contact set/remove
- panic freeze
- device trust awareness
- voice/text safety guidance

## Offline and UX Support

The customer UI includes:

- offline simulator toggle
- flash messages across redirects
- voice feedback prompts
- simplified alerts and risk labels
