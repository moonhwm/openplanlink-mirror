# Style Contract: AI Persona Documents

## Reference Source

- **Source type**: Instruction-only (derived from professional document best practices and persona definition conventions)
- **Primary language**: Chinese (CJK) or English, depending on user query
- **Document type**: Professional structured document with clear hierarchy

## Typography System

### Font Strategy

- **CJK content**: Use a single CJK-capable sans-serif font family consistently across the entire document.
  - Primary recommendation: `Noto Sans CJK SC` (or `Microsoft YaHei`, `PingFang SC`, `Source Han Sans SC`)
  - Fallback: `SimHei`, `SimSun`
- **Latin-only content**: Use a clean sans-serif font family.
  - Primary recommendation: `Inter`, `Segoe UI`, `Arial`, or `Helvetica`
- **Mixed CJK + Latin**: Use a CJK font that has good Latin glyph integration (e.g., `Noto Sans CJK SC`, `Microsoft YaHei`) for all text. Do not mix Latin-only and CJK-only fonts in different paragraphs.

### Heading Hierarchy

| Level | Size | Weight | Usage |
|---|---|---|---|
| Document Title | 18-20pt | Bold | Main document title on cover/header |
| Heading 1 | 16pt | Bold | Major sections (Identity, Personality, etc.) |
| Heading 2 | 13-14pt | Bold | Sub-sections (Key Traits, Greeting Patterns, etc.) |
| Heading 3 | 12pt | Bold | Sub-sub-sections (individual traits, examples) |
| Body Text | 11pt | Regular | Main content |
| Caption/Note | 10pt | Regular | Annotations, metadata, change log entries |

### Text Spacing

- **Line spacing**: 1.15-1.5 for body text
- **Paragraph spacing**: 6-8pt after each paragraph
- **Heading spacing**: 12pt before, 6pt after headings
- **Section spacing**: 18-24pt between major sections

## Color Palette

### Primary Colors

| Role | Color | Usage |
|---|---|---|
| Primary accent | #2B579A (deep blue) | Section headings, key labels |
| Secondary accent | #5B9BD5 (medium blue) | Sub-headings, links |
| Body text | #333333 (near black) | All body content |
| Secondary text | #666666 (dark gray) | Captions, metadata, notes |
| Light background | #F5F5F5 (light gray) | Example dialogue blocks, callout boxes |
| Border/divider | #CCCCCC (medium gray) | Table borders, section dividers |

### Usage Rules

- Use primary accent color for all Heading 1 elements
- Use secondary accent color for Heading 2 elements
- Body text always uses near-black (#333333)
- Sample interaction blocks use light gray background (#F5F5F5) with 8pt padding
- Behavioral rules (dos/don'ts) use subtle left border accent (4pt, primary color)

## Page Layout

### Margins

- Top: 2.5cm (1 inch)
- Bottom: 2.5cm (1 inch)
- Left: 2.5cm (1 inch)
- Right: 2.5cm (1 inch)

### Page Composition

- **Title page** (optional for short documents): Centered title, subtitle, version, date
- **Content pages**: Left-aligned text, consistent indentation for hierarchical lists
- **Header/footer**: Document title in header (left), page number in footer (center or right)

### Whitespace

- Generous whitespace between sections to improve readability
- Avoid dense blocks of text — break into bullet points or structured lists
- Use tables for trait comparisons or rule sets where appropriate

## Visual Treatment of Special Elements

### Sample Interaction Blocks

```
Background: #F5F5F5
Padding: 10pt all sides
Border: none or 1pt solid #E0E0E0
Label: "Example N: [Scenario Name]" in bold, secondary accent color
User input prefix: "User:" in bold
Persona response prefix: "Persona:" in bold, primary accent color
```

### Behavioral Rule Lists

```
Required behaviors (✓):
- Left border: 4pt solid #2B579A (primary accent)
- Background: none or very subtle #F0F7FF

Prohibited behaviors (✗):
- Left border: 4pt solid #CC0000 (subtle red)
- Background: none or very subtle #FFF0F0
```

### Trait Cards

```
Each trait presented as:
- Trait name: Heading 3 style
- Description: Body text, indented
- Example: Body text in italics, indented further, with label "Example:"
```

### Tables

- Use for structured comparisons (e.g., query type → response pattern mapping)
- Header row: Primary accent background with white text
- Alternate rows: White and very light gray (#FAFAFA)
- Borders: 1pt solid #DDDDDD
- Cell padding: 6pt

## Language-Specific Adaptations

### Chinese (CJK) Content

- Use full-width punctuation (。，！？；：""''（）【】)
- No extra space after punctuation
- Paragraph indentation: 2em (two Chinese character widths) for traditional Chinese formatting, OR no indentation with paragraph spacing for modern formatting
- Numbered lists: Use Chinese numerals (一、二、三) or Arabic numerals (1. 2. 3.) based on formality preference
- Section numbering: Use Arabic numerals (1., 1.1, 1.1.1) for consistency

### English Content

- Use standard English punctuation
- Paragraph indentation: none (use paragraph spacing instead)
- Numbered lists: Arabic numerals (1. 2. 3.)
- Section numbering: Arabic numerals (1., 1.1, 1.1.1)

## Output Format Specifics

### DOCX Output

- Use built-in heading styles (Heading 1, Heading 2, Heading 3) for proper navigation pane support
- Use list styles for bullet points and numbered lists
- Define custom styles for sample interaction blocks and trait cards
- Enable table of contents generation based on heading structure
- Page setup: A4 or Letter based on user preference (default: A4)

### PDF Output

- Preserve all style attributes from DOCX
- Ensure embedded fonts for CJK characters
- Maintain hyperlinks if cross-references are used
- Optimize for screen viewing (balanced margins, clear hierarchy)
