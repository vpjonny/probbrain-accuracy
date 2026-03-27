#!/usr/bin/env python3
"""One-time fix: add Telegram + Follow hooks to tweet_3 in all signal posting scripts."""
import glob

OLD_BARE = '"tweet_3": "We track every call publicly \\u2192 https://vpjonny.github.io/probbrain-accuracy/",'

NEW_TWEET3 = (
    '"tweet_3": (\n'
    '            "We track every call publicly.\\n"\n'
    '            "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\\n\\n"\n'
    '            "Join us on Telegram: https://t.me/ProbBrain\\n"\n'
    '            "Follow @ProbBrain for more signals."\n'
    '        ),'
)

files_fixed = []
for pattern in ["tools/post_sig*.py", "tools/post_iran*.py"]:
    for f in sorted(glob.glob(pattern)):
        content = open(f).read()
        if OLD_BARE in content:
            content = content.replace(OLD_BARE, NEW_TWEET3)
            open(f, "w").write(content)
            files_fixed.append(f)

print(f"Fixed {len(files_fixed)} files:")
for f in files_fixed:
    print(f"  {f}")
