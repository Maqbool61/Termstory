from typing import List
from termstory.models import Command, Session

def create_sessions(commands: List[Command], gap_threshold: int = 1800) -> List[Session]:
    """Group sorted commands into sessions based on time-gap threshold (default 30 min)"""
    if not commands:
        return []
        
    # Ensure commands are sorted by timestamp
    sorted_cmds = sorted(commands, key=lambda x: x.timestamp)
    
    sessions = []
    current_commands = [sorted_cmds[0]]
    session_id = 1
    
    for cmd in sorted_cmds[1:]:
        if (cmd.timestamp - current_commands[-1].timestamp) > gap_threshold:
            # Create session for the accumulated commands
            start_time = current_commands[0].timestamp
            end_time = current_commands[-1].timestamp
            duration_seconds = max(0, end_time - start_time)
            
            session = Session(
                id=session_id,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                project_id=None,
                commands=current_commands
            )
            # Update FK references
            for c in current_commands:
                c.session_id = session_id
                
            sessions.append(session)
            session_id += 1
            current_commands = [cmd]
        else:
            current_commands.append(cmd)
            
    # Add final session
    if current_commands:
        start_time = current_commands[0].timestamp
        end_time = current_commands[-1].timestamp
        duration_seconds = max(0, end_time - start_time)
        
        session = Session(
            id=session_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            project_id=None,
            commands=current_commands
        )
        # Update FK references
        for c in current_commands:
            c.session_id = session_id
            
        sessions.append(session)
        
    return sessions
