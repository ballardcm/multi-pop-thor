# Repository instructions

Contributions should arrive through pull requests so their checks and preview downloads can be reviewed before release. Never commit or push directly to `main`; GitHub protects it for maintainers too. Do not merge until the user authorizes merging. Deploy only from a PR merged to `main`.

Chris's personal email must stay out of public commit metadata. Use `3799765+ballardcm@users.noreply.github.com` for local commits and pass `--author-email 3799765+ballardcm@users.noreply.github.com` when merging with `gh pr merge`, because GitHub's merge API can otherwise use the account email. Verify the resulting merge commit's author email before publishing a release or changing repository visibility.

Keep original material under the documented CC BY-NC-SA 4.0 scope and preserve third-party license exceptions. Disclose AI assistance in user-facing documentation when appropriate.

Run the theme checker, media installer tests, and release packaging tests for relevant changes. PR packaging verifies the pinned frontend inputs; changes to frontend patches or compiler inputs require a newly validated binary rather than reusing the old one. See `docs/releases.md` for this process.

Keep credentials, ROMs, downloaded game media, device settings, firmware libraries, and compiler caches out of Git and release source inventories.
