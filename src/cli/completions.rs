const COMMANDS: &[&str] = &[
    "parse",
    "parse-v2",
    "resolve",
    "hash",
    "gen-artifacts",
    "fuzz",
    "migrate",
    "verify",
    "run",
    "compile",
    "knowledge",
    "config",
    "shell",
    "watch",
    "completions",
    "help",
    "--help",
    "-h",
];

pub fn generate(shell: &str) -> Result<String, String> {
    match shell {
        "bash" => Ok(generate_bash()),
        "zsh" => Ok(generate_zsh()),
        "fish" => Ok(generate_fish()),
        other => Err(format!(
            "Unsupported shell: {other}. Supported: bash, zsh, fish"
        )),
    }
}

fn generate_bash() -> String {
    let mut script = String::from(
        r#"_frontier_completions()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="#
    );
    script.push('"');
    script.push_str(&COMMANDS.join(" "));
    script.push_str(
        r#""

    case "${prev}" in
        frontier)
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
        compile)
            COMPREPLY=( $(compgen -f -X '!*.fr' -- "${cur}") )
            return 0
            ;;
        knowledge)
            COMPREPLY=( $(compgen -W "suggest ancestry tradeoffs" -- "${cur}") )
            return 0
            ;;
        config)
            COMPREPLY=( $(compgen -W "init show" -- "${cur}") )
            return 0
            ;;
        completions)
            COMPREPLY=( $(compgen -W "bash zsh fish" -- "${cur}") )
            return 0
            ;;
    esac

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
    fi
}
complete -F _frontier_completions frontier
"#,
    );
    script
}

fn generate_zsh() -> String {
    format!(
        r#"#compdef frontier

_frontier() {{
    local -a commands
    commands=(
        {}
    )

    _arguments -C \
        '1: :->command' \
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[1] in
                compile)
                    _files -g '*.fr'
                    ;;
                knowledge)
                    _values 'subcommand' suggest ancestry tradeoffs
                    ;;
                config)
                    _values 'subcommand' init show
                    ;;
                completions)
                    _values 'shell' bash zsh fish
                    ;;
            esac
            ;;
    esac
}}

_frontier "$@"
"#,
        COMMANDS
            .iter()
            .map(|c| format!("'{c}':'Frontier command'"))
            .collect::<Vec<_>>()
            .join("\n        ")
    )
}

fn generate_fish() -> String {
    let mut script = String::from("complete -c frontier -f\n");
    for cmd in COMMANDS {
        script.push_str(&format!("complete -c frontier -n '__fish_use_subcommand' -a '{cmd}'\n"));
    }
    script.push_str("complete -c frontier -n '__fish_seen_subcommand_from knowledge' -a 'suggest ancestry tradeoffs'\n");
    script.push_str("complete -c frontier -n '__fish_seen_subcommand_from config' -a 'init show'\n");
    script.push_str("complete -c frontier -n '__fish_seen_subcommand_from completions' -a 'bash zsh fish'\n");
    script.push_str("complete -c frontier -n '__fish_seen_subcommand_from compile' -a '(__fish_complete_suffix .fr)'\n");
    script
}
