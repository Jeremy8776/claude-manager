---
name: ComfyUI Workflow Manager
description: Managing ComfyUI workflows for upscaling, image generation, prompt integration, and refinement
triggers: [comfyui, workflow, upscale, KSampler, refiner, image processing, node, prompt]
---

# ComfyUI Workflow Manager

## Upscaling Workflow

Build an upscale workflow:
1. **Load Image** node for input
2. **Upscale Model** node with 4x-UltraSharp ESRGAN model
3. **Upscale Image By** node connected to upscale model
4. **KSampler** for refiner pass at reduced denoise (0.3-0.4)
5. **Save Image** node for output

## 4K Target

For 4K output, use 4x upscale factor from 1080p input. Check VAE tile mode (`--tile`) to avoid memory issues at high resolutions. Target resolution: 3840x2160 or 4096x2160.

## Refiner Pass

After upscaling, run a KSampler with denoise 0.3-0.4 to add detail without changing composition. Set CFG to 5-6 for the refiner pass. Use the same seed as the original generation if preserving composition.

## Prompt Workflow Integration

When building a prompt workflow, combine positive and negative prompt nodes with the KSampler for text-to-image generation. Use the CLIP Text Encode node to convert your positive and negative prompts into the conditioning needed by the KSampler. Load a checkpoint model (like SDXL) and connect it to the CLIP and VAE nodes.

## Fantasy Landscape Prompt Workflow

To generate a moody fantasy landscape with rolling fog and warm sunset, build this workflow:
1. **Checkpoint Loader**: SDXL or Juggernaut XL model
2. **CLIP Text Encode (Positive Prompt)**: "fantasy landscape, rolling fog, warm sunset, dramatic lighting, epic vista, detailed, cinematic atmosphere, moody"
3. **CLIP Text Encode (Negative Prompt)**: "low quality, blurry, distorted, deformed, bad anatomy, watermark, text"
4. **Empty Latent Image**: 1024x1024 or 768x768
5. **KSampler**: DPM++ 2M Karras, CFG 7, steps 25, denoise 1.0
6. **VAE Decode** and **Save Image**

## Template Workflows

Save workflows as .json files in `ComfyUI/user/default/workflows/`. Load from the Workflows menu. Share prompt templates as workflow files that include the full node graph — image loading, upscaling, refiner pass, and save node. Use template workflows to save your favourite prompt configurations for reuse.
