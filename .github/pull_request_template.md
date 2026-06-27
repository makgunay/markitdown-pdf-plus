## Summary

<!-- What does this PR change, and why? Keep it focused. -->

## Related issues

<!-- e.g. "Closes #123". Link the issue this addresses, if any. -->

## Testing done

<!-- List the commands you ran and their results. -->

- [ ] `ruff check src tests` and `ruff format --check src tests`
- [ ] `python -m mypy` (strict)
- [ ] `python -m pytest --ignore=tests/test_integration.py --ignore=tests/eval`
- [ ] Ran the real-document eval (`python tests/eval/run_eval.py`) — required when the
      change touches table detection, headings, or text extraction (the unit fixtures
      do not cover those failure modes)

## Checklist

- [ ] I followed the non-obvious invariants in `CLAUDE.md` (pdfminer text source,
      borderless-table validator, paragraph-only table de-dup)
- [ ] Added or updated tests for the change
- [ ] No new **core** dependencies (the VLM/ML path stays an optional extra)
- [ ] Graceful degradation preserved (useful output with no `llm_client`)
