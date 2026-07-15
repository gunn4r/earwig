# Changelog fragments

Every pull request that changes behavior adds a news fragment here. At release time, `towncrier build` compiles these fragments into `../CHANGELOG.md` and deletes them.

## Format

One file per change, named `<issue>.<type>.md` (or `+<slug>.<type>.md` when there is no issue number). The file body is the changelog line — markdown, one or two sentences.

## Types (and semver impact while pre-1.0)

| type | filename example | semver |
|---|---|---|
| `feature` | `42.feature.md` | minor |
| `bugfix` | `43.bugfix.md` | patch |
| `removal` | `+drop-foo.removal.md` | minor (major once 1.0) |
| `docs` | `+readme.docs.md` | — |
| `chore` | `+ci.chore.md` | — |

Preview the next release without writing anything:

    towncrier build --draft --version X.Y.Z
