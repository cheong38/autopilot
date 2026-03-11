# Ingest Formats

PRD parsing rules per input format. Referenced by Step 1 (INGEST).

## Markdown Files (`.md`)

**Detection**: File path ends with `.md`.

**Parsing rules**:
- `# Heading` → Feature / epic name
- `## Sub-heading` → User story or sub-feature
- Bullet lists under headings → Acceptance criteria
- `> Blockquote` → Constraints or notes
- Code blocks → Technical specifications
- Tables → Data models or configuration matrices

**Extract**:
1. Walk headings depth-first
2. For each leaf heading, collect bullets as acceptance criteria
3. Tag blockquotes as constraints
4. Tag code blocks as technical specs

## Text Files (`.txt`)

**Detection**: File path ends with `.txt`.

**Parsing rules**:
- Numbered items → Features
- Indented sub-items → Acceptance criteria
- Lines starting with `NOTE:` or `CONSTRAINT:` → Constraints
- Empty lines → Section separators

## PDF Files (`.pdf`)

**Detection**: File path ends with `.pdf`.

**Parsing rules**:
- Use Read tool with `pages` parameter for large PDFs
- Read first 5 pages to identify structure
- Apply markdown-like heuristics to extracted text
- Tables may need special handling — extract as structured data

## URLs

**Detection**: Input starts with `http://` or `https://`.

**Parsing rules**:
- Use WebFetch to retrieve content
- HTML converted to markdown automatically
- Apply markdown parsing rules to result
- If content is too large, request summary via WebFetch prompt

## Free Text

**Detection**: Input is neither a file path nor a URL.

**Parsing rules**:
- Treat entire input as requirements text
- Split by sentence boundaries
- Each sentence or bullet = one potential requirement
- Group related sentences into features

## Output Format

All formats produce the same normalized output:

```json
[
  {
    "id": "R-001",
    "text": "User can log in with email and password",
    "type_hint": "story",
    "confidence": 95,
    "source_line": "## Login Feature"
  }
]
```

Fields:
- `id`: Sequential R-NNN identifier
- `text`: Normalized requirement text
- `type_hint`: Suggested issue type (story/task/bug)
- `confidence`: Initial confidence score (0-100)
- `source_line`: Original line/heading from PRD for traceability
