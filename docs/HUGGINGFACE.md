# 🚀 HuggingFace / Gradio Fallback Client

While the primary frontend is a highly customized React SPA, the platform retains a **Gradio 4.x** fallback interface (`app.py`), optimized for deployment on HuggingFace Spaces.

## Capabilities
- **Tinder-Style Candidate Swiping**: A custom HTML/JS component injected into Gradio allows recruiters to rapidly swipe Left/Right on parsed candidates, pushing human-in-the-loop training data back into the SQLite telemetry database.
- **Real-Time Streaming**: Yields intermediate states from the LangGraph pipeline directly to the UI, providing the user with real-time feedback as the agents debate the candidate.
- **Zero-Config Deployment**: The entire Gradio interface runs out of a single lightweight file, making it perfect for rapid prototyping, internal corporate tools, or showcasing the AI's capabilities natively on HuggingFace without requiring a full Node.js stack.
