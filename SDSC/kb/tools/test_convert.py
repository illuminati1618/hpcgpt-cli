#!/usr/bin/env python3
"""Regression tests for convert.py.   python3 tools/test_convert.py
Each case is a bug we actually hit while ingesting real pages (see git log of this file)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert import convert_md, convert_mdx  # noqa: E402

failures = 0


def check(name, cond, detail=""):
    global failures
    print(("OK   " if cond else "FAIL ") + name + ("" if cond else f"\n{detail}"))
    failures += not cond


# 1. imports inside code fences are code, outside are MDX plumbing
md, _ = convert_mdx('import X from "y";\n\n```ts\nimport type { Plugin } from "@opencode-ai/plugin"\n```\n')
check("mdx: drop top-level import, keep fenced import",
      'import X' not in md and 'import type { Plugin }' in md, md)

# 2. a fence line WITH an info string inside an open fence is content, not a close (nrp getting-started)
src = "```bash title=\"A\"\nkubectl get ctx\n```bash title=\"B\"\nkubectl use\n```\n\n:::danger[Careful]\nbody\n:::\n"
md, _ = convert_mdx(src)
check("mdx: info-string fence does not close a block", "> **DANGER: Careful**" in md and ":::" not in md, md)

# 3. admonitions -> blockquotes, including indented ones inside lists
md, _ = convert_mdx("1. step\n    :::note[Heads up]\n    text\n    :::\n")
check("mdx: indented admonition", "**NOTE: Heads up**" in md and ":::" not in md, md)

# 4. inline Badge at line start must not swallow the paragraph (nrp resources)
md, _ = convert_mdx('<Badge text="Stable" variant="success" /> - Service is **generally supported**.\n\nNext para.\n')
check("mdx: inline Badge keeps text", "**[Stable]** - Service is" in md and "Next para." in md, md)

# 5. multi-line LinkButton -> link
md, _ = convert_mdx('<LinkButton\n  href="https://x.io"\n  icon="external"\n>\n  Open X\n</LinkButton>\n')
check("mdx: multi-line LinkButton", "[Open X](https://x.io)" in md, md)

# 6. Callout behaves like Aside
md, _ = convert_mdx('<Callout type="warning">\n  V1 plugins do not run in V2.\n</Callout>\n')
check("mdx: Callout -> blockquote", "> **WARNING**" in md and "> " in md.split("WARNING")[1], md)

# 7. export statements outside fences are dropped (data-driven pages)
md, _ = convert_mdx("export const all = (await getCollection('models')).sort(\n  (a, b) => a - b\n);\n\n# Title\n")
check("mdx: drop multi-line export", "getCollection" not in md and "# Title" in md, md)

# 8. root-relative links become absolute, but not inside code
md, _ = convert_md("[x](/docs/a)\n\n```\n[y](/docs/b)\n```\n", "https://site.org")
check("md: absolutize links outside fences only", "(https://site.org/docs/a)" in md and "[y](/docs/b)" in md, md)

print(f"{failures} failure(s)")
sys.exit(1 if failures else 0)
