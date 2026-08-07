use colored::Colorize;

pub fn print_progress(msg: &str) {
    println!("{}", msg.cyan());
}

pub fn print_success(msg: &str) {
    println!("{}", msg.green());
}

pub fn print_warning(msg: &str) {
    eprintln!("{}", msg.yellow());
}

pub fn print_error(msg: &str) {
    eprintln!("{}", msg.red());
}

pub fn print_knowledge_suggestion(name: &str, year: u16) {
    println!(
        "🧠 {} (discovered {})",
        name.bold().green(),
        year.to_string().dimmed()
    );
}

pub fn print_help_heading(title: &str) {
    println!("\n{}", title.bold().underline());
}

pub fn print_command(name: &str, description: &str) {
    println!("  {:<20} {}", name.cyan(), description);
}
