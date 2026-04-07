# GitHub Summarization Skill

When the user asks about GitHub activity, commits, or repository progress:

1. Use the provided GITHUB COMMITS context block.
2. Group commits by date or feature area.
3. Highlight: new features, bug fixes, refactors, and notable authors.
4. Format output as Markdown with sections per repository.
5. Provide a one-sentence TL;DR at the top.

## Example output format
**TL;DR**: This week focused on auth refactor and CI fixes.

### repo-name
- 2024-01-15: Added OAuth2 flow (alice)
- 2024-01-14: Fixed CI pipeline timeout (bob)
