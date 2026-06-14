import os
import json
import webbrowser
from termstory.insights import analyze_all
from termstory.formatter import _is_noise_command
from termstory.database import Database

def get_web_data(db: Database) -> dict:
    """Gather stats, project list, timeline, and AI highlights from the database."""
    # 1. Base Stats
    stats = analyze_all(db)
    
    # Enrich stats with last ingestion time
    stats["last_ingestion_time"] = db.get_last_ingestion_time()

    # 2. Project List
    projects = db.get_all_projects_with_stats()
    projects_data = []
    for p in projects:
        name = p.name
        if not name or name == "General / No Project":
            name = "Other"
        projects_data.append({
            "id": p.id,
            "name": name,
            "path": p.path or "",
            "session_count": p.session_count,
            "total_time": p.total_time,
            "first_seen": p.first_seen,
            "last_seen": p.last_seen
        })
    # Sort projects by total time descending
    projects_data.sort(key=lambda x: x["total_time"], reverse=True)

    # 3. Recent Sessions (last 30 sessions)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sessions ORDER BY start_time DESC LIMIT 30")
    session_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    sessions = db.get_sessions_by_ids(session_ids)
    sessions_data = []
    for s in sessions:
        proj_name = "Other"
        # Find project name
        for p in projects_data:
            if p["id"] == s.project_id:
                proj_name = p["name"]
                break

        # Mapped commits
        commits = []
        for c in s.commits:
            commits.append({
                "hash": c.get("hash", ""),
                "message": c.get("message", ""),
                "cleaned_message": c.get("cleaned_message", "")
            })

        # Mapped commands
        commands = []
        for cmd in s.commands:
            commands.append({
                "command": cmd.command,
                "timestamp": cmd.timestamp,
                "exit_code": cmd.exit_code,
                "is_legacy": cmd.is_legacy,
                "is_noise": _is_noise_command(cmd.command)
            })

        sessions_data.append({
            "id": s.id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration_seconds": s.duration_seconds,
            "project_name": proj_name,
            "ai_summary": s.ai_summary or "",
            "commands": commands,
            "commits": commits,
            "is_legacy": s.is_legacy
        })

    # 4. AI Summary Highlights
    ai_sessions = [s for s in sessions_data if s["ai_summary"]]
    if len(ai_sessions) < 15:
        # Fetch more from DB if we don't have enough in the last 30
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM sessions 
            WHERE ai_summary IS NOT NULL AND ai_summary != '' 
            ORDER BY start_time DESC LIMIT 15
        """)
        extra_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        extra_ids_to_fetch = [eid for eid in extra_ids if eid not in [s["id"] for s in sessions_data]]
        if extra_ids_to_fetch:
            extra_sessions = db.get_sessions_by_ids(extra_ids_to_fetch)
            for s in extra_sessions:
                proj_name = "Other"
                for p in projects_data:
                    if p["id"] == s.project_id:
                        proj_name = p["name"]
                        break

                ai_sessions.append({
                    "id": s.id,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration_seconds": s.duration_seconds,
                    "project_name": proj_name,
                    "ai_summary": s.ai_summary or "",
                    "commands": [],
                    "commits": [],
                    "is_legacy": s.is_legacy
                })

    ai_sessions.sort(key=lambda x: x["start_time"], reverse=True)
    highlights_data = ai_sessions[:15]

    return {
        "stats": stats,
        "projects": projects_data,
        "sessions": sessions_data,
        "highlights": highlights_data
    }

def generate_and_open_report(db: Database) -> None:
    """Generate the HTML report, save it to ~/.termstory/report.html, and open it in the default browser."""
    data = get_web_data(db)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TermStory Web Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0d10;
            --panel-bg: rgba(20, 24, 30, 0.7);
            --panel-border: rgba(255, 255, 255, 0.05);
            --text-primary: #f0f3f6;
            --text-secondary: #8b949e;
            --accent-color: #58a6ff;
            --accent-glow: rgba(88, 166, 255, 0.15);
            --success-color: #3fb950;
            --success-glow: rgba(63, 185, 80, 0.15);
            --warning-color: #d29922;
            --error-color: #f85149;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            --font-title: 'Outfit', sans-serif;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: var(--font-sans);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(219, 39, 119, 0.05) 0px, transparent 50%),
                radial-gradient(at 50% 0%, rgba(56, 189, 248, 0.05) 0px, transparent 50%);
            background-attachment: fixed;
            -webkit-font-smoothing: antialiased;
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-color);
        }}
        ::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        /* Header style */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            flex-wrap: wrap;
            gap: 20px;
        }}
        header h1 {{
            font-family: var(--font-title);
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #fff 30%, #58a6ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .header-meta {{
            text-align: right;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        /* Glassmorphism panel */
        .panel {{
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--panel-border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s ease;
        }}
        .panel:hover {{
            border-color: rgba(88, 166, 255, 0.2);
        }}

        /* KPI grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .kpi-card {{
            position: relative;
            overflow: hidden;
        }}
        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-color), transparent);
        }}
        .kpi-value {{
            font-family: var(--font-title);
            font-size: 2.2rem;
            font-weight: 800;
            margin-top: 8px;
            color: #fff;
        }}
        .kpi-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* Main Grid Layout */
        .main-grid {{
            display: grid;
            grid-template-columns: 1fr 1.6fr;
            gap: 30px;
        }}
        @media (max-width: 1024px) {{
            .main-grid {{
                grid-template-columns: 1fr;
            }}
            header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .header-meta {{
                text-align: left;
            }}
        }}

        /* Active Projects card style */
        .project-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }}
        .project-row:last-child {{
            border-bottom: none;
        }}
        .project-info {{
            flex: 1;
            margin-right: 16px;
        }}
        .project-name-wrapper {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .project-badge {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }}
        .project-name {{
            font-weight: 600;
            color: #fff;
        }}
        .project-path {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 2px;
            word-break: break-all;
        }}
        .project-stats {{
            text-align: right;
            flex-shrink: 0;
        }}
        .project-time {{
            font-weight: 700;
            color: var(--accent-color);
        }}
        .project-sessions {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        .project-bar-container {{
            width: 100%;
            height: 4px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 2px;
            margin-top: 6px;
            overflow: hidden;
        }}
        .project-bar {{
            height: 100%;
            border-radius: 2px;
        }}

        /* AI highlights feed */
        .highlight-card {{
            border-left: 3px solid var(--accent-color);
            padding-left: 16px;
            margin-bottom: 20px;
        }}
        .highlight-header {{
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }}
        .highlight-project {{
            font-weight: 600;
            color: #fff;
        }}
        .highlight-body {{
            font-size: 0.9rem;
            line-height: 1.5;
            color: var(--text-primary);
            white-space: pre-wrap;
        }}

        /* Search bar style */
        .search-container {{
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            align-items: center;
        }}
        .search-input {{
            flex: 1;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 12px 16px;
            color: #fff;
            font-family: var(--font-sans);
            font-size: 0.95rem;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .search-input:focus {{
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }}
        .filter-btn {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--panel-border);
            color: var(--text-secondary);
            border-radius: 8px;
            padding: 12px 16px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .filter-btn.active {{
            background: var(--accent-color);
            border-color: var(--accent-color);
            color: #000;
            font-weight: 600;
        }}

        /* Timeline style */
        .timeline {{
            position: relative;
            padding-left: 32px;
        }}
        .timeline::before {{
            content: '';
            position: absolute;
            top: 8px;
            bottom: 8px;
            left: 11px;
            width: 2px;
            background: rgba(255, 255, 255, 0.05);
        }}
        .timeline-item {{
            position: relative;
            margin-bottom: 30px;
        }}
        .timeline-item:last-child {{
            margin-bottom: 0;
        }}
        .timeline-dot {{
            position: absolute;
            left: -32px;
            top: 6px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-color);
            border: 4px solid var(--bg-color);
            box-shadow: 0 0 0 4px rgba(88, 166, 255, 0.2);
            transition: transform 0.2s;
        }}
        .timeline-item:hover .timeline-dot {{
            transform: scale(1.3);
        }}
        .session-card {{
            padding: 20px;
        }}
        .session-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .session-meta-left {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .session-project-pill {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            color: #fff;
        }}
        .session-time-range {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        .session-duration {{
            font-size: 0.9rem;
            font-weight: 700;
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 10px;
            border-radius: 6px;
        }}

        /* Commits inside session */
        .session-commits {{
            margin: 12px 0;
            padding: 10px 14px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 2px solid var(--success-color);
        }}
        .commit-row {{
            font-family: var(--font-sans);
            font-size: 0.85rem;
            margin-bottom: 6px;
            color: var(--text-primary);
        }}
        .commit-row:last-child {{
            margin-bottom: 0;
        }}
        .commit-hash {{
            font-family: monospace;
            color: var(--success-color);
            margin-right: 6px;
        }}

        /* Commands inside session */
        .commands-toggle {{
            background: none;
            border: none;
            color: var(--accent-color);
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            padding: 0;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-top: 10px;
        }}
        .commands-toggle:hover {{
            text-decoration: underline;
        }}
        .commands-list {{
            display: none;
            margin-top: 10px;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 8px;
            padding: 12px;
            max-height: 250px;
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }}
        .commands-list.open {{
            display: block;
        }}
        .command-item {{
            font-family: monospace;
            font-size: 0.8rem;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            color: #c9d1d9;
            word-break: break-all;
        }}
        .command-item:last-child {{
            border-bottom: none;
        }}
        .command-item.error {{
            color: var(--error-color);
        }}
        .command-item.legacy {{
            color: #8b949e;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>⚡ TermStory Web Report</h1>
                <div style="color: var(--text-secondary); margin-top: 4px;">Developer Memory Engine & Activity Timeline</div>
            </div>
            <div class="header-meta">
                <div>Generated on <span id="generated-date">-</span></div>
                <div style="margin-top: 2px;">Last Ingested: <span id="last-ingested-date">-</span></div>
            </div>
        </header>
        
        <div class="kpi-grid">
            <div class="panel kpi-card">
                <div class="kpi-label">Total Sessions</div>
                <div class="kpi-value" id="kpi-sessions">-</div>
            </div>
            <div class="panel kpi-card">
                <div class="kpi-label">Total Commands</div>
                <div class="kpi-value" id="kpi-commands">-</div>
            </div>
            <div class="panel kpi-card">
                <div class="kpi-label">Total Projects</div>
                <div class="kpi-value" id="kpi-projects">-</div>
            </div>
            <div class="panel kpi-card">
                <div class="kpi-label">Coding Streak</div>
                <div class="kpi-value" id="kpi-streak">-</div>
            </div>
        </div>
        
        <div class="main-grid">
            <div>
                <!-- Left side: Active Projects & AI highlights -->
                <div class="panel" style="margin-bottom: 30px;">
                    <h2 style="font-family: var(--font-title); font-size: 1.3rem; margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
                        <svg style="width: 20px; height: 20px; color: var(--accent-color)" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                        Active Projects
                    </h2>
                    <div id="projects-container"></div>
                </div>
                
                <div class="panel">
                    <h2 style="font-family: var(--font-title); font-size: 1.3rem; margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
                        <svg style="width: 20px; height: 20px; color: var(--success-color)" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        AI Summary Highlights
                    </h2>
                    <div id="highlights-container"></div>
                </div>
            </div>
            
            <div>
                <!-- Right side: Recent Sessions Timeline -->
                <div class="panel" style="margin-bottom: 24px;">
                    <div class="search-container">
                        <input type="text" id="search-bar" class="search-input" placeholder="Search sessions, commands, commits, summaries...">
                        <button id="noise-toggle" class="filter-btn">Show Noise Cmds</button>
                    </div>
                    
                    <h2 style="font-family: var(--font-title); font-size: 1.3rem; margin-top: 0; margin-bottom: 24px;">Recent Work Timeline</h2>
                    <div class="timeline" id="timeline-container"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const reportData = {json.dumps(data)};
        let showNoise = false;
        let searchQuery = "";

        function getProjectColor(name) {{
            let hash = 0;
            for (let i = 0; i < name.length; i++) {{
                hash = name.charCodeAt(i) + ((hash << 5) - hash);
            }}
            const hue = Math.abs(hash % 360);
            return `hsl(${{hue}}, 65%, 55%)`;
        }}

        function formatDuration(seconds) {{
            if (seconds <= 0) return "0s";
            if (seconds < 60) return `${{seconds}}s`;
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const parts = [];
            if (hours > 0) parts.push(`${{hours}}h`);
            if (minutes > 0 || !parts.length) parts.push(`${{minutes}}m`);
            return parts.join(" ");
        }}

        function formatDate(timestamp) {{
            const d = new Date(timestamp * 1000);
            return d.toLocaleDateString(undefined, {{ month: 'short', day: 'numeric', year: 'numeric' }});
        }}

        function formatTime(timestamp) {{
            const d = new Date(timestamp * 1000);
            return d.toLocaleTimeString(undefined, {{ hour: '2-digit', minute: '2-digit' }});
        }}

        function renderProjects() {{
            const container = document.getElementById('projects-container');
            container.innerHTML = "";
            
            if (reportData.projects.length === 0) {{
                container.innerHTML = `<div style="color: var(--text-secondary); font-size: 0.9rem;">No active projects recorded.</div>`;
                return;
            }}
            
            const totalTime = reportData.projects.reduce((acc, p) => acc + p.total_time, 0);
            
            reportData.projects.forEach(p => {{
                const color = getProjectColor(p.name);
                const pct = totalTime > 0 ? (p.total_time / totalTime * 100).toFixed(1) : 0;
                
                const row = document.createElement('div');
                row.className = 'project-row';
                row.innerHTML = `
                    <div class="project-info">
                        <div class="project-name-wrapper">
                            <span class="project-badge" style="background-color: ${{color}}"></span>
                            <span class="project-name">${{p.name}}</span>
                        </div>
                        <div class="project-path">${{p.path || ''}}</div>
                        <div class="project-bar-container">
                            <div class="project-bar" style="width: ${{pct}}%; background-color: ${{color}}"></div>
                        </div>
                    </div>
                    <div class="project-stats">
                        <div class="project-time">${{formatDuration(p.total_time)}}</div>
                        <div class="project-sessions">${{p.session_count}} sessions (${{pct}}%)</div>
                    </div>
                `;
                container.appendChild(row);
            }});
        }}

        function renderHighlights() {{
            const container = document.getElementById('highlights-container');
            container.innerHTML = "";
            
            if (reportData.highlights.length === 0) {{
                container.innerHTML = `<div style="color: var(--text-secondary); font-size: 0.9rem;">No AI summaries generated yet. Run some sessions and enable AI to see highlights!</div>`;
                return;
            }}
            
            reportData.highlights.forEach(h => {{
                const card = document.createElement('div');
                card.className = 'highlight-card';
                card.style.borderLeftColor = getProjectColor(h.project_name);
                card.innerHTML = `
                    <div class="highlight-header">
                        <span class="highlight-project">${{h.project_name}}</span>
                        <span>${{formatDate(h.start_time)}}</span>
                    </div>
                    <div class="highlight-body">${{h.ai_summary}}</div>
                `;
                container.appendChild(card);
            }});
        }}

        function escapeHtml(str) {{
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }}

        function toggleCommands(id) {{
            const el = document.getElementById(`commands-list-${{id}}`);
            if (el) {{
                el.classList.toggle('open');
            }}
        }}

        function renderTimeline() {{
            const container = document.getElementById('timeline-container');
            container.innerHTML = "";
            
            const filtered = reportData.sessions.filter(s => {{
                const matchesSearch = !searchQuery || 
                    s.project_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    s.ai_summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    s.commands.some(c => c.command.toLowerCase().includes(searchQuery.toLowerCase())) ||
                    s.commits.some(c => c.message.toLowerCase().includes(searchQuery.toLowerCase()));
                    
                return matchesSearch;
            }});
            
            if (filtered.length === 0) {{
                container.innerHTML = `<div style="color: var(--text-secondary); text-align: center; padding: 40px 0;">No matching sessions found.</div>`;
                return;
            }}
            
            filtered.forEach(s => {{
                const color = getProjectColor(s.project_name);
                const cmdsToShow = s.commands.filter(c => showNoise || !c.is_noise);
                
                const item = document.createElement('div');
                item.className = 'timeline-item';
                
                let commitsHtml = "";
                if (s.commits && s.commits.length > 0) {{
                    commitsHtml = `
                        <div class="session-commits">
                            ${{s.commits.map(c => `
                                <div class="commit-row">
                                    <span class="commit-hash">${{c.hash.substring(0, 7)}}</span>
                                    <span>${{c.cleaned_message || c.message}}</span>
                                </div>
                            `).join('')}}
                        </div>
                    `;
                }}
                
                let commandsHtml = "";
                if (cmdsToShow.length > 0) {{
                    commandsHtml = `
                        <button class="commands-toggle" onclick="toggleCommands(${{s.id}})">
                            <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                            Show Commands (${{cmdsToShow.length}})
                        </button>
                        <div class="commands-list" id="commands-list-${{s.id}}">
                            ${{cmdsToShow.map(c => {{
                                let cl = 'command-item';
                                if (c.exit_code !== 0) cl += ' error';
                                if (c.is_legacy) cl += ' legacy';
                                return `<div class="${{cl}}">${{escapeHtml(c.command)}}</div>`;
                            }}).join('')}}
                        </div>
                    `;
                }}
                
                let summaryHtml = "";
                if (s.ai_summary) {{
                    summaryHtml = `<div class="highlight-body" style="margin-top: 8px; font-style: italic;">${{s.ai_summary}}</div>`;
                }}
                
                item.innerHTML = `
                    <span class="timeline-dot" style="background-color: ${{color}}; box-shadow: 0 0 0 4px ${{color}}33"></span>
                    <div class="panel session-card">
                        <div class="session-header">
                            <div class="session-meta-left">
                                <span class="session-project-pill" style="background-color: ${{color}}">${{s.project_name}}</span>
                                <span class="session-time-range">${{formatDate(s.start_time)}} at ${{formatTime(s.start_time)}} - ${{formatTime(s.end_time)}}</span>
                            </div>
                            <span class="session-duration">${{formatDuration(s.duration_seconds)}}</span>
                        </div>
                        ${{summaryHtml}}
                        ${{commitsHtml}}
                        ${{commandsHtml}}
                    </div>
                `;
                container.appendChild(item);
            }});
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            document.getElementById('generated-date').textContent = new Date().toLocaleString();
            
            const lastIngested = reportData.stats.last_ingestion_time || 0;
            document.getElementById('last-ingested-date').textContent = lastIngested ? new Date(lastIngested * 1000).toLocaleString() : 'N/A';
            
            document.getElementById('kpi-sessions').textContent = reportData.stats.total_sessions;
            document.getElementById('kpi-commands').textContent = reportData.stats.total_commands;
            document.getElementById('kpi-projects').textContent = reportData.stats.total_projects;
            document.getElementById('kpi-streak').textContent = `${{reportData.stats.streak}} Days`;
            
            const searchInput = document.getElementById('search-bar');
            searchInput.addEventListener('input', (e) => {{
                searchQuery = e.target.value;
                renderTimeline();
            }});
            
            const noiseToggle = document.getElementById('noise-toggle');
            noiseToggle.addEventListener('click', () => {{
                showNoise = !showNoise;
                if (showNoise) {{
                    noiseToggle.textContent = "Hide Noise Cmds";
                    noiseToggle.classList.add('active');
                }} else {{
                    noiseToggle.textContent = "Show Noise Cmds";
                    noiseToggle.classList.remove('active');
                }}
                renderTimeline();
            }});
            
            renderProjects();
            renderHighlights();
            renderTimeline();
        }});
    </script>
</body>
</html>
"""
    
    report_path = os.path.expanduser("~/.termstory/report.html")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"Web report saved to: {report_path}")
    webbrowser.open(f"file://{os.path.abspath(report_path)}")
