from ._model import Block


def _data_rows(md: str) -> list[str]:
    """Return only the body rows (skip header + separator)."""
    rows = [r for r in md.splitlines() if r.strip().startswith("|")]
    return rows[2:] if len(rows) >= 2 else rows


class CrossPageTableMerger:
    def merge(self, blocks: list[Block]) -> list[Block]:
        ordered = sorted(blocks, key=lambda b: (b.page, b.top, b.x0))
        out: list[Block] = []
        for b in ordered:
            prev = out[-1] if out else None
            if (
                b.kind == "table"
                and prev is not None
                and prev.kind == "table"
                and b.page == prev.page + 1
                and b.cols == prev.cols
                and b.cols > 0
            ):
                extra = _data_rows(b.markdown)
                prev.markdown = prev.markdown.rstrip() + ("\n" + "\n".join(extra) if extra else "")
            else:
                out.append(b)
        return out
