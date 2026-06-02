import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any

from rich.console import Group
from rich.text import Text
from rich.table import Table

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Header, Footer, Tree, Static, Input
from textual.reactive import reactive

from termstory.models import Session, Project, Command, format_duration
from termstory.database import Database
from termstory.project import disambiguate_project_names
from termstory.formatter import _is_noise_command
from termstory.date_utils import get_current_time


# ==========================================
# 1. HELPER LOGIC FOR STATS & MEMORIES
# ==========================================

def calculate_streak(sessions: List[Session]) -> int:
    """Calculate consecutive active work days ending today or on the last active day."""
    if not sessions:
        return 0
    active_dates = {
        datetime.fromtimestamp(s.start_time).date()
        for s in sessions
    }
    if not active_dates:
        return 0
    
    sorted_dates = sorted(list(active_dates), reverse=True)
    streak = 1
    current_date = sorted_dates[0]
    
    # Allow a gap of at most 1 day (e.g. if today is inactive but yesterday was active, streak is still active)
    today = get_current_time().date()
    if (today - current_date).days > 1:
        return 0
        
    for d in sorted_dates[1:]:
        if (current_date - d).days == 1:
            streak += 1
            current_date = d
        elif (current_date - d).days > 1:
            break
    return streak


def generate_heatmap(sessions: List[Session], days_limit: int = 30) -> str:
    """Generate a GitHub-like 30-day activity matrix representing command volume."""
    now = get_current_time().date()
    day_counts = defaultdict(int)
    for s in sessions:
        s_date = datetime.fromtimestamp(s.start_time).date()
        day_counts[s_date] += len(s.commands)
        
    heatmap_blocks = []
    for i in range(days_limit - 1, -1, -1):
        target_date = now - timedelta(days=i)
        cmd_count = day_counts[target_date]
        if cmd_count == 0:
            heatmap_blocks.append("[grey37]░[/]")
        elif cmd_count < 5:
            heatmap_blocks.append("[green]▄[/]")
        elif cmd_count < 20:
            heatmap_blocks.append("[bold green]■[/]")
        else:
            heatmap_blocks.append("[bold reverse green]█[/]")
            
    return " ".join(heatmap_blocks)


def calculate_dashboard_stats(sessions: List[Session], projects: List[Project]) -> Dict[str, Any]:
    """Calculate cumulative dashboard stats."""
    active_dates = {
        datetime.fromtimestamp(s.start_time).date()
        for s in sessions
    }
    
    streak = calculate_streak(sessions)
    total_seconds = sum(s.duration_seconds for s in sessions)
    total_time_str = format_duration(total_seconds)
    heatmap = generate_heatmap(sessions)
    
    return {
        "total_time": total_time_str,
        "active_days": len(active_dates),
        "streak": streak,
        "projects_count": len(projects),
        "heatmap": heatmap
    }


def get_session_memory_str(session: Session) -> str:
    """Extract a single-line summary memory for the session."""
    if session.commits:
        c = session.commits[0]
        return c.get("cleaned_message") or c.get("message") or "Code commit"
        
    candidates = [cmd.command for cmd in session.commands if not _is_noise_command(cmd.command)]
    if candidates:
        return max(candidates, key=len)
        
    if session.commands:
        return session.commands[-1].command
        
    return "Activity logged"


# ==========================================
# 2. TUI WIDGETS
# ==========================================

class StatsHeader(Static):
    """The cumulative stats header spanning the top of the interface."""
    
    def update_stats(self, stats: Dict[str, Any]) -> None:
        self.update(
            f"[bold cyan]TermStory Dashboard[/bold cyan]  │  "
            f"[bold]Time logged:[/bold] {stats['total_time']}  │  "
            f"[bold]Active Days:[/bold] {stats['active_days']}  │  "
            f"[bold green]Streak:[/bold green] {stats['streak']} Days  │  "
            f"[bold]Projects:[/bold] {stats['projects_count']}\n"
            f"[dim]Activity (Last 30 Days):[/dim] {stats['heatmap']}"
        )


class HistoryTree(Tree):
    """Collapsible date-grouped navigation timeline supporting Vim keys."""
    
    BINDINGS = [
        ("j", "cursor_down", "Cursor Down"),
        ("k", "cursor_up", "Cursor Up"),
    ]
    
    def populate(self, projects: List[Project], sessions: List[Session], search_query: Optional[str] = None) -> None:
        self.clear()
        
        project_map = {p.id: p for p in projects if p.id is not None}
        display_names = disambiguate_project_names(projects)
        
        # Group sessions by calendar day
        sessions_by_day = defaultdict(list)
        for s in sessions:
            day_key = datetime.fromtimestamp(s.start_time).strftime("%b %d, %Y")
            sessions_by_day[day_key].append(s)
            
        # Sort days reverse-chronologically
        sorted_days = sorted(sessions_by_day.keys(), key=lambda d: datetime.strptime(d, "%b %d, %Y"), reverse=True)
        
        for day in sorted_days:
            day_sessions = sessions_by_day[day]
            matched_sessions = []
            
            for s in day_sessions:
                proj = project_map.get(s.project_id)
                proj_name = display_names.get(s.project_id, "Other") if proj else "Other"
                if proj_name == "General / No Project":
                    proj_name = "Other"
                
                memory = get_session_memory_str(s)
                
                # Check if matches query
                if search_query:
                    q = search_query.lower()
                    cmd_match = any(q in cmd.command.lower() for cmd in s.commands)
                    commit_match = any(q in (c.get("message", "") + " " + c.get("cleaned_message", "")).lower() for c in s.commits)
                    if q in proj_name.lower() or q in memory.lower() or cmd_match or commit_match:
                        matched_sessions.append((proj, proj_name, s, memory))
                else:
                    matched_sessions.append((proj, proj_name, s, memory))
                    
            if not matched_sessions:
                continue
                
            day_node = self.root.add(day, expand=True)
            for proj, proj_name, s, memory in matched_sessions:
                start_str = datetime.fromtimestamp(s.start_time).strftime("%H:%M")
                end_str = datetime.fromtimestamp(s.end_time).strftime("%H:%M")
                display_label = f"✨ [bold cyan]{proj_name}[/] ➔ {memory} [dim]({start_str} - {end_str})[/]"
                day_node.add_leaf(display_label, data=(proj, s))


def make_stacked_bar(project_seconds: Dict[str, int], total_seconds: int, width: int = 40) -> Tuple[str, str]:
    """Generate a horizontal stacked progress bar and legend using distinct project colors."""
    if total_seconds <= 0 or not project_seconds:
        return "[grey37]" + "░" * width + "[/]", "[dim]No active time[/]"
        
    sorted_projects = sorted(project_seconds.items(), key=lambda x: x[1], reverse=True)
    colors = ["cyan", "green", "yellow", "magenta", "blue", "red", "white"]
    project_colors = {}
    for idx, (p_name, _) in enumerate(sorted_projects):
        project_colors[p_name] = colors[idx % len(colors)]
        
    bar_str = ""
    legend_parts = []
    remaining_width = width
    
    for p_name, seconds in sorted_projects:
        pct = seconds / total_seconds
        char_count = int(round(pct * width))
        if pct > 0 and char_count == 0 and remaining_width > 0:
            char_count = 1
        char_count = min(char_count, remaining_width)
        remaining_width -= char_count
        
        color = project_colors[p_name]
        bar_str += f"[{color}]" + "█" * char_count + "[/]"
        
        pct_display = int(round(pct * 100))
        legend_parts.append(f"[{color}]■ {p_name} ({pct_display}%)[/]")
        
    if remaining_width > 0:
        bar_str += "[grey37]" + "░" * remaining_width + "[/]"
        
    return bar_str, "  ".join(legend_parts)


class DetailsCanvas(Static):
    """Display overall metrics, dynamic time distribution bar, and Git/Command details."""
    
    def update_view_empty(self) -> None:
        self.update(Text.from_markup("\n\n[dim italic]Select a session node from the explorer to view detailed logs.[/dim italic]"))
        
    def render_time_summary(self, title: str, sessions: List[Session], projects: List[Project]) -> None:
        """STATE A: Time Summary View (Today/Week/Month or overall)"""
        from rich.panel import Panel
        
        elements = []
        
        total_time_seconds = sum(s.duration_seconds for s in sessions)
        total_time_str = format_duration(total_time_seconds)
        
        active_project_ids = {s.project_id for s in sessions if s.project_id is not None}
        active_projects_count = len(active_project_ids)
        total_commits = sum(len(s.commits) for s in sessions)
        
        elements.append(Text.from_markup(f"[bold white]{title}[/bold white]\n"))
        
        # 1. Hero Banner: Side-by-side metric cards
        card1 = Panel(
            Text.from_markup(f"[bold cyan]{total_time_str}[/]\n[dim]Total Time Logged[/]"),
            border_style="bright_black",
            padding=(0, 2),
            expand=True
        )
        card2 = Panel(
            Text.from_markup(f"[bold cyan]{active_projects_count}[/]\n[dim]Active Projects[/]"),
            border_style="bright_black",
            padding=(0, 2),
            expand=True
        )
        card3 = Panel(
            Text.from_markup(f"[bold cyan]{total_commits}[/]\n[dim]Git Commits[/]"),
            border_style="bright_black",
            padding=(0, 2),
            expand=True
        )
        
        cards_table = Table(box=None, show_header=False, padding=0, expand=True)
        cards_table.add_column("c1", ratio=1)
        cards_table.add_column("c2", ratio=1)
        cards_table.add_column("c3", ratio=1)
        cards_table.add_row(card1, card2, card3)
        
        elements.append(cards_table)
        elements.append(Text("\n"))
        
        # 2. Time Distribution Bar
        elements.append(Text.from_markup("[bold]Time Distribution[/bold]\n"))
        display_names = disambiguate_project_names(projects)
        project_seconds = defaultdict(int)
        for s in sessions:
            proj_name = "Other"
            if s.project_id is not None and s.project_id in display_names:
                proj_name = display_names[s.project_id]
                if proj_name == "General / No Project":
                    proj_name = "Other"
            project_seconds[proj_name] += s.duration_seconds
            
        bar, legend = make_stacked_bar(project_seconds, total_time_seconds, width=60)
        elements.append(Text.from_markup(f"{bar}\n\n{legend}\n\n"))
        
        # 3. Session Feed
        elements.append(Text.from_markup("[bold]Activity Feed[/bold]\n"))
        sorted_sessions = sorted(sessions, key=lambda s: s.start_time)
        project_map = {p.id: p for p in projects if p.id is not None}
        
        for s in sorted_sessions:
            proj = project_map.get(s.project_id)
            proj_name = display_names.get(s.project_id, "Other") if proj else "Other"
            if proj_name == "General / No Project":
                proj_name = "Other"
                
            dur_str = format_duration(s.duration_seconds)
            memory = get_session_memory_str(s)
            start_time_str = datetime.fromtimestamp(s.start_time).strftime("%I:%M %p")
            
            feed_item = Text()
            feed_item.append(f"• {start_time_str} ", style="dim")
            feed_item.append(f"{proj_name} ", style="bold cyan" if proj_name != "Other" else "bold green")
            feed_item.append(f"({dur_str})\n", style="dim")
            feed_item.append(f"  └─ ✨ {memory}\n", style="white")
            elements.append(feed_item)
            
        self.update(Group(*elements))
        
    def render_session_details(self, project: Optional[Project], session: Session) -> None:
        elements = []
        
        proj_name = project.name if project else "Other"
        if proj_name == "General / No Project":
            proj_name = "Other"
        proj_path = project.path if project else "N/A"
        
        start_str = datetime.fromtimestamp(session.start_time).strftime("%I:%M %p")
        end_str = datetime.fromtimestamp(session.end_time).strftime("%I:%M %p")
        date_str = datetime.fromtimestamp(session.start_time).strftime("%A, %B %d, %Y")
        duration_str = format_duration(session.duration_seconds)
        
        header = Text()
        header.append(f"📁 PROJECT: {proj_name}\n", style="bold cyan")
        header.append(f"Workspace Path: {proj_path}\n", style="dim")
        header.append(f"Session Window: {date_str} ({start_str} → {end_str}) [{duration_str}]\n", style="dim")
        header.append("─" * 60 + "\n", style="dim")
        elements.append(header)
        
        if session.commits:
            git_section = Text()
            git_section.append("🌿 Git Commits:\n", style="bold green")
            for c in session.commits:
                short_hash = c.get("hash", "")[:7]
                msg = c.get("cleaned_message") or c.get("message") or ""
                git_section.append(f"  • [{short_hash}] ", style="yellow")
                git_section.append(f"{msg}\n", style="white")
            git_section.append("\n")
            elements.append(git_section)
            
        cmd_section = Text()
        cmd_section.append("💻 Command Timeline:\n", style="bold yellow")
        for cmd in session.commands:
            t_str = datetime.fromtimestamp(cmd.timestamp).strftime("%H:%M:%S")
            is_noise = _is_noise_command(cmd.command)
            
            if is_noise:
                cmd_section.append(f"  • {t_str}  {cmd.command}\n", style="dim")
            else:
                cmd_section.append(f"  • {t_str}  ", style="cyan")
                cmd_section.append(f"{cmd.command}\n", style="bold white")
                
        elements.append(cmd_section)
        self.update(Group(*elements))


# ==========================================
# 3. MAIN WORKSPACE APP
# ==========================================

class TermStoryWorkspace(App):
    TITLE = "TermStory — Interactive Dashboard"
    
    BINDINGS = [
        ("q", "quit_app", "Quit"),
        ("escape", "quit_app", "Quit"),
        ("slash", "start_search", "Search"),
    ]
    
    CSS = """
    Screen {
        background: #121214;
        color: #e2e2e9;
    }
    #master-layout {
        layout: grid;
        grid-size: 2 2;
        grid-rows: auto 1fr;
        grid-columns: 35% 65%;
        height: 100%;
    }
    #stats-panel {
        column-span: 2;
        border-bottom: solid #323238;
        padding: 1;
        height: 3;
        background: #1a1a1e;
        color: #e2e2e9;
    }
    #tree-container {
        border-right: solid #323238;
        height: 100%;
    }
    #history-navigator {
        height: 1fr;
        background: #121214;
    }
    #search-box {
        display: none;
        background: #1a1a1e;
        border: solid #323238;
        color: #e2e2e9;
        margin: 1 1 0 1;
    }
    #details-canvas {
        padding: 1 2;
        overflow-y: scroll;
        height: 100%;
        background: #121214;
    }
    """
    
    def __init__(self, db: Database, days_limit: Optional[int] = 30):
        super().__init__()
        self.db = db
        self.days_limit = days_limit
        self.sessions = []
        self.projects = []
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Grid(id="master-layout"):
            yield StatsHeader(id="stats-panel")
            with Vertical(id="tree-container"):
                yield HistoryTree("Timeline Explorer", id="history-navigator")
                yield Input(placeholder="Search sessions... (Esc to clear)", id="search-box")
            yield DetailsCanvas(id="details-canvas")
        yield Footer()
        
    def on_mount(self) -> None:
        if self.days_limit:
            start_ts = int((get_current_time() - timedelta(days=self.days_limit)).timestamp())
        else:
            start_ts = 0
            
        # Get active sessions and projects
        self.sessions = self.db.get_range_sessions(start_ts, int(get_current_time().timestamp()))
        project_ids = list(set(s.project_id for s in self.sessions if s.project_id is not None))
        self.projects = self.db.get_projects_by_ids(project_ids)
        
        # Render top stats header
        stats = calculate_dashboard_stats(self.sessions, self.projects)
        self.query_one("#stats-panel").update_stats(stats)
        
        # Populate history navigator tree
        tree = self.query_one("#history-navigator")
        tree.populate(self.projects, self.sessions)
        
        # Setup initial view as overall dashboard summary
        self.query_one("#details-canvas").render_time_summary("📊 Overall Dashboard Summary", self.sessions, self.projects)
        tree.focus()
        
    def action_quit_app(self) -> None:
        self.exit()
        
    def action_start_search(self) -> None:
        search_box = self.query_one("#search-box")
        search_box.styles.display = "block"
        search_box.focus()
        
    def on_key(self, event) -> None:
        search_box = self.query_one("#search-box")
        if search_box.has_focus:
            if event.key == "escape":
                search_box.value = ""
                search_box.styles.display = "none"
                self.query_one("#history-navigator").focus()
                event.prevent_default()
                event.stop()
                
    def on_input_submitted(self, event: Input.Submitted) -> None:
        search_box = self.query_one("#search-box")
        search_box.styles.display = "none"
        self.query_one("#history-navigator").focus()
        
    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        tree = self.query_one("#history-navigator")
        tree.populate(self.projects, self.sessions, search_query=query)
        
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node_data = event.node.data
        canvas = self.query_one("#details-canvas")
        if node_data:
            project, session = node_data
            canvas.render_session_details(project, session)
        else:
            node_label = str(event.node.label)
            # Filter sessions matching this date
            day_sessions = []
            for s in self.sessions:
                s_date = datetime.fromtimestamp(s.start_time).strftime("%b %d, %Y")
                if s_date == node_label:
                    day_sessions.append(s)
            
            if day_sessions:
                canvas.render_time_summary(f"📅 Daily Overview ({node_label})", day_sessions, self.projects)
            else:
                canvas.render_time_summary("📊 Overall Dashboard Summary", self.sessions, self.projects)
