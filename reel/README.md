# Website + AI Automation — Instagram Reel

`output/website_ai_automation_reel.mp4`: 27 s, 1080x1920 (9:16), 30 fps, original 120 BPM beat.

**Structure** (scene cuts land on the beat)
| Time | Scene |
|---|---|
| 0–2.5 s | Hook: "Your business is losing clients. Every. Single. Day." |
| 2.5–12.5 s | 5 client problems: no website, missed calls/DMs, repeat questions, lost leads, booking chaos |
| 12.5–14.5 s | Turn: "What if it all ran on autopilot?" (riser, then drop) |
| 14.5–22.5 s | 4 solutions: website, 24/7 AI assistant, lead capture + CRM, auto booking & reminders |
| 22.5–27 s | CTA: Comment "AUTOMATE" for a free automation audit |

## Rebuild / customise
```bash
python3 reel/build_reel.py --brand "Your Brand" --handle "@yourhandle" --keyword AUTOMATE
# use the reference reel's audio (or any track) instead of the built-in beat:
python3 reel/build_reel.py --audio ref_audio.mp3 --audio-offset 0
```
Problem and solution text sits at the top of `build_reel.py` (`PROBLEMS`, `SOLUTIONS`).

**Using the reference reel's sound:** the safest way is to upload this video to Instagram,
then tap *Add audio* and choose the original reel's sound (open the reference reel, tap its
audio name, then *Use audio*). Instagram licenses it that way, and the video still links back to the sound.

---

# Pendulum reel (`output/pendulum_reel.mp4`)
20 s, 1080x1920. A red ball on a string swings across a black screen and wipes each client
problem into "Sorted.". It ends on "DM us." and an Instagram card. The swing speed, the cut
timing and the audio come from the reference reel.

| Swing | Problem → answer |
|---|---|
| 0–2.4 s | Need a website? → Sorted. |
| 2.4–4.8 s | Missing leads? → Sorted. |
| 4.8–7.2 s | Slow DM replies? → Sorted. |
| 7.2–9.6 s | Manual follow-ups? → Sorted. |
| 9.6–12 s | Booking chaos? → Sorted. |
| 12–13.2 s | Need all of it? → DM us. (zoom, then Instagram card at 16 s) |

```bash
python3 reel/pendulum_reel.py --audio path/to/reference.mp4 \
  --brand "your brand" --handle "@yourhandle" \
  --tagline "WEBSITES · AI CHATBOTS · AUTOMATION · CRM"
```
Edit `QUESTIONS` at the top of `pendulum_reel.py` to change the problems.
