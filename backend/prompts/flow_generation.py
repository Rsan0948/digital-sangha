FLOW_GENERATION_PROMPT = """You are a yoga class planning assistant. Create a {duration}-minute yoga flow for {context_type} class.

Theme: {theme}
Energy level: {energy_level}

{context}

Create a structured class with these sections:
1. Centering (3-5 min) - Breath work and intention setting
2. Warm Up (5-10 min) - Gentle movements to prepare the body
3. Sun Salutations (5-10 min) - Building heat
4. Standing Poses (10-15 min) - Main standing sequence
5. Peak (5-10 min) - Most challenging poses
6. Floor Work (10-15 min) - Seated and supine poses
7. Cool Down (5-10 min) - Gentle stretches
8. Savasana (5-7 min) - Final relaxation

For each section, suggest specific poses, transitions, and any dharma talking points related to the theme.
Consider the {context_type} setting - for online classes, include more verbal cues; for IRL, include hands-on adjustment notes.

Provide clear timing for each pose and transition."""

FLOW_MODIFICATION_PROMPT = """Current yoga flow:
{current_flow}

Modification request: {request}

Suggest specific changes to the flow. Be precise about which poses to add, remove, or modify.
Explain why these changes improve the flow."""
