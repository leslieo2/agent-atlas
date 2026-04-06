# Controlled Validation Carrier

`validation/` owns the thin assets needed for `#18` style project-in-container validation runs:

- a Linux runner image that includes `agent-atlas-runner-base`
- a Linux Claude Code CLI install as a validation-time assumption
- one pre-positioned sample project bundle at
  `file:///opt/atlas-validation/project-bundle.tar.gz`
- a local execution script that runs the real runner entrypoint and verifies transcript,
  terminal, changed-files, and artifact recovery

This directory is intentionally validation-scoped. It is not a general artifact delivery or
workspace lifecycle subsystem.

Sensitive host-auth bridge note:

- local validation currently requires host Claude auth at `~/.claude` and `~/.claude.json`
- `run_validation.py` copies those files into a temporary home for the validation container rather
  than expecting fresh in-container login
- it also forwards host `ANTHROPIC_*` and `CLAUDE_*` environment variables into the runner payload
  unless the payload already pinned explicit values
- this is an explicit local bridge for controlled validation and starter realism, not a silent
  default Atlas-wide auth behavior
