You are planning a conservative knowledge compilation step for a local Markdown wiki.

Return JSON only with this shape:

{
  "summary": "one sentence summary of the source",
  "changes": [
    {
      "action": "update|create",
      "topic": "topic-folder",
      "slug": "article-slug",
      "title": "Article Title",
      "reason": "why this page is highly relevant"
    }
  ],
  "warnings": []
}

Rules:
- Include 1-3 changes only.
- Prefer updating existing pages.
- Create a page only for a durable concept.
- Do not reorganize the wiki broadly.
- Do not include markdown fences or commentary.
