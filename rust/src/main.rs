use clap::Parser;
use research_engine::cli::{run, Cli, Commands};
use research_engine::integrity;
use research_engine::util::to_stable_json;

fn main() {
    let cli = Cli::parse();
    match run(&cli) {
        Ok(output) => {
            if cli.json {
                print!("{}", to_stable_json(&output.json));
            } else {
                print!("{}", output.text);
            }
            // Python's check exits 1 when the graph has error-level findings.
            if matches!(cli.command, Commands::Check)
                && output.json.as_array().map(|items| integrity::has_errors(items)).unwrap_or(false)
            {
                std::process::exit(1);
            }
        }
        Err(error) => {
            eprintln!("{}", error.what);
            eprintln!("Why: {}", error.why);
            eprintln!("Fix: {}", error.fix);
            std::process::exit(1);
        }
    }
}
