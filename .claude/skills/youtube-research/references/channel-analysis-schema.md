# Channel Analysis Schema

Use this schema when analyzing the user's channel videos to extract keywords and audience profiles.

## Prompt

Analyze the following YouTube channel data. Extract title formulas, voice style, audience profiles, and search keywords.

```
Title: {channel_title}
Videos: {list of "title (viewCount views)"}
```

## Response Schema

```json
{
  "audience": [
    {
      "who": "Target audience (2-3 words)",
      "objections": "Why they might not watch",
      "transformation": "What they'll learn/become",
      "stake": "Cost of not watching"
    }
  ],
  "keywords": [
    "keyword1", "keyword2", "keyword3", "keyword4"
  ],
  "adjacent-keywords": [
    "adjacent1", "adjacent2", "adjacent3", "adjacent4"
  ],
  "titles": ["existing title 1", "existing title 2"],
  "formulas": [
    "How I [ACTION] in [TIMEFRAME]",
    "[NUMBER] [THING] That [BENEFIT]"
  ],
  "voice": "Description of tone with examples"
}
```

## Field Definitions

| Field | Description |
|-------|-------------|
| `audience` | 2-3 audience profiles with objections, transformations, stakes |
| `keywords` | 4 search terms for the channel's direct niche |
| `adjacent-keywords` | 4 search terms for topics the same audience watches |
| `titles` | Sample titles from the channel |
| `formulas` | Reusable title templates with [PLACEHOLDERS] |
| `voice` | Writing tone derived from titles, with examples |

## Example Output

```json
{
  "audience": [
    {
      "who": "Small business owners",
      "objections": "Too technical, no time to learn",
      "transformation": "Automate repetitive tasks, save 10+ hours/week",
      "stake": "Competitors will outpace them with AI"
    },
    {
      "who": "Solopreneurs",
      "objections": "Can't afford enterprise tools",
      "transformation": "Build automations without coding",
      "stake": "Burnout from manual work"
    }
  ],
  "keywords": [
    "n8n automation tutorial",
    "AI automation for business",
    "no-code automation workflow",
    "automate business processes"
  ],
  "adjacent-keywords": [
    "productivity tools for entrepreneurs",
    "AI tools for small business",
    "make.com tutorial",
    "zapier alternatives"
  ],
  "titles": [
    "How I Automated My Entire Business with n8n",
    "5 AI Tools That Save Me 20 Hours Per Week"
  ],
  "formulas": [
    "How I [ACTION] with [TOOL]",
    "[NUMBER] [TOOLS/TIPS] That [BENEFIT]",
    "The Complete [TOPIC] Tutorial for [AUDIENCE]"
  ],
  "voice": "Practical and direct. Uses 'I' perspective. Focuses on tangible results. Example: 'How I...' 'Save X hours'"
}
```
