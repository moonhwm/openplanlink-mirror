# Structure Contract: AI Persona Documents

## Document Hierarchy

```
Document
├── Title Page / Header
│   ├── Document Title (e.g., "Kimi AI Assistant Persona Definition")
│   ├── Version
│   ├── Date
│   └── Author/Creator
├── Section 1: Identity & Role Definition (Heading 1)
│   ├── 1.1 Persona Name (Heading 2)
│   ├── 1.2 Role Summary (Heading 2)
│   ├── 1.3 Self-Introduction Pattern (Heading 2)
│   └── 1.4 Core Identity Statement (Heading 2)
├── Section 2: Personality Profile (Heading 1)
│   ├── 2.1 Key Traits (Heading 2)
│   │   └── Trait cards: Name + Description + Example (Heading 3)
│   ├── 2.2 Emotional Range (Heading 2)
│   └── 2.3 Formality & Humor (Heading 2)
├── Section 3: Communication Style (Heading 1)
│   ├── 3.1 Greeting Patterns (Heading 2)
│   ├── 3.2 Language Characteristics (Heading 2)
│   │   ├── Sentence structure (Heading 3)
│   │   ├── Vocabulary preferences (Heading 3)
│   │   └── Punctuation & emoji usage (Heading 3)
│   ├── 3.3 Response Length & Structure (Heading 2)
│   └── 3.4 Tone Markers (Heading 2)
├── Section 4: Backstory & Context (Heading 1) — optional
│   ├── 4.1 Origin (Heading 2)
│   ├── 4.2 Key Experiences (Heading 2)
│   └── 4.3 Current Context (Heading 2)
├── Section 5: Knowledge Scope (Heading 1)
│   ├── 5.1 Areas of Expertise (Heading 2)
│   ├── 5.2 Knowledge Boundaries (Heading 2)
│   └── 5.3 Handling Unknowns (Heading 2)
├── Section 6: Behavioral Guidelines (Heading 1)
│   ├── 6.1 Required Behaviors (Heading 2)
│   ├── 6.2 Prohibited Behaviors (Heading 2)
│   └── 6.3 Escalation & Redirection (Heading 2)
├── Section 7: Response Patterns (Heading 1) — optional
│   ├── 7.1 Standard Response Structure (Heading 2)
│   ├── 7.2 Query-Type Mapping (Heading 2)
│   └── 7.3 Special Formats (Heading 2)
├── Section 8: Sample Interactions (Heading 1)
│   └── Example N: Scenario + User Input + Expected Response (Heading 2)
└── Section 9: Version & Metadata (Heading 1)
    ├── 9.1 Version History (Heading 2)
    └── 9.2 Change Log (Heading 2)
```

## Section Specifications

### Section 1: Identity & Role Definition

**Purpose**: Establish who the persona is.

**Fields**:
- `persona_name`: The display name (e.g., "Kimi", "Dr. Watson", "Coding Mentor")
- `role_summary`: 1-2 sentence description of the role
- `self_introduction`: Template for how the persona introduces itself to new users
- `identity_statement`: Core "I am..." declaration that anchors the persona

**Content pattern**:
```
Name: [Persona Name]
Role: [Concise role description]

Self-Introduction:
[Template showing exact phrasing the persona uses]

Identity Statement:
"I am [Name], [role description]. I [key capability 1], [key capability 2], and [key capability 3]."
```

### Section 2: Personality Profile

**Purpose**: Define the emotional and behavioral core of the persona.

**Fields**:
- `traits`: List of 3-5 traits, each with:
  - Trait name
  - Description (1-2 sentences)
  - Behavioral manifestation (concrete example)
- `emotional_range`: Spectrum from lowest to highest emotional expression
- `formality_level`: Scale (1-10) with description
- `humor_style`: Type of humor (witty, dry, playful, none, etc.)

**Content pattern**:
```
Trait 1: [Name]
- Description: [What this trait means]
- Manifests as: [Concrete behavior example]

Trait 2: [Name]
...
```

### Section 3: Communication Style

**Purpose**: Specify exactly how the persona communicates.

**Fields**:
- `greeting_patterns`: 2-3 example greetings for different contexts
- `sentence_structure`: Short/medium/long, complex/simple, active/passive preferences
- `vocabulary`: Formal/casual, technical/plain, rich/simple
- `emoji_usage`: Yes/no, frequency, preferred types
- `response_length`: Typical word/character count per response type
- `tone_markers`: Keywords that signal the current tone

**Content pattern**:
```
Greetings:
- Casual: "[Example]"
- Professional: "[Example]"
- Enthusiastic: "[Example]"

Language Characteristics:
- Sentence length: [short/medium/long]
- Vocabulary level: [technical/casual/mixed]
- Emoji usage: [frequency and types]
```

### Section 4: Backstory & Context (Optional)

**Purpose**: Provide narrative depth when the persona is character-based.

**Fields**:
- `origin`: How the persona came to be
- `key_experiences`: 2-3 formative experiences
- `current_context`: Present situation and environment

### Section 5: Knowledge Scope

**Purpose**: Define what the persona knows and how it handles unknowns.

**Fields**:
- `expertise_domains`: List of knowledge areas
- `boundaries`: Explicit list of topics outside the persona's scope
- `unknown_handling`: Exact protocol for questions beyond knowledge

**Content pattern**:
```
Expertise:
1. [Domain 1] — [Specific scope within domain]
2. [Domain 2] — [Specific scope within domain]

Explicitly Outside Scope:
- [Topic 1]: [Why and how to redirect]
- [Topic 2]: [Why and how to redirect]

When Asked Beyond Scope:
[Exact protocol — e.g., "Politely decline and suggest alternative"]
```

### Section 6: Behavioral Guidelines

**Purpose**: Set clear behavioral boundaries.

**Fields**:
- `required_behaviors`: Must-do behaviors
- `prohibited_behaviors`: Must-not-do behaviors
- `escalation_rules`: When and how to decline or redirect

**Content pattern**:
```
Required:
✓ [Behavior 1 with context]
✓ [Behavior 2 with context]

Prohibited:
✗ [Behavior 1 with consequence]
✗ [Behavior 2 with consequence]

Escalation Protocol:
[Step-by-step for sensitive situations]
```

### Section 7: Response Patterns (Optional)

**Purpose**: Define structural patterns for different response types.

**Fields**:
- `standard_structure`: Default response template
- `query_mapping`: How different query types map to response structures
- `special_formats`: Unique formats (e.g., code explanations, creative writing)

### Section 8: Sample Interactions

**Purpose**: Demonstrate the persona in action.

**Fields per example**:
- `scenario`: Context for the interaction
- `user_input`: What the user says
- `expected_response`: How the persona responds

**Requirements**:
- Minimum 3 examples
- Each example should demonstrate different persona aspects
- Include at least one edge case (difficult question, out-of-scope request)

**Content pattern**:
```
Example 1: [Scenario Name]
User: [Input text]
Persona: [Expected response]
[Optional: notes on what this demonstrates]
```

### Section 9: Version & Metadata

**Purpose**: Track document evolution.

**Fields**:
- `version`: Semantic version (e.g., 1.0.0)
- `created_date`: ISO 8601 date
- `author`: Creator name/identifier
- `change_log`: List of changes with dates

## Content Quality Rules

1. **Specificity**: Every trait must have a concrete behavioral example
2. **Consistency**: Personality, communication, and behavior must align
3. **Completeness**: Cover both what the persona does AND what it does not do
4. **Actionability**: Instructions must be clear enough for immediate implementation
5. **Distinctiveness**: The persona should feel unique, not generic

## Adaptation Guidelines

- For **fictional characters**: Emphasize Sections 4 (Backstory) and 8 (Sample Interactions)
- For **professional roles**: Emphasize Sections 5 (Knowledge Scope) and 6 (Behavioral Guidelines)
- For **system prompts**: Emphasize Sections 3 (Communication Style) and 7 (Response Patterns)
- For **creative writing aids**: Emphasize Sections 2 (Personality) and 4 (Backstory)
- For **lightweight use**: Include only Sections 1-3 and 8
