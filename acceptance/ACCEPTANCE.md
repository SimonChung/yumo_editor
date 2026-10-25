# YuMo Explorer context menu: staged acceptance

The task uses the current working-tree snapshot, including version 0.3.0 changes.
The original project is not the worker workspace and must not be modified.

## Required behavior

- The existing Windows installer registers a file action named `以 YuMo Editor 編輯` for all files, with a quoted executable and quoted `%1` argument. Uninstall removes its own context-menu key. The Chinese caption must survive the existing Windows NSIS build.
- Public bridge for this task: `App.GetStartupFiles() []string` returns a copy of the command-line file arguments, empty when none. Preserve paths with Chinese characters and spaces. Invalid paths are handled by the existing frontend `OpenFile` error path, which reports an error and continues other files.
- Frontend startup calls `GetStartupFiles`, feeds the returned paths into the existing guarded open flow, and preserves drag/drop, deduplication, unsaved documents, encoding-aware saves, and React StrictMode behavior.
- The Wails generated binding must correspond to the real Go method. Use the pinned beta.30 API. Windows `build.bat build-installer` regenerates bindings and must still compile.
- Preserve current version, dependencies, build entrypoint, existing tests and this acceptance directory.

## Phase A: Linux model task (the run's DONE boundary)

The prepared worker supplies pinned frontend dependencies at `/opt/yumo-deps`.
Run both fixed commands:

1. `node acceptance/context-acceptance.cjs`: 23 checks, including real rendered React startup/open/edit/save behavior, existing drag/drop regressions, and clearly labelled installer-source checks. Native Wails I/O is mocked; these are not Windows installation tests.
2. `node acceptance/typecheck.cjs`: real TypeScript check.

The independent reviewer must assess code, generated binding correctness, regressions, and these fixed tests. It may approve Phase A only when these requirements are met. It must record Windows build/native acceptance as external and not yet established; missing Windows tools in this Linux worker alone is not a Phase-A defect. Do not add self-authored replacement tests or claim Phase B passed. Do not run `build.bat`, install Go/NSIS, or attempt Windows execution inside this Linux worker.

## Phase B: Windows host verification of the same candidate

The outer verifier downloads the approved cumulative patch, applies it to a fresh copy of this snapshot, checks candidate/source hashes, and runs:

- `build.bat build-installer` (existing workflow, frontend dependencies, Wails binding generation, Go binary, NSIS installer).
- `go build ./...`, `go test -count=1 -v ./...`, `go vet ./...` (including the fixed `context_menu_acceptance_test.go`).
- Re-run the fixed React/TypeScript checks after regeneration; compare generated binding output to the submitted binding.
- On Windows, check the actual app opens the named Chinese/space-containing file with expected content. Installer registration, Explorer action and uninstall cleanup require native evidence, with existing user installation/data protected.

Overall feature acceptance is reported separately from Phase A. Build success, simulated tests or a LangGraph DONE state do not by themselves prove Windows install/uninstall and Explorer behavior. No patch is automatically applied to the original project.
