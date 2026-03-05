# Getting Started: Teaching Your AI to Remember You

This guide is for people who want their AI assistant to actually remember them — across days, weeks, and conversations. No technical background required.

---

## The Basic Idea

By default, every conversation with an AI starts from zero. It doesn't know you, your projects, your preferences, or what you talked about yesterday. HippoGraph fixes this by giving your AI a persistent memory — a knowledge graph that lives on your own computer and grows over time.

Think of it like a notebook that your AI can read and write to. Every session, it checks the notebook. Over time, the notebook becomes a detailed picture of who you are and what you care about.

---

## Step 1: Run HippoGraph

Follow the [Quick Start](README.md#-quick-start) in the README. Once Docker is running and you see `{"status": "ok"}` from `http://localhost:5001/health` — you're ready.

---

## Step 2: Connect to Your AI

In Claude.ai, go to **Settings → Integrations** and add a new MCP connection:

```
Name: My Memory
URL:  http://localhost:5001/sse2
Key:  <your NEURAL_API_KEY from .env>
```

For remote access (mobile, other devices) see [MCP_CONNECTION.md](MCP_CONNECTION.md).

Once connected, Claude will have access to 8 memory tools: save notes, search memories, see connections between ideas, and more.

---

## Step 3: Your First Session — Tell It Who You Are

This is the most important step. The first time you use HippoGraph, your AI's memory is empty. You need to introduce yourself.

Start a conversation and say something like:

> *"I want you to start building a memory of me. Ask me a few questions about who I am, what I'm working on, and what's important to me. Then save what you learn to memory."*

Or just start talking and occasionally say:

> *"Save that to memory."*

Your AI will use the `add_note` tool to write notes about you. These notes become the foundation of its memory.

**What's worth saving early:**
- Your name and how you like to be addressed
- What you're working on (projects, goals)
- Your role / what you do
- Preferences (communication style, what annoys you, what helps)
- Important context (your tech stack, your team, your timezone)

---

## Step 4: Set Up the Wake-Up Instruction

This is what makes memory *automatic* — so your AI checks its notes at the start of every session without you having to ask.

In Claude.ai, go to **Settings → Claude's instructions** (also called "user preferences" or "custom instructions") and paste this:

```
At the start of every conversation, use the search_memory tool 
to search for "self-identity protocol" and load context from 
previous sessions before responding.
```

That's it. Now every conversation begins with your AI reading its notes about you.

**Why "self-identity protocol"?**  
It's just a search term. When you save notes about yourself, include that phrase (or ask your AI to tag important self-description notes with it). This way the wake-up search always finds the right notes first.

---

## Step 5: Let It Grow

Memory gets better the more you use it. A few habits that help:

**At the end of a productive session:**
> *"Summarize what we accomplished today and save it to memory."*

**When something important happens:**
> *"Remember this — it's important for future sessions."*

**When something changes:**
> *"Update your memory: I'm no longer working on X, I've switched to Y."*

Your AI will handle the rest — writing notes, connecting them to related memories, and making sure important things don't get forgotten.

---

## How Memory Works (Simply)

HippoGraph doesn't store memories as a flat list. It builds a *graph* — a web of connected ideas.

When you search for something, the system doesn't just find the closest match. It activates that memory, then lets the activation spread to connected memories — like following a train of thought. This is how you end up finding relevant context you didn't explicitly ask for.

Memories also have **weight**. Something you marked as important, or something tied to a strong emotion, stays prominent longer. Routine details fade over time. This mirrors how human memory works — not everything deserves equal weight forever.

---

## Frequently Asked Questions

**Q: Does my AI remember things automatically, or do I have to tell it to save?**  
A: Both. You can explicitly ask it to save things. But over time, a well-prompted AI will start saving important moments on its own, especially if your custom instruction encourages it.

**Q: What if my AI saves something wrong?**  
A: You can ask it to correct or delete notes at any time. Say: *"That's not quite right — update the note about X to say Y."* Or: *"Delete what you saved about Z."*

**Q: Can I see what's in memory?**  
A: Yes. Open `http://localhost:5002` in your browser for a visual graph of all your memories. You can also ask your AI: *"What do you remember about me?"* and it will search and summarize.

**Q: Is my data private?**  
A: Everything stays on your computer. HippoGraph runs locally in Docker. Nothing is sent to any cloud service — not your memories, not your notes, not your data.

**Q: What if I want to start over?**  
A: Stop Docker, delete the `data/memory.db` file, and restart. Fresh start.

**Q: Works with other AIs besides Claude?**  
A: HippoGraph uses MCP (Model Context Protocol). Any AI that supports MCP can use it. Claude.ai is the most seamless experience, but others work too.

---

> ✅ For a more complete system prompt that covers how to save, search, and maintain memory
> — see [AGENT_PROMPT.md](AGENT_PROMPT.md). It also includes the init script for your first session.

## Template: Wake-Up Instruction

Copy this into your AI's custom instructions:

```
At the start of every conversation, search your memory for 
"self-identity protocol" to load context about me and our 
shared history. If memory is empty, ask me to introduce myself 
so you can start building context.
```

---

## Template: First Session Script

If you want a structured first session, share this with your AI:

```
This is our first session with persistent memory. 
Please:
1. Ask me 5 questions to understand who I am and what I'm working on
2. Save my answers as notes, tagged with "self-identity protocol"
3. Summarize what you've learned and confirm it's saved
4. Tell me what to say in future sessions to trigger memory loading
```

---

*Back to [README](README.md)*