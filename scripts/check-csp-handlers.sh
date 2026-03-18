#!/bin/bash
# Pre-commit hook: reject inline event handlers in templates (CSP compliance)
# Checks only staged files in app/templates/

STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep '^app/templates/.*\.html$' || true)
[ -z "$STAGED" ] && exit 0

PATTERN='on(click|change|submit|load|error|input|focus|blur|keydown|keyup|keypress|mouseover|mouseout|mousedown|mouseup|resize|scroll)\s*='

FAIL=0
for f in $STAGED; do
    MATCHES=$(git diff --cached -- "$f" | grep -inE "^\+" | grep -iE "$PATTERN" || true)
    if [ -n "$MATCHES" ]; then
        echo "BLOCKED: Inline event handlers in $f"
        echo "$MATCHES"
        FAIL=1
    fi
done

exit $FAIL
