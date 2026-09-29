---
name: ai-persona-document
description: Create structured AI assistant persona and role-play definition documents in DOCX or PDF format. Use when the user needs to (1) create a persona document that defines how an AI assistant should behave, speak, and respond, (2) define a character role-play profile for AI systems, (3) produce a structured system prompt or custom instructions document, (4) design an AI assistant identity specification with personality traits, communication style, and behavioral guidelines, or (5) create any document that specifies AI persona configuration, role definition, or character behavior patterns. Also triggers for requests involving "role-play", "persona", "character definition", "AI assistant behavior", "system prompt document", or "custom instructions" in DOCX or PDF form.
---

# AI Persona Document

## Overview

This skill creates structured persona definition documents that specify how an AI assistant should behave when adopting a specific role or character. The output is a professional document (DOCX or PDF) containing identity definition, personality profile, communication guidelines, knowledge boundaries, behavioral rules, and sample interactions.

## Reference Source and Output Policy

- **Reference source type**: Instruction-only (derived from persona document best practices)
- **Reference artifact type**: DOCX
- **Reference File Type**: DOCX
- **Supported outputs**: DOCX, PDF
- **Default output**: DOCX (when user does not specify)

If the user explicitly requests PDF, produce PDF. If they explicitly request DOCX, produce DOCX. Otherwise, default to DOCX.

## Workflow

### Step 1: Gather Persona Requirements

Determine from the user query:
- **Persona name / identity**: What character or role should the AI adopt?
- **Source material**: Is this based on an existing character (fiction, history, real person), an original creation, or a professional role?
- **Language**: Primary language for the persona document (default: match user query language; often Chinese for Kimi-style personas)
- **Depth level**: Brief profile (1-2 pages) or comprehensive specification (5+ pages)
- **Target use case**: System prompt, custom instructions, team onboarding, or creative writing reference

### Step 2: Determine Document Scope

Select the appropriate section set based on user needs:

| Use Case | Required Sections |
|---|---|
| Quick persona | Identity, Personality, Communication Style |
| Full character | All sections including Backstory, Relationships, Sample Dialogues |
| Professional role | Identity, Knowledge Scope, Behavioral Rules, Response Patterns |
| System prompt | Identity, Personality, Communication Style, Boundaries, Examples |

### Step 3: Generate Content Following the Structure Contract

Use the section hierarchy and field semantics defined in `references/structure_contract.md`. Populate each section with specific, concrete details rather than generic descriptions.

### Step 4: Apply the Style Contract

Format the document according to `references/style_contract.md`. Ensure:
- Consistent heading hierarchy
- Proper CJK typography when content includes Chinese
- Professional but approachable tone in document design
- Clear visual separation between sections

## Document Section Guide

### Core Sections (Always Include)

1. **Identity & Role Definition**
   - Persona name and title
   - Core role description (1-2 sentences)
   - Self-introduction pattern (how the persona introduces itself)

2. **Personality Profile**
   - 3-5 key personality traits with concrete manifestations
   - Emotional range and expression patterns
   - Humor style and formality level

3. **Communication Style**
   - Typical greeting patterns
   - Response length preferences
   - Language patterns (emoji usage, punctuation style, sentence structure)
   - Tone descriptors (warm, professional, playful, authoritative, etc.)

### Extended Sections (Include When Depth Is Required)

4. **Backstory & Context**
   - Origin story (1-2 paragraphs)
   - Key experiences that shape behavior
   - Current situation or environment

5. **Knowledge Scope**
   - Domains of expertise
   - Explicit knowledge boundaries (what the persona does NOT know)
   - How to handle out-of-scope questions

6. **Behavioral Guidelines**
   - Dos: Required behaviors and response patterns
   - Don'ts: Prohibited behaviors and topics
   - Escalation rules (when to decline or redirect)

7. **Response Patterns**
   - Standard response structure
   - How to handle different query types
   - Special response formats (lists, explanations, creative outputs)

8. **Sample Interactions**
   - 3-5 example dialogues showing the persona in action
   - Each example should demonstrate a different aspect of the persona
   - Include user input and expected persona response

9. **Version & Metadata**
   - Document version
   - Creation date
   - Author/creator
   - Update log (if applicable)

## Language and Typography

- **Primary language**: Match the user query language. If the user writes in Chinese, the persona document should be in Chinese.
- **CJK support**: When generating Chinese content, use CJK-capable fonts throughout the document (e.g., SimHei, SimSun, Microsoft YaHei, or Noto Sans CJK).
- **Mixed content**: For documents with both English and Chinese, maintain consistent font pairing — use a sans-serif CJK font as the primary typeface for both scripts.
- **Heading fonts**: Bold, slightly larger than body text. Use the same font family as body text.
- **Body text**: 11-12pt, 1.15-1.5 line spacing.
- **Sample dialogue formatting**: Use distinct styling (indentation, background shading, or quotation blocks) to visually separate examples from guidelines.

## Quality Guidelines

- Be specific, not vague. Instead of "be friendly," write "greet users warmly with phrases like '很高兴见到你' or '有什么我可以帮你的吗？'"
- Include concrete examples for every abstract trait.
- Define boundaries clearly — what the persona should NOT do is as important as what it should do.
- Ensure consistency across all sections; personality traits should align with communication style and behavioral rules.
- Make sample interactions realistic and representative of the full persona range.

## Reference Files

- **`references/structure_contract.md`**: Detailed section hierarchy, field semantics, and content patterns for persona documents.
- **`references/style_contract.md`**: Typography, color, layout, and visual formatting specifications.

Read the relevant reference file when you need detailed guidance on document structure or visual styling.
