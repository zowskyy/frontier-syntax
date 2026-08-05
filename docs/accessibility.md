# Frontier Accessibility Guide

## Screen Reader Support

- CLI output uses structured JSON for `frontier knowledge query` and `frontier mcp list`
- Dashboard at `chat_scrub/dashboard.html` uses semantic HTML headings

## Voice Interface (Planned)

- Lighthouse conversational core supports natural language via `frontier_agent.py`
- Example: `python3 frontier_agent.py "explain ReDoS mitigation"`

## Keyboard Navigation

- All CLI commands accessible without mouse
- REPL: `cargo run --bin frontier -- shell`

## High-Contrast / Reduced Motion

- Dashboard CSS in `chat_scrub/dashboard.html` — dark theme by default
- No auto-playing animations in verification scripts

## BCI Integration (Roadmap)

- Symbiotic learner module (`frontier/learning/symbiotic_learner.fr`) designed for direct knowledge exchange
- JIT knowledge (`frontier/knowledge/just_in_time.fr`) supports topic-based queries without visual UI

## Testing Accessibility Modes

```bash
python3 scripts/frontier_know.py "accessibility features"
cargo run --bin frontier -- knowledge query "accessibility"
```
