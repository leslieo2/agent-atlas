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
