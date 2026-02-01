#compdef terminalcp

_terminalcp_sessions() {
  local -a sessions
  sessions=(${(f)"$(terminalcp list --ids 2>/dev/null)"})
  _values 'session' $sessions
}

_terminalcp() {
  local -a commands
  commands=(
    'list:List all active sessions'
    'ls:List all active sessions'
    'start:Start a new named session'
    'stop:Stop session(s)'
    'attach:Attach to a session'
    'stdout:Get terminal output (rendered)'
    'stream:Get raw output stream'
    'stdin:Send input to a session'
    'resize:Resize terminal dimensions'
    'term-size:Get terminal size'
    'completion:Install shell completion'
    'version:Show client and server versions'
    'kill-server:Shutdown the terminal server'
  )

  _arguments -C \
    '(--server)--mcp[Run as MCP server on stdio]' \
    '(--mcp)--server[Run as terminal server daemon]' \
    '1:command:->command' \
    '*::arg:->args'

  case $state in
    command)
      _describe 'command' commands
      ;;
    args)
      local cmd=$words[1]
      case $cmd in
        list|ls)
          _arguments '--ids[Only show session ids]'
          ;;
        start)
          _arguments \
            '1:session-id:' \
            '2:command:' \
            '*:args:'
          ;;
        stop)
          _arguments '1:session:_terminalcp_sessions'
          ;;
        attach)
          _arguments '1:session:_terminalcp_sessions'
          ;;
        stdout)
          _arguments \
            '1:session:_terminalcp_sessions' \
            '2:lines:'
          ;;
        stream)
          _arguments \
            '1:session:_terminalcp_sessions' \
            '--since-last[Only show new output]' \
            '--with-ansi[Keep ANSI codes]'
          ;;
        stdin)
          _arguments \
            '1:session:_terminalcp_sessions' \
            '*:input:'
          ;;
        resize)
          _arguments \
            '1:session:_terminalcp_sessions' \
            '2:cols:' \
            '3:rows:'
          ;;
        term-size)
          _arguments '1:session:_terminalcp_sessions'
          ;;
        completion)
          _arguments '--shell[Shell type]:shell:(bash zsh fish)'
          ;;
        version|kill-server)
          ;;
      esac
      ;;
  esac
}

if (( $+functions[compdef] )); then
  compdef _terminalcp terminalcp
fi

_terminalcp "$@"
