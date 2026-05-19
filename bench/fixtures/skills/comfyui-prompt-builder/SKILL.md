---
name: ComfyUI Prompt Builder
description: Building effective prompts for ComfyUI image generation workflows
triggers: [comfyui, prompt, stable diffusion, image generation, positive, negative, CFG]
---

# ComfyUI Prompt Builder

## Positive Prompt Structure

Structure positive prompts with subject, style, environment, and lighting:

```
fantasy landscape, rolling fog, warm sunset, dramatic clouds, epic vista, detailed, cinematic lighting
```

## Negative Prompts

Include negative prompts to avoid artifacts:

```
low quality, blurry, distorted, deformed, extra limbs, bad anatomy, watermark, text, signature
```

## Settings Guidance

- CFG Scale: 7.0 for balanced creativity
- Sampler: DPM++ 2M Karras for quality
- Steps: 20-30 for standard output
- Resolution: 768x768 or 1024x1024 for SDXL
- Seed: -1 for random, fixed for reproducibility

## Weighted Tokens

Use parentheses and number weights: `(fog:1.2)` or `(sunset:1.3)` to emphasize elements. Use `(unwanted:0.5)` to reduce emphasis.
