# Contributing

We welcome contributions to add more Qiniu Cloud product skills.

## What Makes a Good Skill

A good candidate:

- Covers a Qiniu Cloud product or tool with a CLI or API interface
- Is reusable across many scenarios (not a one-off task)
- Has clear command patterns that an AI agent can follow

## Skill Structure

Each skill lives in its own directory under `skills/`:

```
skills/
└── <skill-name>/
    ├── SKILL.md                # Skill definition (required)
    ├── references/             # Supporting docs (optional)
    │   └── install.md
    └── examples/               # Interaction examples (optional)
        └── conversation-flow.md
```

### SKILL.md Format

```yaml
---
name: skill-name
description: >
  One-line description of what the skill does. Keep it concise for
  leaderboard display on skills.sh.
type: tool
best_for:
  - "Primary use case 1"
  - "Primary use case 2"
scenarios:
  - "Concrete example scenario 1"
  - "Concrete example scenario 2"
---

# Skill Title

Skill instructions for the AI agent...
```

### Required Frontmatter Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier (lowercase, hyphens allowed) |
| `description` | Brief description for discovery and search (English recommended) |

### Recommended Frontmatter Fields

| Field | Description |
|-------|-------------|
| `type` | Skill type: `tool`, `component`, `workflow` |
| `best_for` | List of primary use cases |
| `scenarios` | Concrete usage scenarios |

### Skill Content Sections

A well-structured SKILL.md should include:

1. **Prerequisites** - Setup requirements and install instructions
2. **Command Reference** - Organized command documentation
3. **Intent Mapping** - User intent to command mapping table
4. **Safety Rules** - Dangerous vs safe operations classification
5. **Output Format** - Expected output formatting guidance
6. **Error Handling** - Common errors and resolution steps

## How to Contribute

### Option 1: Open an Issue

Describe the Qiniu product or tool you'd like to see covered. We'll discuss scope and approach.

### Option 2: Submit a Pull Request

1. Fork this repository
2. Create a branch: `git checkout -b add-<skill-name>`
3. Add your skill under `skills/<skill-name>/`
4. Ensure `SKILL.md` has valid YAML frontmatter with `name` and `description`
5. Test with: `npx skills add ./ --list` (should discover your skill)
6. Submit a pull request

### Quality Checklist

- [ ] SKILL.md has valid YAML frontmatter with `name` and `description`
- [ ] Commands are accurate and tested against the latest tool version
- [ ] Dangerous operations are clearly marked with safety warnings
- [ ] Error handling covers common failure scenarios
- [ ] Examples show realistic usage (not generic placeholders)

## Style Guidelines

- Skill body content can be in Chinese (targeting Qiniu Cloud users)
- Frontmatter `description` should be in English (for skills.sh discovery)
- Keep commands copy-paste ready
- Use tables for structured reference data
- Classify operations as safe/dangerous to guide agent behavior

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
