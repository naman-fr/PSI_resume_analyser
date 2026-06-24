# 🚀 HuggingFace Space / Gradio Fallback Client: Technical Setup

While the primary product is a React/Vite SPA hosted on Vercel, we maintain `app.py` as a standalone `gradio` interface designed specifically for serverless deployment on **HuggingFace Spaces**.

## 1. Architecture

### 1.1 Gradio Blocks Engine (`app.py`)
We leverage `gr.Blocks(theme=gr.themes.Glass())` to construct a stateful UI without writing CSS.
- **Event Listeners**: Standard Python functions (e.g., `gradio_analyze`) are bound to `.click()` events.
- **State Preservation**: `gr.State()` objects are passed between function calls to retain the `debate_log` and `premium_report` payloads across sequential user interactions.

### 1.2 Custom HTML/JS Injection (Swipe Interface)
Gradio's native components lack fluid gesture interfaces. To replicate a "Tinder-style" candidate swiping mechanic, we inject raw HTML/CSS/JS into a `gr.HTML` block.
```python
swipe_js = """
<script>
  function handleSwipe(direction, candidateId) {
     // Emits custom JS event caught by Gradio
     window.parent.postMessage({action: 'swipe', dir: direction, id: candidateId}, '*');
  }
</script>
"""
```

## 2. Streaming State Yields
Because the LangGraph swarm can take 15-30 seconds to run through all nodes (Parse $\rightarrow$ Normalize $\rightarrow$ Tech Lead Tool Calls $\rightarrow$ Judge), we utilize Python generator functions (`yield`) within the Gradio event handler.
As the graph progresses, intermediate states update a `gr.Textbox` or `gr.Markdown` component, creating a typewriter-effect loading screen that updates in real-time, preventing request timeouts on the HuggingFace free tier.
