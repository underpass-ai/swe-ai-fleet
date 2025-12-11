#!/usr/bin/env python3
"""Monitor gráfico del proceso de deliberación en tiempo real.

Este script monitorea los logs de Kubernetes y muestra el estado del proceso
de deliberación de forma visual, incluyendo:
- Estado de la ceremonia
- Progreso de agentes
- Eventos NATS
- Respuestas de LLM

Uso:
    python scripts/monitoring/deliberation_monitor.py --ceremony-id BRC-xxx
    python scripts/monitoring/deliberation_monitor.py --follow
"""

import argparse
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    from rich.layout import Layout
    from rich import box
except ImportError:
    print("❌ Error: rich no está instalado. Instala con: pip install rich")
    sys.exit(1)


@dataclass
class AgentStatus:
    """Estado de un agente individual."""

    agent_id: str
    role: str
    status: str = "pending"  # pending, running, completed, failed
    duration_ms: int = 0
    timestamp: str = ""
    proposal_preview: str = ""


@dataclass
class DeliberationState:
    """Estado de una deliberación."""

    task_id: str
    ceremony_id: str = ""
    story_id: str = ""
    role: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    expected_agents: int = 0
    received_agents: int = 0
    agents: dict[str, AgentStatus] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    error: str = ""


@dataclass
class FlowStep:
    """Paso en el flujo de deliberación."""

    step_name: str
    status: str = "pending"  # pending, in_progress, completed, failed
    timestamp: str = ""
    details: str = ""
    service: str = ""


@dataclass
class FlowState:
    """Estado del flujo completo para una deliberación."""

    ceremony_id: str
    story_id: str
    role: str
    task_id: str
    steps: dict[str, FlowStep] = field(default_factory=dict)
    current_step: str = ""


@dataclass
class MonitorState:
    """Estado global del monitor."""

    ceremonies: dict[str, dict[str, DeliberationState]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    flows: dict[str, FlowState] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)


class LogParser:
    """Parser de logs de Kubernetes."""

    def __init__(self, namespace: str = "swe-ai-fleet"):
        """Inicializar parser."""
        self.namespace = namespace
        self.console = Console()

    def get_logs(
        self,
        service: str,
        since: str = "5m",
        tail: int = 1000,
    ) -> list[str]:
        """Obtener logs de un servicio."""
        try:
            cmd = [
                "kubectl",
                "logs",
                "-n",
                self.namespace,
                "-l",
                f"app={service}",
                "--tail",
                str(tail),
                "--since",
                since,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                return []
            return result.stdout.splitlines()
        except Exception as e:
            self.console.print(f"[red]Error obteniendo logs: {e}[/red]")
            return []

    def parse_agent_response(self, line: str) -> dict[str, Any] | None:
        """Parsear línea de log de respuesta de agente."""
        # Formato: [timestamp] [LEVEL] service: [task_id] Received response from agent-xxx
        pattern = r"\[([^\]]+)\]\s+\[(\w+)\]\s+[^:]+:\s+\[([^\]]+)\]\s+Received response from (\S+)"
        match = re.search(pattern, line)
        if match:
            return {
                "type": "agent_response",
                "timestamp": match.group(1),
                "task_id": match.group(3),
                "agent_id": match.group(4),
            }
        return None

    def parse_deliberation_complete(self, line: str) -> dict[str, Any] | None:
        """Parsear línea de log de deliberación completada."""
        # Formato: [task_id] ✅ Deliberation complete: X/Y responses
        pattern = r"\[([^\]]+)\]\s+✅\s+Deliberation complete:\s+(\d+)/(\d+)\s+responses"
        match = re.search(pattern, line)
        if match:
            return {
                "type": "deliberation_complete",
                "task_id": match.group(1),
                "received": int(match.group(2)),
                "expected": int(match.group(3)),
            }
        return None

    def parse_published_event(self, line: str) -> dict[str, Any] | None:
        """Parsear línea de log de evento publicado."""
        # Formato: [task_id] 📢 Published planning.backlog_review.story.reviewed
        pattern = r"\[([^\]]+)\]\s+📢\s+Published\s+(\S+)"
        match = re.search(pattern, line)
        if match:
            return {
                "type": "event_published",
                "task_id": match.group(1),
                "subject": match.group(2),
            }
        return None

    def parse_received_event(self, line: str) -> dict[str, Any] | None:
        """Parsear línea de log de evento recibido."""
        # Formato: 📥 Received backlog review story.reviewed event: ceremony=xxx, story=xxx
        pattern = r"📥\s+Received\s+backlog review\s+story\.reviewed\s+event:\s+ceremony=([^,]+),\s+story=([^,]+),\s+role=([^,]+)"
        match = re.search(pattern, line)
        if match:
            return {
                "type": "event_received",
                "ceremony_id": match.group(1).strip(),
                "story_id": match.group(2).strip(),
                "role": match.group(3).strip(),
            }
        return None

    def extract_task_id_info(self, task_id: str) -> dict[str, str]:
        """Extraer información de task_id (ceremony, story, role)."""
        # Formato: ceremony-{id}:story-{id}:role-{role}
        result = {
            "ceremony_id": "",
            "story_id": "",
            "role": "",
        }
        if ":story-" in task_id and ":role-" in task_id:
            parts = task_id.split(":")
            for part in parts:
                if part.startswith("ceremony-"):
                    result["ceremony_id"] = part.replace("ceremony-", "")
                elif part.startswith("story-"):
                    result["story_id"] = part.replace("story-", "")
                elif part.startswith("role-"):
                    result["role"] = part.replace("role-", "")
        return result


class DeliberationMonitor:
    """Monitor de deliberaciones."""

    def __init__(
        self,
        namespace: str = "swe-ai-fleet",
        ceremony_id: str | None = None,
    ):
        """Inicializar monitor."""
        self.namespace = namespace
        self.ceremony_id = ceremony_id
        self.parser = LogParser(namespace)
        self.state = MonitorState()
        self.console = Console()

    def update_state(self) -> None:
        """Actualizar estado desde logs."""
        # Obtener logs de orchestrator y planning
        orchestrator_logs = self.parser.get_logs("orchestrator", since="10m")
        planning_logs = self.parser.get_logs("planning", since="10m")

        # Parsear eventos
        for line in orchestrator_logs + planning_logs:
            # Parsear respuesta de agente
            agent_event = self.parser.parse_agent_response(line)
            if agent_event:
                self._handle_agent_response(agent_event)
                continue

            # Parsear deliberación completada
            complete_event = self.parser.parse_deliberation_complete(line)
            if complete_event:
                self._handle_deliberation_complete(complete_event)
                continue

            # Parsear evento publicado
            published_event = self.parser.parse_published_event(line)
            if published_event:
                self._handle_event_published(published_event)
                continue

            # Parsear evento recibido
            received_event = self.parser.parse_received_event(line)
            if received_event:
                self._handle_event_received(received_event)
                continue

        self.state.last_update = datetime.now()

    def _handle_agent_response(self, event: dict[str, Any]) -> None:
        """Manejar respuesta de agente."""
        task_id = event["task_id"]
        agent_id = event["agent_id"]
        info = self.parser.extract_task_id_info(task_id)

        # Filtrar por ceremony_id si está especificado
        if self.ceremony_id and info["ceremony_id"] != self.ceremony_id:
            return

        ceremony_id = info["ceremony_id"] or "unknown"
        role = info["role"] or "unknown"

        if ceremony_id not in self.state.ceremonies:
            self.state.ceremonies[ceremony_id] = {}

        if task_id not in self.state.ceremonies[ceremony_id]:
            self.state.ceremonies[ceremony_id][task_id] = DeliberationState(
                task_id=task_id,
                ceremony_id=ceremony_id,
                story_id=info["story_id"],
                role=role,
                status="in_progress",
            )

        deliberation = self.state.ceremonies[ceremony_id][task_id]

        # Extraer role del agent_id (formato: agent-{role}-{number})
        agent_role = role
        if "-" in agent_id:
            parts = agent_id.split("-")
            if len(parts) >= 2:
                agent_role = parts[1].upper()

        if agent_id not in deliberation.agents:
            deliberation.agents[agent_id] = AgentStatus(
                agent_id=agent_id,
                role=agent_role,
                status="completed",
                timestamp=event["timestamp"],
            )
            deliberation.received_agents += 1
        else:
            deliberation.agents[agent_id].status = "completed"
            deliberation.agents[agent_id].timestamp = event["timestamp"]

    def _handle_deliberation_complete(self, event: dict[str, Any]) -> None:
        """Manejar deliberación completada."""
        task_id = event["task_id"]
        info = self.parser.extract_task_id_info(task_id)

        ceremony_id = info["ceremony_id"] or "unknown"

        if ceremony_id in self.state.ceremonies:
            if task_id in self.state.ceremonies[ceremony_id]:
                deliberation = self.state.ceremonies[ceremony_id][task_id]
                deliberation.status = "completed"
                deliberation.received_agents = event["received"]
                deliberation.expected_agents = event["expected"]
                deliberation.completed_at = datetime.now().isoformat()

    def _handle_event_published(self, event: dict[str, Any]) -> None:
        """Manejar evento publicado."""
        self.state.events.append(
            {
                "type": "published",
                "task_id": event["task_id"],
                "subject": event["subject"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        # Mantener solo los últimos 20 eventos
        if len(self.state.events) > 20:
            self.state.events = self.state.events[-20:]

    def _handle_event_received(self, event: dict[str, Any]) -> None:
        """Manejar evento recibido."""
        self.state.events.append(
            {
                "type": "received",
                "ceremony_id": event["ceremony_id"],
                "story_id": event["story_id"],
                "role": event["role"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        # Mantener solo los últimos 20 eventos
        if len(self.state.events) > 20:
            self.state.events = self.state.events[-20:]

    def render(self) -> Layout:
        """Renderizar interfaz."""
        layout = Layout()

        # Crear layout principal
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        # Header
        header_text = Text("🔍 Deliberation Monitor", style="bold cyan")
        if self.ceremony_id:
            header_text.append(f" | Ceremony: {self.ceremony_id}", style="yellow")
        header_text.append(
            f" | Last update: {self.state.last_update.strftime('%H:%M:%S')}",
            style="dim",
        )
        layout["header"].update(Panel(header_text, box=box.ROUNDED))

        # Main content
        main_layout = Layout()
        main_layout.split_row(
            Layout(name="ceremonies", ratio=2),
            Layout(name="events", ratio=1),
        )
        layout["main"].update(main_layout)

        # Tabla de ceremonias
        ceremonies_table = self._render_ceremonies_table()
        layout["ceremonies"].update(ceremonies_table)

        # Tabla de eventos
        events_table = self._render_events_table()
        layout["events"].update(events_table)

        # Footer
        footer_text = Text("Press Ctrl+C to exit", style="dim")
        layout["footer"].update(Panel(footer_text, box=box.ROUNDED))

        return layout

    def _render_ceremonies_table(self) -> Panel:
        """Renderizar tabla de ceremonias."""
        table = Table(
            title="Ceremonies & Deliberations",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED,
        )
        table.add_column("Ceremony", style="cyan", no_wrap=True)
        table.add_column("Story", style="blue", no_wrap=True)
        table.add_column("Role", style="yellow", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Agents", style="white", justify="right")
        table.add_column("Progress", style="white")

        if not self.state.ceremonies:
            table.add_row("No ceremonies found", "", "", "", "", "")

        for ceremony_id, deliberations in self.state.ceremonies.items():
            if self.ceremony_id and ceremony_id != self.ceremony_id:
                continue

            for task_id, deliberation in deliberations.items():
                # Status color
                status_color = {
                    "pending": "dim white",
                    "in_progress": "yellow",
                    "completed": "green",
                    "failed": "red",
                }.get(deliberation.status, "white")

                status_text = Text(deliberation.status.upper(), style=status_color)

                # Progress bar
                if deliberation.expected_agents > 0:
                    progress = (
                        deliberation.received_agents / deliberation.expected_agents
                    ) * 100
                    progress_text = f"{deliberation.received_agents}/{deliberation.expected_agents} ({progress:.0f}%)"
                else:
                    progress_text = f"{deliberation.received_agents}/?"

                table.add_row(
                    ceremony_id[:20] + "..." if len(ceremony_id) > 20 else ceremony_id,
                    deliberation.story_id[:15] + "..."
                    if len(deliberation.story_id) > 15
                    else deliberation.story_id,
                    deliberation.role,
                    status_text,
                    str(len(deliberation.agents)),
                    progress_text,
                )

        return Panel(table, title="[bold]Ceremonies[/bold]", box=box.ROUNDED)

    def _render_events_table(self) -> Panel:
        """Renderizar tabla de eventos."""
        table = Table(
            title="Recent Events",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED,
        )
        table.add_column("Time", style="dim", no_wrap=True)
        table.add_column("Type", style="cyan")
        table.add_column("Details", style="white")

        if not self.state.events:
            table.add_row("No events", "", "")

        # Mostrar eventos más recientes primero
        for event in reversed(self.state.events[-10:]):
            event_time = event.get("timestamp", "")
            if event_time:
                try:
                    dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                    event_time = dt.strftime("%H:%M:%S")
                except Exception:
                    pass

            event_type = event.get("type", "unknown")
            if event_type == "published":
                details = f"Published {event.get('subject', '')}"
            elif event_type == "received":
                details = f"Received: {event.get('role', '')} review"
            else:
                details = str(event)

            table.add_row(event_time, event_type.upper(), details)

        return Panel(table, title="[bold]Events[/bold]", box=box.ROUNDED)


def main() -> None:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Monitor gráfico del proceso de deliberación"
    )
    parser.add_argument(
        "--ceremony-id",
        type=str,
        help="ID de la ceremonia a monitorear (opcional)",
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="swe-ai-fleet",
        help="Namespace de Kubernetes (default: swe-ai-fleet)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Intervalo de actualización en segundos (default: 2)",
    )

    args = parser.parse_args()

    monitor = DeliberationMonitor(
        namespace=args.namespace, ceremony_id=args.ceremony_id
    )
    console = Console()

    try:
        with Live(
            monitor.render(),
            refresh_per_second=1,
            screen=True,
        ) as live:
            while True:
                monitor.update_state()
                live.update(monitor.render())
                time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor detenido[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()


