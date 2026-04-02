# Privacy Design: Screen Context and Proactive Suggestions

## Overview

This project separates proactive assistance into two operating modes so that users can control how much context Copilot may inspect before offering suggestions.

## Operating Modes

### Safe Mode

Safe Mode is the default.

- uses low-sensitivity signals only
- does not capture screenshots for proactive suggestion generation
- relies on active app name, window title, explicit user input, and local metadata

### Enhanced Mode

Enhanced Mode is opt-in.

- allows screen-derived context for proactive suggestions
- is limited in scope to proactive suggestion generation only
- is intended for users who want richer contextual help and accept the additional privacy tradeoff

## Product Principles

1. Privacy by default
   Safe Mode is the default system behavior.

2. Explicit user control
   Enhanced Mode requires an intentional user action.

3. Minimum necessary data
   The system should prefer app and window metadata before using deeper context.

4. Local-first processing
   When possible, screen-derived understanding should happen locally or be reduced to minimal structured signals before any model call.

5. Clear visibility
   Users should be able to see which mode is active and change it at any time.

6. Narrow scope
   Enhanced Mode should not silently expand to unrelated features without another explicit user decision.

## Threat Model

Screen-derived context can expose:

- private messages
- financial data
- health information
- credentials or session tokens
- confidential company material

The system therefore treats screenshots as higher-risk context than app metadata or explicit user input.

## Guardrails

- default to Safe Mode
- make Enhanced Mode opt-in
- limit Enhanced Mode to proactive suggestions only
- avoid collecting screenshots continuously when no trigger is present
- allow users to disable the feature immediately
- avoid storing screenshots after use
- block or downscope support for especially sensitive app categories in future iterations

## Data Flow

### Safe Mode

```text
Active app/window
  -> Context heuristics
  -> Trigger detection
  -> Suggestions
```

### Enhanced Mode

```text
Active app/window
  -> Optional screen-derived context
  -> Context heuristics
  -> Trigger detection
  -> Suggestions
```

## Engineering Scope in This Repo

The current implementation adds:

- persisted privacy mode state
- Safe vs Enhanced runtime toggle
- proactive suggestion behavior that respects the selected mode

The current implementation does not yet add:

- a full allowlist / denylist for sensitive apps
- local OCR or local screen classification
- retention dashboards or admin policy controls

## Future Work

- add app-level privacy policies
- add local OCR before any model upload
- add a visible indicator showing when screen-derived context was last used
- add enterprise policy controls and audit logs
