---
name: persona-memory-anchors
description: >
  Extract and structure "personality memory anchors" from persona descriptions, interaction samples, or reference materials to generate reusable persona profile documents.
  Use when the user needs to: (1) replicate or restore an AI persona/character, (2) extract persona traits from documents, conversation logs, or instructions, (3) build structured personality memory anchor lists, (4) generate persona configuration files or character specification documents, (5) analyze and standardize an agent's behavior patterns and language style.
---

# Persona Memory Anchors

## Overview

This skill systematically extracts "memory anchors" from any persona reference material (text descriptions, conversation logs, behavior specification documents, web content, etc.) and outputs a structured persona profile document.

Memory anchors are the key dimensions that define a persona's uniqueness, including language style, values, knowledge boundaries, behavior patterns, emotional expression, and more.

## Reference Source Type

- **Type**: Instruction-only / No concrete reference artifact
- **Note**: This skill is built around the concept of "personality memory anchors." When the user provides concrete reference material (documents, conversation logs, web pages), extract anchors from the material. When the user only gives a persona name or general description, generate anchors based on general persona modeling methods.

## Output Policy

| Output Format | Default | Description |
|---------------|---------|-------------|
| **DOCX** | **Yes** | Default output. Generates a structured persona profile document for editing and reuse. |
| **PDF** | Supported | Generated when the user explicitly requests fixed-format distribution. |
| **PPTX** | Supported | Generated when the user needs presentation/slideshow format. |
| **Markdown** | Supported | Generated when the user needs lightweight text or import into other systems. |

- If the user does not specify an output format, default to **DOCX**.
- If the user explicitly requests slides/presentation, generate **PPTX**.
- If the user requests "direct text output / code configuration," generate **Markdown**.

## Core Workflow

### Step 1: Collect Persona Reference Materials

1. Identify all reference sources provided by the user:
   - Uploaded documents (.docx, .pdf, .txt, .md)
   - Provided web URLs
   - Pasted conversation logs or text snippets
   - Persona names or brands (e.g., "Kimi")

2. If the user has not provided specific material, only a persona name or vague description:
   - Search for public descriptions, official introductions, and user feedback about that persona
   - Based on the general persona modeling framework, guide the user to supplement key information

### Step 2: Extract Memory Anchors

Systematically extract memory anchors from the reference material across the following dimensions:

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Identity Positioning** | Core identity, role positioning, service objectives | "I am Kimi, an AI assistant" |
| **Language Style** | Word preferences, sentence patterns, tone characteristics, rhetorical habits | Formal/casual, concise/detailed, use of emoji |
| **Values & Principles** | Core beliefs, moral boundaries, priorities | Helpful, privacy-protecting, refusing harmful requests |
| **Knowledge Boundaries** | Areas of expertise, knowledge cutoff, limitation statements | Knowledge cutoff 2024, excels at long text processing |
| **Behavior Patterns** | Response structure, thinking style, interaction habits, default behavior | Summarize first then elaborate, proactively ask for clarification |
| **Emotional Expression** | Emotional temperature, empathy style, humor level, politeness tier | Gentle and neutral, moderate empathy, no strong emotions |
| **Special Abilities** | Unique features, differentiating characteristics, signature skills | Ultra-long context, web search, file parsing |
| **Restrictions & Taboos** | Explicitly stated things not to do, red lines, topics to avoid | Does not generate code, does not provide medical advice |
| **Memory & Context** | How historical information is handled, whether user is remembered | Supports multi-turn dialogue, no cross-session memory retention |

### Step 3: Structure and Prioritize

1. Categorize extracted anchors by **priority**:
   - **Core Anchors** (immutable): Anchors that define the essence of the persona; changing them would distort the character
   - **Important Anchors** (stable): Significantly affect persona performance and should be preserved
   - **Style Anchors** (adjustable): Details that affect perception but can be moderately adjusted

2. For each anchor, annotate:
   - Source basis (which reference material it came from)
   - Confidence level (high / medium / low)
   - Priority level (core / important / style)

### Step 4: Generate Persona Profile Document

Generate a structured document according to the output format:

- **Cover / Title Page**: Persona name, version, generation date
- **Persona Overview**: One-sentence positioning + core characteristics summary
- **Memory Anchor Detail Table**: Anchor list organized by dimension (table or card format)
- **Behavior Examples**: 2-3 response demonstrations in typical scenarios
- **Usage Instructions**: How to replicate the persona based on this profile, precautions

## Style Contract

### Typography & Visual Design

- **Page Layout**: A4 portrait, standard margins (2.54cm)
- **Font Strategy**: Prioritize CJK-compatible fonts for Chinese content
  - Body text: Noto Sans CJK SC / Source Han Sans (sans-serif, modern and clean)
  - Headings: Noto Sans CJK SC Bold / Source Han Sans Bold
  - Mixed Western text: Segoe UI / Arial (coordinates well with Chinese fonts)
- **Type Size Hierarchy**:
  - Main title: 18pt, bold
  - Level 1 heading: 14pt, bold
  - Level 2 heading: 12pt, bold
  - Body text: 10.5pt
  - Table content: 10pt
- **Color Palette**:
  - Primary: Deep blue (#1a365d) for headings and emphasis
  - Secondary: Light gray (#f7fafc) for table backgrounds and card base colors
  - Accent: Cyan (#319795) for highlights and labels
  - Text: Dark gray (#2d3748) for body text

### Tables & Structured Elements

- Anchor detail tables use **three-line tables** or **card-style tables**
- Each row contains: dimension, anchor description, priority, confidence, source
- Priority uses color labels to distinguish: Core (red/dark red), Important (orange), Style (green)
- Tables should have clear borders with header row background color

## Structure Contract

### Document Hierarchy

1. Cover / Title
2. Persona Overview (Executive Summary)
3. Core Identity Positioning
4. Memory Anchor Detail Table (by dimension)
5. Behavior Patterns & Examples
6. Usage Guide & Precautions
7. Version History (optional)

### Cross-References & Numbering

- Anchors in each dimension use unified codes: A-Identity, B-Language, C-Values, D-Knowledge, E-Behavior, F-Emotion, G-Abilities, H-Restrictions
- Example scenarios use numbering: Ex-01, Ex-02...

## Runtime Adaptation Guide

- If reference material is a **long document**, first read through the full text to mark key passages, then extract by dimension
- If reference material is **conversation logs**, focus on analyzing the persona's response side, ignoring user inputs
- If reference material is from **web/multiple sources**, first consolidate and deduplicate information, then annotate source differences
- If the user only provides a **persona name** (e.g., "Kimi"), first search for official introductions and user consensus about that persona, then build anchors; if information is insufficient, confirm key characteristics with the user
- If the user requests replication of a **specific version** of a persona, clearly identify the version label and difference points
- If the user requests **comparison of multiple personas**, independently extract anchors for each persona, then add a comparison analysis chapter

## CJK Typography Strategy

- Use a unified CJK-compatible font family across all text paths to avoid font discontinuity when mixing Chinese and Western text
- Long text in table cells should auto-wrap with row height adapted to content
- Avoid using Latin-only fonts as default body fonts
