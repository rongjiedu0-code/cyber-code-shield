# Demo buggy project

This tiny project is designed for the `--fix-error` workflow.

`app.py` contains a simple `NameError`: the function receives `raw_username`, but the implementation uses a variable named `username`.

## Reproduce the error

From this directory:

```bash
python app.py
```

The sample traceback is saved in `error.log`.

## Generate a local fix suggestion

From the Cyber-Code-Shield repository root:

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/error.log --context-lite --dry-run
```

To call a local Ollama model instead of only previewing the prompt:

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/error.log --chat-model gemma4-local --context-lite --patch-timeout 600
```

The expected suggestion should identify the wrong variable name and propose using `raw_username.strip().lower()` inside `normalize_username`.

Cyber-Code-Shield only writes a Markdown suggestion file. It does not modify `app.py` automatically. Generated suggestion files are local review artifacts and should not be committed unless they are intentionally used as examples.
