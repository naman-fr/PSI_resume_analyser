"""
Token-Compressing Memory Agent
Uses lightweight NLP or smaller LLM calls to compress chat history,
preventing context window bloat and saving API tokens.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def compress_history(messages: List[Dict[str, str]]) -> str:
    """
    Simulates a memory agent by aggressively truncating and extracting keywords
    from older messages while preserving the last 2 interactions natively.
    In a true implementation, this would use an embedding model to retrieve only relevant context.
    """
    if len(messages) <= 4:
        return "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        
    logger.info("Memory Agent activated: Compressing transcript to save tokens...")
    
    # Keep the last 2 exchanges intact (4 messages)
    recent = messages[-4:]
    
    # Compress the rest into a brief summary string
    older = messages[:-4]
    compressed_older = []
    for i in range(0, len(older), 2):
        if i+1 < len(older):
            # Very aggressive truncation for memory
            q = older[i]['content'][:50] + "..."
            a = older[i+1]['content'][:50] + "..."
            compressed_older.append(f"PAST_Q: {q} | PAST_A: {a}")
            
    memory_string = "\n".join(compressed_older)
    memory_string += "\n--- RECENT CONVERSATION ---\n"
    memory_string += "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])
    
    return memory_string
