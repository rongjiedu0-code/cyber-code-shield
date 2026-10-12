# Demo buggy project

This tiny project is designed for the `--fix-error` workflow.

`app.py` contains a simple `NameError`: the function receives `raw_username`, but the implementation uses a variable named `username`.

## Reproduce the error

From this directory:

```bash
python app.py
```

A portable sample traceback is included in `traceback.txt`. It points to the deliberately broken line in `app.py`. The `.txt` extension keeps the fixture versioned while generated `*.log` files remain ignored.

Running `python app.py` is expected to fail with `NameError`; it does not save a log automatically. You can use the included fixture directly without running the broken app first.

## Generate a local fix suggestion

From the Cyber-Code-Shield repository root:

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/traceback.txt --context-lite --dry-run
```

To call a local Ollama model instead of only previewing the prompt:

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/traceback.txt --chat-model gemma4-local --context-lite --patch-timeout 600
```

In dry-run mode, expect an exit code of 0, `app.py:2` as the primary error location, and a prompt containing the undefined `username` variable. A model is not called, so this is a context preview rather than a generated repair.

The expected suggestion from a real model should identify the wrong variable name and propose using `raw_username.strip().lower()` inside `normalize_username`.

Cyber-Code-Shield only writes a Markdown suggestion file. It does not modify `app.py` automatically. Generated suggestion files are local review artifacts and should not be committed unless they are intentionally used as examples.

