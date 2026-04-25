# Multi-Model Architecture V2 - True Collaboration

## Overview

This architecture redesigns the original multimodel-coo to solve fundamental collaboration problems:

### Problems Solved

| Problem | Old Architecture | New Architecture |
|---------|-----------------|-----------------|
| **Role Hard-coding** | Each model locked to single role (reason/review/execute) | Flexible task types: reason, write, review, execute, continue |
| **File I/O Missing** | Models could not read/write files directly | Full file read/write support with artifact passing |
| **Output Truncation** | Fixed token limits (~3000) | Configurable max_tokens with continuation support |
| **Stage Isolation** | Stages completely independent, no artifact passing | Automatic artifact registration and retrieval between stages |
| **Rigid Phase Structure** | Fixed Phase 1-6 sequence | Conditional branching, parallel execution, automatic retry |

---

## Core Components

### 1. Universal Wrapper (`universal_wrapper.py`)

**Purpose:** Single, flexible wrapper for all model types and tasks.

**Key Features:**
- **No hard-coded prompt prefixes** - models adapt to task type
- **Full file I/O:**
  - `--read-file`: Read input file content into prompt
  - `--write-file`: Write output to specified path
  - `--append-file`: Append to existing file
- **Task Type Flexibility:**
  - `reason`: Analysis and planning
  - `write`: Long-form content generation
  - `review`: Quality assessment
  - `execute`: Task execution
  - `continue`: Resume truncated output
- **Configurable Output Length:**
  - `--max-tokens`: Override default limits (higher for long writing tasks)
- **Continuation Support:**
  - `--continue-from marker`: Resume from specific point in existing file

**Model-Specific Prompt Engineering:**
- **Qwen:** Optimized for concise reasoning and writing with natural break points
- **DeepSeek:** Prompted for complete, detailed responses with structured output
- **GLM:** Adaptive prompts for different task types (write/review/reason)
- **Claude:** Reserved for integration and coordination

### 2. Workflow Orchestrator (`workflow_orchestrator.py`)

**Purpose:** Coordinate multi-stage workflows with dependency tracking and artifact passing.

**Key Features:**
- **Dependency Management:** Stages execute in correct order based on dependencies
- **Conditional Branching:** Stages can have conditions (e.g., "execute only if previous stage succeeded")
- **Artifact Passing:** Output of one stage automatically available to dependent stages
- **Automatic Retry:** Failed stages can retry with alternative models
- **State Persistence:** Full tracking of stage status, artifacts, and execution log
- **Dry-Run Mode:** Test workflows without actual model calls

**Workflow Definition:**
```python
StageDefinition(
    name="write_section4",
    model="deepseek",
    task_type="write",
    prompt_template="Write Section 4...",
    depends_on=["write_section3"],
    required_artifacts=["OUTLINE_PATH"],
    output_artifact="section4_draft",
    max_tokens=8000,
    can_retry=True,
    retry_models=["glm", "qwen"],
)
```

### 3. Session State Management

**File:** `{session_dir}/workflow_state.json`

**Contents:**
```json
{
  "workflow_name": "nature_review_multiscale",
  "stages": {
    "foundation_analysis": {
      "status": "completed",
      "model": "qwen",
      "output_path": "...",
      "bytes_written": 5432
    },
    "draft_phase_a": {
      "status": "completed",
      "model": "deepseek",
      "was_truncated": false,
      "output_path": "..."
    }
  },
  "global_artifacts": {
    "OUTLINE_PATH": {
      "path": "/path/to/outline.md",
      "description": "Original outline file"
    },
    "draft_phase_a": {
      "path": "/path/to/draft_phase_a.md",
      "description": "Draft of Sections 1-3"
    }
  },
  "execution_log": [...]
}
```

---

## Usage Examples

### Example 1: Write a Section with File Access

```bash
python scripts/ai_wrappers/universal_wrapper.py \
    --model deepseek \
    --task write \
    --read-file "<PROJECT_ROOT>/03_Theoretical_Work\Literature_Review\outline.md" \
    --write-file "<PROJECT_ROOT>/01_Planning\workflows\current_task\section4.md" \
    --max-tokens 6000 \
    --prompt "Write Section 4 on brain organoids following the outline. Focus on organoid intelligence, MEA interfaces, and AI analysis methods."
```

### Example 2: Review with Complete Draft Access

```bash
python scripts/ai_wrappers/universal_wrapper.py \
    --model glm \
    --task review \
    --read-file "<PROJECT_ROOT>/03_Theoretical_Work\Literature_Review\draft_complete.md" \
    --write-file "<PROJECT_ROOT>/01_Planning\workflows\current_task\review.md" \
    --prompt "Review this Nature Review draft for narrative coherence, technical accuracy, and adherence to journal standards."
```

### Example 3: Continue Truncated Output

```bash
python scripts/ai_wrappers/universal_wrapper.py \
    --model deepseek \
    --task continue \
    --read-file "<PROJECT_ROOT>/01_Planning\workflows\current_task\section4.md" \
    --write-file "<PROJECT_ROOT>/01_Planning\workflows\current_task\section4.md" \
    --continue-from "### 4.5 Disease Modeling" \
    --max-tokens 6000 \
    --prompt "Continue writing from the marker. Complete all remaining subsections."
```

### Example 4: Execute Complete Workflow

```bash
python scripts/workflow_orchestrator.py \
    --session-id coo-20260416-newarch \
    --outline "<PROJECT_ROOT>/03_Theoretical_Work\Literature_Review\outline.md"
```

---

## Nature Review Workflow

The new architecture includes a predefined workflow for the Nature Review task:

### Stage Sequence

1. **Foundation Analysis** (Qwen - reason)
   - Analyze outline structure
   - Plan reference allocation
   - Identify potential challenges

2. **Draft Phase A** (DeepSeek - write)
   - Abstract + Sections 1-3
   - Box 1
   - Partial citations
   - Target: ~5500 words

3. **Draft Phase B** (DeepSeek/GLM/Qwen - continue)
   - Sections 4-6
   - Boxes 2-3
   - Tables 1-3
   - Remaining citations
   - Target: ~4500 words (total ~10,000)

4. **Review Round 1** (GLM - review)
   - Assess narrative coherence
   - Check technical accuracy
   - Verify citation completeness
   - Provide specific feedback

5. **Final Integration** (Claude - execute)
   - Incorporate review feedback
   - Finalize reference list
   - Format for publication
   - Add figure captions

6. **Archive Session** (Claude - execute)
   - Save final summary
   - Archive artifacts

### Artifact Flow

```
OUTLINE_PATH
    ↓
foundation_analysis
    ↓
OUTLINE_PATH (used again)
    ↓
draft_phase_a
    ↓
OUTLINE_PATH + draft_phase_a (used)
    ↓
draft_complete
    ↓
draft_complete + review_structure
    ↓
final_paper
```

---

## Configuration

### Environment Variables Required

```bash
# DeepSeek API
export DEEPSEEK_API_KEY="your-deepseek-key"

# GLM API
export GLM_API_KEY="your-glm-key"

# Claude API (optional, for integration stages)
export ANTHROPIC_API_KEY="your-claude-key"

# Ollama (for Qwen local model)
# No environment variable needed if Ollama is running on localhost:11434
```

### Config File

**Location:** `scripts/ai_wrappers/multimodel_config.json`

**Key Settings:**
- `max_tokens`: Default output length per model
- `temperature`: Response randomness (0.0-1.0)
- `num_ctx`: Context window (Ollama only)
- `timeout_seconds`: Maximum wait time for API calls

---

## Advantages Over Old Architecture

### 1. True Collaboration
- **Old:** Models were isolated, couldn't see each other's work
- **New:** Artifact passing enables genuine collaboration

### 2. Flexibility
- **Old:** Fixed roles (reasoning, reviewing, executing)
- **New:** Any model can take any task type

### 3. Long Content Support
- **Old:** ~3000 token limit, outputs truncated
- **New:** Configurable limits up to 8000+, continuation support

### 4. Self-Healing
- **Old:** Failed stage = workflow failure
- **New:** Automatic retry with alternative models, workflow continues

### 5. Visibility
- **Old:** Hard to track progress across stages
- **New:** Complete state file with execution log and artifacts

---

## Migration Path

For existing multimodel-coo workflows:

1. **Update Configuration:**
   ```bash
   # Backup old config
   cp scripts/ai_wrappers/multimodel_config.json scripts/ai_wrappers/multimodel_config_old.json

   # Use new config
   cp scripts/ai_wrappers/multimodel_config_new.json scripts/ai_wrappers/multimodel_config.json
   ```

2. **Update Skill Definition:**
   - Update skill metadata to reference `workflow_orchestrator.py` instead of old phase sequence
   - Add new command examples in skill documentation

3. **Test with Simple Task:**
   ```bash
   python scripts/ai_wrappers/universal_wrapper.py \
       --model qwen \
       --task reason \
       --write-file test_output.md \
       --prompt "Analyze this simple task"
   ```

4. **Run Full Workflow:**
   ```bash
   python scripts/workflow_orchestrator.py \
       --session-id test-$(date +%Y%m%d-%H%M%S) \
       --outline path/to/your/outline.md
   ```

---

## Troubleshooting

### Issue: Model cannot read file

**Symptom:** Error "Failed to read file: path"

**Solution:**
- Ensure file path is absolute (starts with drive letter on Windows)
- Use forward slashes even on Windows: `<PROJECT_ROOT>/workspace/...`
- Check file exists: `ls "<PROJECT_ROOT>/workspace/..."`

### Issue: Output still truncated

**Symptom:** "Warning: Output appears truncated"

**Solution:**
- Increase `--max-tokens` (try 12000 for very long tasks)
- Use `--task continue` to resume from truncation point
- Check model API limits (some have hard caps)

### Issue: Stage stuck in dependency loop

**Symptom:** "Cannot proceed. Stages stuck: [...]"

**Solution:**
- Check `depends_on` lists in workflow definition
- Ensure no circular dependencies (A→B→A)
- Check stage status in workflow_state.json

### Issue: Required artifact not found

**Symptom:** "Error: Required artifact 'X' not found"

**Solution:**
- Check that previous stage completed successfully
- Verify artifact was registered in global_artifacts
- Check artifact name spelling matches

---

## Future Enhancements

1. **Parallel Stage Execution:** Run independent stages simultaneously
2. **Live Monitoring:** Real-time progress updates during workflow execution
3. **Smart Continuation:** Automatic detection and resumption of truncated outputs
4. **Model Selection Logic:** Automatically choose best model based on task characteristics
5. **Artifact Versioning:** Track multiple versions of same artifact
6. **Web Interface:** Visual workflow builder and execution monitor

---

## Design Philosophy

This architecture embodies these principles:

1. **Stateful:** Everything is tracked and persisted
2. **Resilient:** Failures don't stop the whole workflow
3. **Transparent:** Full visibility into what happened and why
4. **Composable:** Workflows are built from reusable stages
5. **Adaptive:** System can learn and adjust based on execution history

---

*Architect V2: True Collaboration*
*Designed to solve the fundamental problems of the original multimodel-coo*
*Created: 2026-04-16*
