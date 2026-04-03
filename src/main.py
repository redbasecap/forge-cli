from __future__ import annotations

import argparse

from .bootstrap_graph import build_bootstrap_graph
from .command_graph import build_command_graph
from .commands import execute_command, get_command, get_commands, render_command_index
from .direct_modes import run_deep_link, run_direct_connect
from .parity_audit import run_parity_audit
from .permissions import ToolPermissionContext
from .port_manifest import build_port_manifest
from .query_engine import QueryEnginePort
from .remote_runtime import run_remote_mode, run_ssh_mode, run_teleport_mode
from .runtime import PortRuntime
from .session_store import load_session
from .setup import run_setup
from .tool_pool import assemble_tool_pool
from .tools import execute_tool, get_tool, get_tools, render_tool_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Python porting workspace for the Forge CLI effort')
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('summary', help='render a Markdown summary of the Python porting workspace')
    subparsers.add_parser('manifest', help='print the current Python workspace manifest')
    subparsers.add_parser('parity-audit', help='compare the Python workspace against the local ignored TypeScript archive when available')
    subparsers.add_parser('setup-report', help='render the startup/prefetch setup report')
    subparsers.add_parser('command-graph', help='show command graph segmentation')
    subparsers.add_parser('tool-pool', help='show assembled tool pool with default settings')
    subparsers.add_parser('bootstrap-graph', help='show the mirrored bootstrap/runtime graph stages')
    list_parser = subparsers.add_parser('subsystems', help='list the current Python modules in the workspace')
    list_parser.add_argument('--limit', type=int, default=32)

    commands_parser = subparsers.add_parser('commands', help='list mirrored command entries from the archived snapshot')
    commands_parser.add_argument('--limit', type=int, default=20)
    commands_parser.add_argument('--query')
    commands_parser.add_argument('--no-plugin-commands', action='store_true')
    commands_parser.add_argument('--no-skill-commands', action='store_true')

    tools_parser = subparsers.add_parser('tools', help='list mirrored tool entries from the archived snapshot')
    tools_parser.add_argument('--limit', type=int, default=20)
    tools_parser.add_argument('--query')
    tools_parser.add_argument('--simple-mode', action='store_true')
    tools_parser.add_argument('--no-mcp', action='store_true')
    tools_parser.add_argument('--deny-tool', action='append', default=[])
    tools_parser.add_argument('--deny-prefix', action='append', default=[])

    route_parser = subparsers.add_parser('route', help='route a prompt across mirrored command/tool inventories')
    route_parser.add_argument('prompt')
    route_parser.add_argument('--limit', type=int, default=5)

    bootstrap_parser = subparsers.add_parser('bootstrap', help='build a runtime-style session report from the mirrored inventories')
    bootstrap_parser.add_argument('prompt')
    bootstrap_parser.add_argument('--limit', type=int, default=5)

    loop_parser = subparsers.add_parser('turn-loop', help='run a small stateful turn loop for the mirrored runtime')
    loop_parser.add_argument('prompt')
    loop_parser.add_argument('--limit', type=int, default=5)
    loop_parser.add_argument('--max-turns', type=int, default=3)
    loop_parser.add_argument('--structured-output', action='store_true')

    flush_parser = subparsers.add_parser('flush-transcript', help='persist and flush a temporary session transcript')
    flush_parser.add_argument('prompt')

    load_session_parser = subparsers.add_parser('load-session', help='load a previously persisted session')
    load_session_parser.add_argument('session_id')

    remote_parser = subparsers.add_parser('remote-mode', help='simulate remote-control runtime branching')
    remote_parser.add_argument('target')
    ssh_parser = subparsers.add_parser('ssh-mode', help='simulate SSH runtime branching')
    ssh_parser.add_argument('target')
    teleport_parser = subparsers.add_parser('teleport-mode', help='simulate teleport runtime branching')
    teleport_parser.add_argument('target')
    direct_parser = subparsers.add_parser('direct-connect-mode', help='simulate direct-connect runtime branching')
    direct_parser.add_argument('target')
    deep_link_parser = subparsers.add_parser('deep-link-mode', help='simulate deep-link runtime branching')
    deep_link_parser.add_argument('target')

    show_command = subparsers.add_parser('show-command', help='show one mirrored command entry by exact name')
    show_command.add_argument('name')
    show_tool = subparsers.add_parser('show-tool', help='show one mirrored tool entry by exact name')
    show_tool.add_argument('name')

    exec_command_parser = subparsers.add_parser('exec-command', help='execute a mirrored command shim by exact name')
    exec_command_parser.add_argument('name')
    exec_command_parser.add_argument('prompt')

    exec_tool_parser = subparsers.add_parser('exec-tool', help='execute a mirrored tool shim by exact name')
    exec_tool_parser.add_argument('name')
    exec_tool_parser.add_argument('payload')

    # -- Forge self-improvement commands ------------------------------------
    improve_parser = subparsers.add_parser('forge-improve', help='start the self-improvement experiment loop')
    improve_parser.add_argument('--max-iterations', type=int, default=None, help='maximum number of iterations (default: run until converged)')
    improve_parser.add_argument('--parallel', type=int, default=10, help='number of parallel VMs/tasks (default: 10)')
    improve_parser.add_argument('--no-sandbox', action='store_true', help='disable MicroVM sandbox, use plain subprocesses')

    bench_parser = subparsers.add_parser('forge-bench', help='run the benchmark task suite once and print results')
    bench_parser.add_argument('--parallel', type=int, default=10, help='number of parallel VMs/tasks (default: 10)')
    bench_parser.add_argument('--no-sandbox', action='store_true', help='disable MicroVM sandbox, use plain subprocesses')

    subparsers.add_parser('forge-score', help='show the current experiment score history')
    subparsers.add_parser('forge-experiment-log', help='print the raw results.tsv experiment log')
    subparsers.add_parser('forge-sandbox-status', help='check MicroVM sandbox availability and configuration')

    init_tasks_parser = subparsers.add_parser('forge-init-tasks', help='scaffold a tasks/ directory with an example task')
    init_tasks_parser.add_argument('--force', action='store_true', help='overwrite existing example task')

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = build_port_manifest()
    if args.command == 'summary':
        print(QueryEnginePort(manifest).render_summary())
        return 0
    if args.command == 'manifest':
        print(manifest.to_markdown())
        return 0
    if args.command == 'parity-audit':
        print(run_parity_audit().to_markdown())
        return 0
    if args.command == 'setup-report':
        print(run_setup().as_markdown())
        return 0
    if args.command == 'command-graph':
        print(build_command_graph().as_markdown())
        return 0
    if args.command == 'tool-pool':
        print(assemble_tool_pool().as_markdown())
        return 0
    if args.command == 'bootstrap-graph':
        print(build_bootstrap_graph().as_markdown())
        return 0
    if args.command == 'subsystems':
        for subsystem in manifest.top_level_modules[: args.limit]:
            print(f'{subsystem.name}\t{subsystem.file_count}\t{subsystem.notes}')
        return 0
    if args.command == 'commands':
        if args.query:
            print(render_command_index(limit=args.limit, query=args.query))
        else:
            commands = get_commands(include_plugin_commands=not args.no_plugin_commands, include_skill_commands=not args.no_skill_commands)
            output_lines = [f'Command entries: {len(commands)}', '']
            output_lines.extend(f'- {module.name} — {module.source_hint}' for module in commands[: args.limit])
            print('\n'.join(output_lines))
        return 0
    if args.command == 'tools':
        if args.query:
            print(render_tool_index(limit=args.limit, query=args.query))
        else:
            permission_context = ToolPermissionContext.from_iterables(args.deny_tool, args.deny_prefix)
            tools = get_tools(simple_mode=args.simple_mode, include_mcp=not args.no_mcp, permission_context=permission_context)
            output_lines = [f'Tool entries: {len(tools)}', '']
            output_lines.extend(f'- {module.name} — {module.source_hint}' for module in tools[: args.limit])
            print('\n'.join(output_lines))
        return 0
    if args.command == 'route':
        matches = PortRuntime().route_prompt(args.prompt, limit=args.limit)
        if not matches:
            print('No mirrored command/tool matches found.')
            return 0
        for match in matches:
            print(f'{match.kind}\t{match.name}\t{match.score}\t{match.source_hint}')
        return 0
    if args.command == 'bootstrap':
        print(PortRuntime().bootstrap_session(args.prompt, limit=args.limit).as_markdown())
        return 0
    if args.command == 'turn-loop':
        results = PortRuntime().run_turn_loop(args.prompt, limit=args.limit, max_turns=args.max_turns, structured_output=args.structured_output)
        for idx, result in enumerate(results, start=1):
            print(f'## Turn {idx}')
            print(result.output)
            print(f'stop_reason={result.stop_reason}')
        return 0
    if args.command == 'flush-transcript':
        engine = QueryEnginePort.from_workspace()
        engine.submit_message(args.prompt)
        path = engine.persist_session()
        print(path)
        print(f'flushed={engine.transcript_store.flushed}')
        return 0
    if args.command == 'load-session':
        session = load_session(args.session_id)
        print(f'{session.session_id}\n{len(session.messages)} messages\nin={session.input_tokens} out={session.output_tokens}')
        return 0
    if args.command == 'remote-mode':
        print(run_remote_mode(args.target).as_text())
        return 0
    if args.command == 'ssh-mode':
        print(run_ssh_mode(args.target).as_text())
        return 0
    if args.command == 'teleport-mode':
        print(run_teleport_mode(args.target).as_text())
        return 0
    if args.command == 'direct-connect-mode':
        print(run_direct_connect(args.target).as_text())
        return 0
    if args.command == 'deep-link-mode':
        print(run_deep_link(args.target).as_text())
        return 0
    if args.command == 'show-command':
        module = get_command(args.name)
        if module is None:
            print(f'Command not found: {args.name}')
            return 1
        print('\n'.join([module.name, module.source_hint, module.responsibility]))
        return 0
    if args.command == 'show-tool':
        module = get_tool(args.name)
        if module is None:
            print(f'Tool not found: {args.name}')
            return 1
        print('\n'.join([module.name, module.source_hint, module.responsibility]))
        return 0
    if args.command == 'exec-command':
        result = execute_command(args.name, args.prompt)
        print(result.message)
        return 0 if result.handled else 1
    if args.command == 'exec-tool':
        result = execute_tool(args.name, args.payload)
        print(result.message)
        return 0 if result.handled else 1

    # -- Forge self-improvement handlers ------------------------------------
    if args.command == 'forge-improve':
        from .self_improve import ExperimentLoop
        loop = ExperimentLoop(
            use_sandbox=not args.no_sandbox,
            parallel=args.parallel,
        )
        mode = 'subprocess' if args.no_sandbox else ('microvm' if loop._sandbox and loop._sandbox.is_available() else 'subprocess (fallback)')
        print(f'Execution mode: {mode}  parallel={args.parallel}')
        results = loop.run(max_iterations=args.max_iterations)
        for r in results:
            status = 'KEPT' if r.kept else 'DISCARDED'
            print(f'[{status}] iteration {r.iteration}: avg_score={r.avg_score:.3f}  '
                  f'passed={r.passed}/{r.total}  commit={r.commit}')
            print(f'         {r.description}')
        if not results:
            print('No iterations executed.')
        return 0
    if args.command == 'forge-bench':
        from .self_improve import ExperimentLoop
        loop = ExperimentLoop(
            use_sandbox=not args.no_sandbox,
            parallel=args.parallel,
        )
        mode = 'subprocess' if args.no_sandbox else ('microvm' if loop._sandbox and loop._sandbox.is_available() else 'subprocess (fallback)')
        print(f'Execution mode: {mode}  parallel={args.parallel}')
        results = loop.run_benchmark()
        for r in results:
            status = 'PASS' if r['passed'] else 'FAIL'
            print(f'[{status}] {r["name"]}  score={r["score"]:.2f}  duration={r["duration"]:.1f}s')
            if not r['passed']:
                print(f'       {r["output"][:200]}')
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        print(f'\n{passed}/{total} tasks passed')
        return 0
    if args.command == 'forge-score':
        from .self_improve import ExperimentLoop
        loop = ExperimentLoop()
        print(loop.show_scores())
        return 0
    if args.command == 'forge-experiment-log':
        from .self_improve import ExperimentLoop
        loop = ExperimentLoop()
        loop._setup()
        if loop._history.results_path.exists():
            print(loop._history.results_path.read_text())
        else:
            print('No experiment log found. Run forge-improve first.')
        return 0
    if args.command == 'forge-sandbox-status':
        from .self_improve import MicroVMSandbox
        sandbox = MicroVMSandbox()
        info = sandbox.status()
        print(f'MicroVM Sandbox Status')
        print(f'  Binary:       {info["binary"]}')
        print(f'  Kernel:       {info["kernel"]}')
        print(f'  Rootfs:       {info["rootfs"]}')
        print(f'  Mode:         {info["mode"]}')
        print(f'  Max parallel: {info["max_parallel"]}')
        print(f'  Memory/VM:    {info["memory_mb"]}MB')
        print(f'  VM timeout:   {info["vm_timeout"]}s')
        if not info['available']:
            print(f'\nTo enable MicroVM isolation:')
            print(f'  1. Install: cargo install --git https://github.com/quantumnic/microvm microvm')
            print(f'  2. Place a RISC-V Linux kernel at ~/.forge/vm/Image')
            print(f'  3. Optionally add rootfs at ~/.forge/vm/rootfs.img')
        elif info['kernel'] == 'not configured':
            print(f'\nmicrovm found but no kernel configured.')
            print(f'  Place a RISC-V Linux kernel at ~/.forge/vm/Image')
            print(f'  Or set FORGE_VM_KERNEL=/path/to/Image')
        return 0
    if args.command == 'forge-init-tasks':
        import shutil
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        tasks_dir = project_root / 'tasks' / 'example-task'
        if tasks_dir.exists() and not args.force:
            print(f'Example task already exists at {tasks_dir}. Use --force to overwrite.')
            return 1
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'task.toml').write_text(
            '[task]\nname = "example-task"\n'
            'description = "Write a function that returns the nth Fibonacci number"\n'
            'timeout = 60\n'
        )
        (tasks_dir / 'instruction.md').write_text(
            '# Task: Fibonacci Function\n\n'
            'Write a Python file `solution.py` that contains a function `fibonacci(n)` '
            'which returns the nth Fibonacci number (0-indexed).\n\n'
            '- fibonacci(0) = 0\n- fibonacci(1) = 1\n- fibonacci(10) = 55\n\n'
            'The function should handle n >= 0.\n'
        )
        tests_dir = tasks_dir / 'tests'
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_script = tests_dir / 'test.sh'
        test_script.write_text(
            '#!/usr/bin/env bash\nset -e\ncd "$(dirname "$0")/.."\n'
            'python3 -c "\nfrom solution import fibonacci\n'
            "assert fibonacci(0) == 0, f'fibonacci(0) = {fibonacci(0)}'\n"
            "assert fibonacci(1) == 1, f'fibonacci(1) = {fibonacci(1)}'\n"
            "assert fibonacci(10) == 55, f'fibonacci(10) = {fibonacci(10)}'\n"
            "assert fibonacci(20) == 6765, f'fibonacci(20) = {fibonacci(20)}'\n"
            "print('All tests passed!')\n\"\n"
        )
        test_script.chmod(0o755)
        print(f'Scaffolded example task at {tasks_dir}')
        return 0

    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
