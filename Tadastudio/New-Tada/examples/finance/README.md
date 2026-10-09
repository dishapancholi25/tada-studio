# Finance Agents

This directory contains agent configurations for financial analysis and reporting use cases.

## Agent Categories

### Market Analysis Agents

These agents work together to provide comprehensive market reviews:

- **Economic Indicators Analyst** (`economic_indicators_analyst.json`) - Analyzes GDP, inflation, employment, and other
  macroeconomic indicators
- **Sector Performance Analyst** (`sector_performance_analyst.json`) - Examines industry performance, growth drivers,
  and notable sector events
- **Global Macro Analyst** (`global_macro_analyst.json`) - Analyzes worldwide economic events and their investment
  impacts
- **Market Sentiment Analyst** (`market_sentiment_analyst.json`) - Studies investor behavior, sentiment shifts, and
  market flows
- **Market Review Synthesizer** (`market_review_synthesizer.json`) - Orchestrator that integrates all market analysis
  into a cohesive commentary (max 800 words)

### Fund Activity Reporting Agents

These agents work together to analyze and report on fund portfolio activities:

- **Fund Manager Rationale Analyst** (`fund_manager_rationale_analyst.json`) - Explains the strategic reasoning behind
  manager decisions
- **Portfolio Sales Analyst** (`portfolio_sales_analyst.json`) - Analyzes major sales and exits from portfolios
- **Portfolio Acquisitions Analyst** (`portfolio_acquisitions_analyst.json`) - Analyzes major buys and new positions
- **Portfolio Allocation Analyst** (`portfolio_allocation_analyst.json`) - Examines allocation changes by country,
  sector, or asset class
- **Portfolio Outlook Analyst** (`portfolio_outlook_analyst.json`) - Captures forward-looking guidance and positioning
  signals
- **Fund Activity Synthesizer** (`fund_activity_synthesizer.json`) - Orchestrator that compiles all fund activity into a
  clear report (max 600 words)

## Key Features

All agents in this collection:

- **Prioritize uploaded documents**: Use document search first, web search as fallback
- **Maintain clear sourcing**: Cite all claims with full URLs (web) or file paths (documents)
- **Distinguish scope**: Clearly indicate fund-specific vs. product/asset-class-specific vs. general data
- **Structured citations**: Include sources in structured format for verification

## Usage

### Importing Individual Agents

1. Navigate to the Workflow Library in Agentic Studio
2. Click "Import Agent"
3. Copy and paste the contents of any JSON file
4. Review metadata and import

### Team Workflows

**Market Review Team**: Deploy all Market Analysis agents together with the Market Review Synthesizer as the
orchestrator.

**Fund Activity Team**: Deploy all Fund Activity Reporting agents together with the Fund Activity Synthesizer as the
orchestrator.

## Configuration Notes

- All agents use `azure_openai` provider with `gpt-4.1-nano` model
- Research agents use temperature 0.3 for accuracy
- Orchestrator agents use temperature 0.5 for better synthesis
- All research agents use `react` agent type with document and web search tools
- Orchestrator agents use `plan_and_execute` type with supervisor mode
- Document search is enabled with k=5 retrieval and structured citations

## Customization

You can customize these agents by:

- Changing the LLM provider/model in `llm_config`
- Adjusting temperature for more/less creative outputs
- Modifying max_iterations for longer/shorter reasoning chains
- Adding additional tools to the `tools` array
- Updating system prompts to match your specific requirements
