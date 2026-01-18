# Vector Chat (RAG) vs RLM Chat: Comparison Guide

## Overview

aiMultiFool supports two different approaches to managing long conversation context:

- **Vector Chat (RAG)**: Uses semantic similarity search via embeddings stored in a vector database
- **RLM Chat**: Uses LLM-generated search queries with multi-strategy retrieval (keyword, semantic, temporal) to query full conversation history recursively

Both can be used together or separately, depending on your needs.

---

## Vector Chat (RAG - Retrieval Augmented Generation)

### How It Works

- **Embedding Model**: Uses `nomic-embed-text-v2-moe` to convert text into high-dimensional vectors
- **Storage**: Stores conversation pairs (user + assistant) as embeddings in Qdrant vector database
- **Retrieval**: Uses cosine similarity search to find semantically similar past conversations
- **Returns**: Top-k most relevant memories based on semantic meaning

### Strengths ✅

- **Semantic Understanding**: Finds relevant context even with different wording
  - Example: "fight" matches "battle", "conflict", "combat"
- **Efficient**: Vector search is fast even with thousands of entries
- **Focused Retrieval**: Only brings back relevant memories, not everything
- **Proven Technology**: RAG is widely used and battle-tested
- **Cross-Conversation**: Can find relevant context across different sessions/characters

### Weaknesses ❌

- **Requires Embedding Model**: Needs separate embedding model loaded (uses memory/disk)
- **May Miss Exact Matches**: Similarity-based, not exact - might miss specific references
- **Limited to Stored Pairs**: Only retrieves what was explicitly saved as conversation pairs
- **No Temporal Awareness**: Doesn't prioritize recent vs old memories by default

### Best For 🎯

- Long-term memory across multiple conversations
- Finding similar situations/themes
- Character consistency over time
- When you want semantic similarity, not exact matches
- Cross-character knowledge sharing

---

## RLM Chat (Recursive Language Models)

### How It Works

- **Full History Storage**: Stores complete conversation history externally (never deletes)
- **LLM-Generated Search Queries**: The language model itself generates optimized search queries based on user input, implementing MIT's recursive querying approach
- **Multi-Strategy Search**: Uses prewritten Python functions to execute searches combining:
  - Keyword matching with relevance scoring
  - Semantic similarity (when embedding models are available)
  - Temporal relevance (prioritizing recent messages)
- **Recursive Querying**: Queries the full history recursively to find relevant chunks
- **External Context**: Treats context as an external environment (MIT approach)
- **Programmatic Access**: Can access entire conversation history programmatically

### Strengths ✅

- **Complete History**: Nothing is ever lost - full conversation preserved
- **Intelligent Search**: LLM generates optimized search queries tailored to each user question
- **Multi-Strategy Retrieval**: Combines keyword matching, semantic similarity, and temporal relevance for best results
- **Temporal Awareness**: Can prioritize recent vs old context with recency scoring
- **Exact Matches**: Can find specific mentions, names, events, dates
- **Semantic Support**: When embedding models are available, uses semantic similarity alongside keyword matching
- **No Embedding Model Required**: Works with just the main LLM (embeddings optional for enhanced results)
- **Scalable**: Can handle very long conversations without degradation
- **Chronological Context**: Maintains conversation flow and timeline
- **Safe Execution**: Uses prewritten Python functions for reliable, secure search execution

### Weaknesses ❌

- **More Complex**: Recursive querying adds computational overhead (LLM call for query generation)
- **Storage Intensive**: Stores everything, not just summaries
- **Moderate Speed**: Search through full text is slower than vector search, but optimized with sampling strategies

### Best For 🎯

- Very long single conversations (50+ exchanges)
- When you need exact references (who said what, when)
- Maintaining complete conversation context
- When you don't want to load an embedding model
- When you need temporal/chronological awareness

---

## Comparison Table

| Feature | Vector Chat (RAG) | RLM Chat |
|---------|-------------------|----------|
| **Storage Method** | Embeddings in vector DB | Full text in JSON files |
| **Retrieval Method** | Semantic similarity search | LLM-generated queries + multi-strategy search |
| **Model Required** | Embedding model + LLM | LLM only (embeddings optional for enhancement) |
| **Memory Efficiency** | High (compressed vectors) | Lower (full text) |
| **Search Speed** | Very fast (~50-100ms) | Moderate (~500-1000ms, includes LLM query generation) |
| **Semantic Understanding** | Excellent | Good to Excellent (when embeddings available) |
| **Exact Match Finding** | Good | Excellent |
| **Temporal Awareness** | Limited | Excellent |
| **Cross-Conversation** | Yes | No (per-conversation) |
| **History Preservation** | Selective (only saved pairs) | Complete (everything) |
| **Best Conversation Length** | Any length | Very long (50+ exchanges) |

---

## Which Should You Use?

### Use Vector Chat When:
- ✅ You want semantic similarity (find "similar situations")
- ✅ You have multiple separate conversations/characters
- ✅ You want efficient long-term memory
- ✅ You're okay loading an embedding model
- ✅ You want cross-conversation memory
- ✅ You want proven, stable technology

### Use RLM Chat When:
- ✅ You have very long single conversations
- ✅ You need exact references (who said what, when)
- ✅ You want complete history preservation
- ✅ You want intelligent, context-aware search (LLM generates optimized queries)
- ✅ You don't want to load an embedding model (or want optional semantic enhancement)
- ✅ You need temporal/chronological awareness
- ✅ You want to experiment with cutting-edge MIT research

### Use Both Together:
- ✅ **Vector Chat** for semantic long-term memory
- ✅ **RLM Chat** for exact conversation history
- ✅ They complement each other perfectly
- ✅ Get the best of both worlds

---

## Recommendation

**For Most Users**: Start with **Vector Chat**. It's more efficient and better at finding relevant context semantically.

**Switch to RLM Chat if**:
- Your conversations exceed 50+ exchanges regularly
- You need exact references to past events
- You want complete history preservation
- You're hitting context window limits frequently

**Use Both**: The app supports using both simultaneously - enable both and get the benefits of each approach!

---

## Technical Details

### Vector Chat Implementation
- **Embedding Model**: `nomic-embed-text-v2-moe.Q4_K_M.gguf`
- **Vector Database**: Qdrant (local storage mode)
- **Embedding Dimension**: 768 (nomic-embed-text-v2-moe)
- **Storage Location**: `vectors/{chat_name}/`
- **Encryption**: Optional AES-256-GCM encryption

### RLM Chat Implementation
- **Storage Format**: JSON files with full message history
- **Storage Location**: `rlmcontexts/{chat_name}/`
- **Context File**: `context.json` (stores all messages)
- **Chat Files**: `chats/*.json` (saved chat snapshots)
- **Encryption**: Optional AES-256-GCM encryption
- **Query Method**: LLM-generated search queries with multi-strategy execution
  - LLM generates optimized search queries based on user input
  - Prewritten Python functions execute searches using keyword matching, semantic similarity, and temporal relevance
  - Results are scored, deduplicated, and ranked by relevance

---

## Performance Considerations

### Vector Chat
- **Initial Setup**: Requires embedding model load (~2GB disk, ~500MB RAM)
- **Query Speed**: ~50-100ms per query
- **Storage**: ~1KB per conversation pair
- **Scalability**: Handles 10,000+ entries efficiently

### RLM Chat
- **Initial Setup**: No additional models needed (embeddings optional for enhanced semantic search)
- **Query Speed**: ~500-1000ms per query (includes LLM query generation + search execution, depends on history size and model speed)
- **Storage**: ~10-50KB per conversation exchange
- **Scalability**: Best for single long conversations (100-1000+ exchanges)

---

## Future Enhancements

### Potential Vector Chat Improvements
- Hierarchical summarization
- Temporal weighting (recent memories prioritized)
- Multi-vector search (combining multiple embedding models)

### Potential RLM Chat Improvements
- Recursive sub-calls (model queries itself on smaller chunks for deeper analysis)
- Hierarchical chunking and summarization
- REPL-style code execution (model writes executable Python code for advanced searches)
- Answer aggregation from multiple recursive calls

---

## References

- **Vector Chat**: Based on RAG (Retrieval Augmented Generation) principles
- **RLM Chat**: Based on MIT's "Recursive Language Models" (arXiv:2512.24601)
  - Authors: Alex L. Zhang, Tim Kraska, Omar Khattab (MIT CSAIL)
  - Paper: https://arxiv.org/abs/2512.24601

---

*Last Updated: 2025*
