---
name: PowerPoint Generator
description: PowerPoint slide deck creation and automation for presentations and slide decks
triggers: [PowerPoint, pptx, slide, deck, presentation, office, automation, slideshow]
---

# PowerPoint Generator

## Creating Presentations

Use the `python-pptx` library to create slide decks programmatically:

```python
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation()
slide_layout = prs.slide_layouts[1]  # Title and Content
slide = prs.slides.add_slide(slide_layout)
slide.shapes.title.text = "Q2 Objectives"
```

## Slide Layouts

- **Title slide**: for section dividers
- **Content slide**: bullet points or body text
- **Two content**: side-by-side comparison
- **Blank**: custom layouts

## Deck Structure

A well-structured presentation deck includes a title slide, an agenda slide, content slides for each topic, and a closing slide. For Q2 planning, include milestones, key results, and timeline slides.

## Theme-Factory Integration

Use custom themes from theme-factory with python-pptx: design principles like Dieter Rams' "less but better" can be applied programmatically. Set the theme's accent colors, typography (Styrene for titles, Tiempos for body), and slide master layouts. The preferred aesthetic is restrained — generous whitespace, single accent element per slide, no gradients.

## Q2 Planning Deck with Rams Theme

For a Q2 slide deck using the Dieter Rams theme: create a title slide with project name, an agenda slide listing objectives, milestone slides (1 per quarter-month), and key results slides. Apply the Rams design principles: honest presentation of data, unobtrusive layouts, useful visual hierarchy. Use the theme-factory preset's color palette (Slate, Clay, Ivory) and ensure consistent typography throughout every slide.

## Formatting Tips

- Use consistent font sizes (title 28pt, body 18pt)
- Keep 5-7 bullets per slide max
- Include speaker notes for presentation delivery
- Export to PDF for distribution

## Automation

Use `Add-Member -Type NoteProperty` in PowerShell to generate PPTX via COM object, or use python-pptx for cross-platform creation. Slide decks can be automated end-to-end with dynamic data from spreadsheets or databases.
