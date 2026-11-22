use clap::Parser;
use research_engine::cli::{run, Cli};
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
        }
        Err(error) => {
            eprintln!("{}", error.what);
            eprintln!("Why: {}", error.why);
            eprintln!("Fix: {}", error.fix);
            std::process::exit(1);
        }
    }
}
