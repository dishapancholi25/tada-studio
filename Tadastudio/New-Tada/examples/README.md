# Agentic Studio Agent Examples

This directory contains example agent configurations that can be imported into Agentic Studio.

## Directory Structure

- **finance/** - Financial analysis and reporting agents

## Import Instructions

To import any agent:

1. Navigate to the Workflow Library page in Agentic Studio
2. Click the "Import Agent" button
3. Open the desired JSON file from this directory
4. Copy and paste the entire JSON content
5. Review and optionally modify metadata (categories, tags, icon color)
6. Click "Import" to add the agent to your library

## Available Agent Collections

### Finance

The finance directory contains 11 agents organized into two teams:

**Market Analysis Team** (5 agents):

- Economic Indicators Analyst
- Sector Performance Analyst
- Global Macro Analyst
- Market Sentiment Analyst
- Market Review Synthesizer (orchestrator)

**Fund Activity Reporting Team** (6 agents):

- Fund Manager Rationale Analyst
- Portfolio Sales Analyst
- Portfolio Acquisitions Analyst
- Portfolio Allocation Analyst
- Portfolio Outlook Analyst
- Fund Activity Synthesizer (orchestrator)

See `finance/README.md` for detailed documentation.

## Agent Naming Conventions

Agents have been renamed from their original branding names to functional, descriptive names:

| Original Name      | New Name                       | Rationale                      |
|--------------------|--------------------------------|--------------------------------|
| EconCore           | Economic Indicators Analyst    | Describes core function        |
| SectorWatch        | Sector Performance Analyst     | Clearer role description       |
| MacroIntel         | Global Macro Analyst           | More professional naming       |
| MarketMood         | Market Sentiment Analyst       | Describes analysis focus       |
| AlphaLead (Market) | Market Review Synthesizer      | Clarifies synthesis role       |
| StratMind          | Fund Manager Rationale Analyst | Describes strategic analysis   |
| SellSignal         | Portfolio Sales Analyst        | Clearer functional name        |
| BuySignal          | Portfolio Acquisitions Analyst | More professional terminology  |
| AllocShift         | Portfolio Allocation Analyst   | Describes allocation focus     |
| Foresight          | Portfolio Outlook Analyst      | Describes forward-looking role |
| AlphaLead (Fund)   | Fund Activity Synthesizer      | Clarifies synthesis role       |

## Contributing

When adding new agent examples:

1. Create category subdirectories as needed
2. Use clear, functional names (not branding names)
3. Include a README.md in each category directory
4. Follow the Agentic Studio import schema (see `AGENT_IMPORT.md` in the root)
5. Test import and functionality before committing

## Schema Reference

All agent configurations follow the Agentic Studio agent import schema. See the main project `AGENT_IMPORT.md` for complete
schema documentation.
