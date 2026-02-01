# fish completion for terminalcp

function __terminalcp_sessions
    terminalcp list --ids 2>/dev/null
end

set -l commands list ls start stop attach stdout stream stdin resize term-size completion version kill-server

# Disable file completions by default
complete -c terminalcp -f

# Global options (only when no subcommand yet)
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -l mcp -d "Run as MCP server on stdio"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -l server -d "Run as terminal server daemon"

# Subcommands
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a list -d "List all active sessions"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a ls -d "List all active sessions"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a start -d "Start a new named session"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a stop -d "Stop session(s)"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a attach -d "Attach to a session"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a stdout -d "Get terminal output (rendered)"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a stream -d "Get raw output stream"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a stdin -d "Send input to a session"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a resize -d "Resize terminal dimensions"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a term-size -d "Get terminal size"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a completion -d "Install shell completion"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a version -d "Show client and server versions"
complete -c terminalcp -n "not __fish_seen_subcommand_from $commands" -a kill-server -d "Shutdown the terminal server"

# Session-based completions
for cmd in stop attach stdout stream stdin resize term-size
    complete -c terminalcp -n "__fish_seen_subcommand_from $cmd" -a "(__terminalcp_sessions)" -d "Session"
end

# List options
complete -c terminalcp -n "__fish_seen_subcommand_from list ls" -l ids -d "Only show session ids"

# Stream options
complete -c terminalcp -n "__fish_seen_subcommand_from stream" -l since-last -d "Only show new output"
complete -c terminalcp -n "__fish_seen_subcommand_from stream" -l with-ansi -d "Keep ANSI codes"

# Completion subcommand options
complete -c terminalcp -n "__fish_seen_subcommand_from completion" -l shell -d "Shell type" -ra "bash zsh fish"
