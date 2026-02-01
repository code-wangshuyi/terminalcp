# bash completion for terminalcp

_terminalcp_sessions() {
    local sessions
    sessions=$(terminalcp list 2>/dev/null | sed -n 's/^  \([^ ]\+\).*/\1/p')
    echo "$sessions"
}

_terminalcp() {
    local cur prev words cword
    if type _init_completion &>/dev/null; then
        _init_completion || return
    else
        COMPREPLY=()
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    local commands="list ls start stop attach stdout stream stdin resize term-size completion version kill-server"
    local global_opts="--mcp --server"

    # First argument: command or global option
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$commands $global_opts" -- "$cur"))
        return
    fi

    local cmd="${words[1]}"

    case "$cmd" in
        list|ls|version|kill-server)
            # No further arguments
            ;;
        start)
            # start <session-id> <command> — no completions (user-defined)
            ;;
        stop|attach|term-size)
            if [[ $cword -eq 2 ]]; then
                local sessions
                sessions=$(_terminalcp_sessions)
                COMPREPLY=($(compgen -W "$sessions" -- "$cur"))
            fi
            ;;
        stdout)
            if [[ $cword -eq 2 ]]; then
                local sessions
                sessions=$(_terminalcp_sessions)
                COMPREPLY=($(compgen -W "$sessions" -- "$cur"))
            fi
            # cword 3 = lines (numeric, no completion)
            ;;
        stream)
            if [[ $cword -eq 2 ]]; then
                local sessions
                sessions=$(_terminalcp_sessions)
                COMPREPLY=($(compgen -W "$sessions" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "--since-last --with-ansi" -- "$cur"))
            fi
            ;;
        stdin)
            if [[ $cword -eq 2 ]]; then
                local sessions
                sessions=$(_terminalcp_sessions)
                COMPREPLY=($(compgen -W "$sessions" -- "$cur"))
            fi
            ;;
        resize)
            if [[ $cword -eq 2 ]]; then
                local sessions
                sessions=$(_terminalcp_sessions)
                COMPREPLY=($(compgen -W "$sessions" -- "$cur"))
            fi
            # cword 3 = cols, cword 4 = rows (numeric, no completion)
            ;;
        completion)
            if [[ "$prev" == "--shell" ]]; then
                COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "--shell" -- "$cur"))
            fi
            ;;
    esac
}

complete -F _terminalcp terminalcp
