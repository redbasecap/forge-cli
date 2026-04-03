# Forge CLI

<p align="center">
  <strong>Self-improving agent harness CLI — forge better agents through iterative refinement</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/language-Rust-orange?logo=rust&style=flat-square" alt="Rust" />
  <img src="https://img.shields.io/badge/language-Python-blue?logo=python&style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License" />
</p>

---

## What is Forge?

Forge is an open-source agent harness CLI that combines a high-performance Rust runtime with a self-improving experimentation loop. It provides:

- **Fast, memory-safe runtime** — Rust-powered CLI for interactive and scripted agent sessions
- **Multi-provider support** — works with Anthropic, OpenAI-compatible, and other LLM providers
- **Self-improving loop** — automated benchmark, score, and hill-climbing engine that iteratively refines the harness
- **Plugin system** — extensible hooks and bundled plugins for customizing agent behavior
- **Tool ecosystem** — file operations, bash execution, web search, MCP integration, and more

## Quick Start

### Build from source (Rust)

```bash
cd rust
cargo build --release
./target/release/forge
```

### Run in interactive mode

```bash
forge                          # Start REPL
forge prompt "explain this"    # One-shot prompt
forge --resume                 # Resume last session
```

### Self-improving loop (Python)

```bash
# Initialize example tasks
python3 -m src.main forge-init-tasks

# Run the benchmark suite
python3 -m src.main forge-bench

# Start the self-improvement loop
python3 -m src.main forge-improve

# View scores and experiment history
python3 -m src.main forge-score
python3 -m src.main forge-experiment-log
```

## Self-Improving Loop

Forge includes an experimentation engine inspired by [autoagent](https://github.com/autoagent) that iteratively improves the harness through hill-climbing:

1. **Read** — the meta-agent reads `program.md` for high-level directives
2. **Benchmark** — runs all tasks in `tasks/` and scores results (0.0-1.0)
3. **Diagnose** — analyzes failure patterns from failed tasks
4. **Propose** — generates targeted modifications to the harness
5. **Evaluate** — re-runs benchmarks; keeps improvements, discards regressions
6. **Log** — records every experiment in `results.tsv` with git commit references

Edit `program.md` to steer the loop toward your goals.

## Task Format

Each task lives in `tasks/<task-name>/` with:

```
tasks/example-task/
  task.toml           # name, description, timeout
  instruction.md      # what the agent should do
  tests/
    test.sh           # verification script (exit 0 = pass)
```

Example `task.toml`:

```toml
[task]
name = "example-task"
description = "Write a function that returns the nth Fibonacci number"
timeout = 60
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `forge` | Start interactive REPL |
| `forge prompt "..."` | One-shot prompt execution |
| `forge --resume` | Resume the last session |
| `forge improve` | Start the self-improvement loop |
| `forge bench` | Run benchmark suite once |
| `forge score` | Show current benchmark scores |
| `forge experiment-log` | Display experiment history |
| `forge init-tasks` | Scaffold a `tasks/` directory with examples |

## Architecture

```
rust/                      # Rust workspace
  crates/
    forge-cli/             # CLI binary (forge)
    runtime/               # Session, config, permissions, hooks
    api/                   # LLM provider clients
    tools/                 # Built-in tool implementations
    commands/              # Slash commands
    plugins/               # Plugin system
    telemetry/             # Usage tracking
    compat-harness/        # Compatibility layer

src/                       # Python modules
  self_improve/            # Self-improvement engine
    engine.py              # ExperimentLoop (hill-climbing)
    scorer.py              # TaskScorer + ScoreHistory
    task_runner.py          # Task discovery and execution
    meta_agent.py          # Diagnosis and proposal generation
  main.py                  # CLI entrypoint

tasks/                     # Benchmark tasks
program.md                 # Meta-agent directives
results.tsv                # Experiment log (auto-generated)
```

## Configuration

- `.forge.json` — project-level configuration
- `.forge/settings.json` — user settings
- `.forge/settings.local.json` — machine-local overrides

## License

MIT
