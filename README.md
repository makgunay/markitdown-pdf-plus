# markitdown-pdf-plus

A [MarkItDown](https://github.com/microsoft/markitdown) plugin that overrides the built-in PDF converter with always-on font-heuristic heading detection and figure extraction, plus opt-in model-agnostic VLM table transcription, cross-page table merging, and figure captioning.

## Install

```bash
pip install markitdown-pdf-plus
```

## Usage

```python
from markitdown import MarkItDown
import openai

client = openai.OpenAI()

md = MarkItDown(enable_plugins=True, llm_client=client, llm_model="gpt-4o")
result = md.convert("document.pdf")
print(result.text_content)
```

Without a VLM client, the plugin still runs with font-heuristic headings and figure extraction (no table transcription or figure captioning):

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("document.pdf")
print(result.text_content)
```
