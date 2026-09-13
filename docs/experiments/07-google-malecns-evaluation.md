# Experiment 07: Thoughts on the Google MaleCNS Dataset

## Observation
I recently heard about this new dataset called Google MaleCNS v1.0. From what I understand, it maps the brain of a male fly, but the really interesting part is that it apparently includes the Ventral Nerve Cord (which I think is basically the fly's version of a spinal cord). Our current FlyWire dataset only has the central brain of a female fly.

## Theoretical Capability
Having the spinal cord mapped out theoretically means you could trace the signals all the way down to the actual legs and wings. That sounds like it would be awesome for connecting the brain to physical limbs or game controls in a much more detailed and accurate way, instead of just reading the high-level escape signals like I'm doing right now.

## Strategic Decision
I don't think I'm going to try migrating to this MaleCNS dataset anytime soon. 

First off, trying to simulate an entire spinal cord and all those extra leg mechanics on top of the brain seems like it would just explode my GPU's VRAM and completely kill the framerate. Secondly, I've already invested so much time getting the FlyWire dataset to work, and honestly, it's already doing exactly what I need for the FNAF survival mechanics. 

It's a cool discovery, but I'll stick to what I have for now. Maybe I'll look into it in the future if I ever need to simulate actual joint movements.

| Versão | Descrição | Autor(es) | Data | Revisor(es) | Data de Revisão |
|---|---|---|---|---|---|
| 1.0 | Initial thoughts on the MaleCNS dataset | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-13 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-13 |
