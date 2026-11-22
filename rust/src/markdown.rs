//! Markdown-safe rendering and the shared four-character token estimate.
//! Ports `engine/markdown.py` and the budget helpers from `engine/context.py`.

pub const CHARS_PER_TOKEN: usize = 4;
pub const DEFAULT_WIDTH: usize = 160;
pub const RESERVE_TOKENS: usize = 40;

/// Collapse untrusted text to one safe line: no controls, no newlines, capped width.
pub fn sanitize(text: &str, width: usize) -> String {
    let mut cleaned = String::new();
    for c in text.chars() {
        if c == '\r' || c == '\n' || c == '\t' {
            cleaned.push(' ');
            continue;
        }
        // Cc, Cf, Cs, Co, Cn, Zl, Zp are not representable as readable text.
        if c.is_control() || matches!(c, '\u{2028}' | '\u{2029}') {
            continue;
        }
        cleaned.push(c);
    }
    let flat = cleaned.split_whitespace().collect::<Vec<_>>().join(" ");
    if width > 0 && flat.chars().count() > width {
        let prefix: String = flat.chars().take(width.saturating_sub(1)).collect();
        format!("{}…", prefix.trim_end())
    } else {
        flat
    }
}

pub fn cell(text: &str, width: usize) -> String {
    sanitize(text, width).replace('\\', "\\\\").replace('|', "\\|").replace('`', "\\`")
}

pub fn bullet(text: &str, width: usize) -> String {
    sanitize(text, width).replace('`', "\\`")
}

pub fn code(text: &str, width: usize) -> String {
    sanitize(text, width).replace('`', "'")
}

pub fn estimate_tokens(text: &str) -> usize {
    (text.len() + CHARS_PER_TOKEN - 1) / CHARS_PER_TOKEN
}

/// Always keep the anchor line; drop from the end when the budget is exhausted.
pub fn pack(lines: &[String], budget: usize) -> (Vec<String>, usize, usize) {
    assert!(budget > 0, "budget must be positive");
    let available = budget.saturating_sub(RESERVE_TOKENS).max(1);
    let mut kept = Vec::new();
    let mut used = 0usize;
    for (index, line) in lines.iter().enumerate() {
        let cost = estimate_tokens(line) + 1;
        if index == 0 {
            kept.push(line.clone());
            used += cost;
            continue;
        }
        if used + cost > available {
            break;
        }
        kept.push(line.clone());
        used += cost;
    }
    let omitted = lines.len() - kept.len();
    (kept, omitted, used)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_matches_python_shape() {
        assert_eq!(sanitize("  a\n b\t c  ", 160), "a b c");
        assert_eq!(sanitize("abcdef", 3), "ab…");
        assert_eq!(cell("a|b`c", 160), "a\\|b\\`c");
    }

    #[test]
    fn pack_keeps_anchor() {
        let lines = vec!["anchor".to_string(), "second".to_string()];
        let (kept, omitted, _) = pack(&lines, 1);
        assert_eq!(kept, vec!["anchor"]);
        assert_eq!(omitted, 1);
    }
}
