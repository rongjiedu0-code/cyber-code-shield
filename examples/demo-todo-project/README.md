# Demo TODO project

This tiny project is designed for the `--complete-todo` workflow.

`app.py` contains one incomplete function: `is_valid_username`. The surrounding code and docstring describe the expected behavior, so the local model does not need broad project context.

## Generate a local completion suggestion

From the Cyber-Code-Shield repository root:

```bash
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --context-lite --dry-run
```

To call a local Ollama model instead of only previewing the prompt:

```bash
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --chat-model gemma4-local --context-lite --patch-timeout 600
```

A good suggestion should implement `is_valid_username` for 3-20 character usernames containing only letters, digits, or underscores.

Cyber-Code-Shield only writes a Markdown suggestion file. It does not modify `app.py` automatically.
