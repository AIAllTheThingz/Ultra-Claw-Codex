from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.commands import PORTED_COMMANDS
from src.parity_audit import run_parity_audit
from src.port_manifest import build_port_manifest
from src.query_engine import QueryEnginePort
from src.server.web_ui import (
    PROMPT_PAGE,
    advertised_urls,
    bootstrap_prompt_payload,
    build_overview_payload,
    claw_prompt_payload,
    claw_runtime_payload,
    local_ipv4_addresses,
    route_prompt_payload,
    search_commands_payload,
    search_tools_payload,
)
from src.tools import PORTED_TOOLS


class PortingWorkspaceTests(unittest.TestCase):
    def test_manifest_counts_python_files(self) -> None:
        manifest = build_port_manifest()
        self.assertGreaterEqual(manifest.total_python_files, 20)
        self.assertTrue(manifest.top_level_modules)

    def test_query_engine_summary_mentions_workspace(self) -> None:
        summary = QueryEnginePort.from_workspace().render_summary()
        self.assertIn('Python Porting Workspace Summary', summary)
        self.assertIn('Command surface:', summary)
        self.assertIn('Tool surface:', summary)

    def test_cli_summary_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'summary'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Python Porting Workspace Summary', result.stdout)

    def test_parity_audit_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'parity-audit'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Parity Audit', result.stdout)

    def test_root_file_coverage_is_complete_when_local_archive_exists(self) -> None:
        audit = run_parity_audit()
        if audit.archive_present:
            self.assertEqual(audit.root_file_coverage[0], audit.root_file_coverage[1])
            self.assertGreaterEqual(audit.directory_coverage[0], 28)
            self.assertGreaterEqual(audit.command_entry_ratio[0], 150)
            self.assertGreaterEqual(audit.tool_entry_ratio[0], 100)

    def test_command_and_tool_snapshots_are_nontrivial(self) -> None:
        self.assertGreaterEqual(len(PORTED_COMMANDS), 150)
        self.assertGreaterEqual(len(PORTED_TOOLS), 100)

    def test_commands_and_tools_cli_run(self) -> None:
        commands_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'commands', '--limit', '5', '--query', 'review'],
            check=True,
            capture_output=True,
            text=True,
        )
        tools_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'tools', '--limit', '5', '--query', 'MCP'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Command entries:', commands_result.stdout)
        self.assertIn('Tool entries:', tools_result.stdout)

    def test_subsystem_packages_expose_archive_metadata(self) -> None:
        from src import assistant, bridge, utils

        self.assertGreater(assistant.MODULE_COUNT, 0)
        self.assertGreater(bridge.MODULE_COUNT, 0)
        self.assertGreater(utils.MODULE_COUNT, 100)
        self.assertTrue(utils.SAMPLE_FILES)

    def test_route_and_show_entry_cli_run(self) -> None:
        route_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'route', 'review MCP tool', '--limit', '5'],
            check=True,
            capture_output=True,
            text=True,
        )
        show_command = subprocess.run(
            [sys.executable, '-m', 'src.main', 'show-command', 'review'],
            check=True,
            capture_output=True,
            text=True,
        )
        show_tool = subprocess.run(
            [sys.executable, '-m', 'src.main', 'show-tool', 'MCPTool'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('review', route_result.stdout.lower())
        self.assertIn('review', show_command.stdout.lower())
        self.assertIn('mcptool', show_tool.stdout.lower())

    def test_bootstrap_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'bootstrap', 'review MCP tool', '--limit', '5'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Runtime Session', result.stdout)
        self.assertIn('Startup Steps', result.stdout)
        self.assertIn('Routed Matches', result.stdout)

    def test_bootstrap_session_tracks_turn_state(self) -> None:
        from src.runtime import PortRuntime

        session = PortRuntime().bootstrap_session('review MCP tool', limit=5)
        self.assertGreaterEqual(len(session.turn_result.matched_tools), 1)
        self.assertIn('Prompt:', session.turn_result.output)
        self.assertGreaterEqual(session.turn_result.usage.input_tokens, 1)

    def test_exec_command_and_tool_cli_run(self) -> None:
        command_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'exec-command', 'review', 'inspect security review'],
            check=True,
            capture_output=True,
            text=True,
        )
        tool_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'exec-tool', 'MCPTool', 'fetch resource list'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Mirrored command 'review'", command_result.stdout)
        self.assertIn("Mirrored tool 'MCPTool'", tool_result.stdout)

    def test_setup_report_and_registry_filters_run(self) -> None:
        setup_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'setup-report'],
            check=True,
            capture_output=True,
            text=True,
        )
        command_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'commands', '--limit', '5', '--no-plugin-commands'],
            check=True,
            capture_output=True,
            text=True,
        )
        tool_result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'tools', '--limit', '5', '--simple-mode', '--no-mcp'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Setup Report', setup_result.stdout)
        self.assertIn('Command entries:', command_result.stdout)
        self.assertIn('Tool entries:', tool_result.stdout)

    def test_load_session_cli_runs(self) -> None:
        from src.runtime import PortRuntime

        session = PortRuntime().bootstrap_session('review MCP tool', limit=5)
        session_id = Path(session.persisted_session_path).stem
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'load-session', session_id],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn(session_id, result.stdout)
        self.assertIn('messages', result.stdout)

    def test_tool_permission_filtering_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'tools', '--limit', '10', '--deny-prefix', 'mcp'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Tool entries:', result.stdout)
        self.assertNotIn('MCPTool', result.stdout)

    def test_turn_loop_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'turn-loop', 'review MCP tool', '--max-turns', '2', '--structured-output'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('## Turn 1', result.stdout)
        self.assertIn('stop_reason=', result.stdout)

    def test_remote_mode_clis_run(self) -> None:
        remote_result = subprocess.run([sys.executable, '-m', 'src.main', 'remote-mode', 'workspace'], check=True, capture_output=True, text=True)
        ssh_result = subprocess.run([sys.executable, '-m', 'src.main', 'ssh-mode', 'workspace'], check=True, capture_output=True, text=True)
        teleport_result = subprocess.run([sys.executable, '-m', 'src.main', 'teleport-mode', 'workspace'], check=True, capture_output=True, text=True)
        self.assertIn('mode=remote', remote_result.stdout)
        self.assertIn('mode=ssh', ssh_result.stdout)
        self.assertIn('mode=teleport', teleport_result.stdout)

    def test_flush_transcript_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'flush-transcript', 'review MCP tool'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('flushed=True', result.stdout)

    def test_command_graph_and_tool_pool_cli_run(self) -> None:
        command_graph = subprocess.run([sys.executable, '-m', 'src.main', 'command-graph'], check=True, capture_output=True, text=True)
        tool_pool = subprocess.run([sys.executable, '-m', 'src.main', 'tool-pool'], check=True, capture_output=True, text=True)
        self.assertIn('Command Graph', command_graph.stdout)
        self.assertIn('Tool Pool', tool_pool.stdout)

    def test_setup_report_mentions_deferred_init(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.main', 'setup-report'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Deferred init:', result.stdout)
        self.assertIn('plugin_init=True', result.stdout)

    def test_execution_registry_runs(self) -> None:
        from src.execution_registry import build_execution_registry

        registry = build_execution_registry()
        self.assertGreaterEqual(len(registry.commands), 150)
        self.assertGreaterEqual(len(registry.tools), 100)
        self.assertIn('Mirrored command', registry.command('review').execute('review security'))
        self.assertIn('Mirrored tool', registry.tool('MCPTool').execute('fetch mcp resources'))

    def test_bootstrap_graph_and_direct_modes_run(self) -> None:
        graph_result = subprocess.run([sys.executable, '-m', 'src.main', 'bootstrap-graph'], check=True, capture_output=True, text=True)
        direct_result = subprocess.run([sys.executable, '-m', 'src.main', 'direct-connect-mode', 'workspace'], check=True, capture_output=True, text=True)
        deep_link_result = subprocess.run([sys.executable, '-m', 'src.main', 'deep-link-mode', 'workspace'], check=True, capture_output=True, text=True)
        self.assertIn('Bootstrap Graph', graph_result.stdout)
        self.assertIn('mode=direct-connect', direct_result.stdout)
        self.assertIn('mode=deep-link', deep_link_result.stdout)

    def test_web_ui_payloads_expose_workspace_data(self) -> None:
        overview = build_overview_payload()
        self.assertGreaterEqual(overview['manifest']['total_python_files'], 20)
        self.assertGreaterEqual(overview['commands']['total'], 150)
        self.assertGreaterEqual(overview['tools']['total'], 100)

        commands = search_commands_payload('review', limit=5)
        tools = search_tools_payload('MCP', limit=5)
        route = route_prompt_payload('review MCP tool flow', limit=5)
        bootstrap = bootstrap_prompt_payload('review MCP tool flow', limit=5)

        self.assertTrue(any('review' in entry['name'].lower() for entry in commands['entries']))
        self.assertTrue(any('mcp' in entry['name'].lower() for entry in tools['entries']))
        self.assertTrue(route['matches'])
        self.assertIn('Prompt:', bootstrap['turn_output'])
        self.assertIn('Runtime Session', bootstrap['markdown'])

    def test_web_ui_network_helpers_cover_lan_and_local_modes(self) -> None:
        localhost_urls = advertised_urls('127.0.0.1', 8765)
        self.assertEqual(localhost_urls, ['http://127.0.0.1:8765'])

        lan_urls = advertised_urls('0.0.0.0', 8765)
        self.assertTrue(lan_urls)
        self.assertEqual(lan_urls[0], 'http://127.0.0.1:8765')
        self.assertTrue(all(url.startswith('http://') for url in lan_urls))

        addresses = local_ipv4_addresses()
        self.assertTrue(all(not address.startswith('127.') for address in addresses))

    def test_claw_runtime_payload_detects_built_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            binary = repo_root / 'rust' / 'target' / 'debug' / 'claw'
            binary.parent.mkdir(parents=True)
            binary.write_text('')
            runtime = claw_runtime_payload(repo_root)
            self.assertTrue(runtime['available'])
            self.assertEqual(runtime['strategy'], 'binary')
            self.assertTrue(runtime['command_path'].endswith('claw'))

    def test_claw_prompt_payload_uses_binary_and_loads_project_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            rust_root = repo_root / 'rust'
            binary = rust_root / 'target' / 'debug' / 'claw'
            binary.parent.mkdir(parents=True)
            binary.write_text('')
            (rust_root / '.env').write_text('ANTHROPIC_API_KEY=test-key\\n')

            captured: dict[str, object] = {}

            def fake_runner(command, **kwargs):
                captured['command'] = command
                captured['cwd'] = kwargs['cwd']
                captured['env'] = kwargs['env']
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout='{"message":"live claw ok"}',
                    stderr='',
                )

            payload = claw_prompt_payload(
                'summarize the repo',
                model='sonnet',
                permission_mode='read-only',
                repo_root=repo_root,
                runner=fake_runner,
            )

            self.assertTrue(payload['ok'])
            self.assertEqual(payload['message'], 'live claw ok')
            self.assertEqual(captured['cwd'], str(rust_root))
            self.assertIn('--output-format', captured['command'])
            self.assertEqual(captured['env']['ANTHROPIC_API_KEY'], 'test-key')

    def test_prompt_page_exposes_live_claw_workspace(self) -> None:
        self.assertIn('Claw Prompt Workspace', PROMPT_PAGE)
        self.assertIn('/api/claw', PROMPT_PAGE)
        self.assertIn('Recent Runs', PROMPT_PAGE)
        self.assertIn('Ctrl+Enter', PROMPT_PAGE)


if __name__ == '__main__':
    unittest.main()
