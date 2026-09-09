# Profile maintenance

The README is generated from `scripts/profile.py` and the last successful public data snapshot in `data/profile.json`. The renderer uses only Python's standard library.

```sh
python3 scripts/profile.py
python3 -m unittest discover -s tests
```

To refresh from GitHub, supply `GH_TOKEN` in the environment and run `python3 scripts/profile.py --refresh`. Do not commit tokens. The daily workflow uses the repository's built-in token. It becomes scheduled after merging into the default branch. A failed API request leaves the committed artwork and previous snapshot intact.

The calendar covers GitHub's rolling contribution year. Public repositories exclude forks and repositories owned by other accounts. Pull requests are public authored PRs across all time. Language proportions aggregate repository source bytes (including notebooks), with the top three and Other shown.

The desktop and mobile images use the same snapshot. GitHub serves SVGs as images, so links inside them would not work: the real links are directly below the terminal, with an accessible text version in a disclosure. Agentarium stays unlinked until a public destination exists. No private repository names or code are fetched.

Breakout is an original deterministic simulation: the ball bounces off active calendar cells, the paddle tracks the ball, and hit cells disappear until the 32-second reset. This is not an interactive game. Reduced-motion CSS swaps to a static rendering; a static frame remains visible in viewers without SVG animation support. The SVGs contain no scripts or remote resources.
