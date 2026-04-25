from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SESSION_ROOT = PROJECT_ROOT / "workspace" / "sessions"


class StageStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageDefinition:
    name: str
    model: str
    task_type: str
    prompt_template: str
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    required_artifacts: list[str] = field(default_factory=list)
    output_artifact: str | None = None
    max_tokens: int | None = None
    can_retry: bool = True
    retry_models: list[str] = field(default_factory=list)
    read_artifact: str | None = None


@dataclass
class WorkflowDefinition:
    name: str
    description: str
    stages: list[StageDefinition]
    session_id: str


class WorkflowOrchestrator:
    def __init__(self, session_dir: Path, dry_run: bool = False):
        self.session_dir = session_dir
        self.state_file = session_dir / "workflow_state.json"
        self.artifacts_dir = session_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self._load_state()

    def _load_state(self) -> None:
        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
            return
        self.state = {
            "workflow_name": "",
            "stages": {},
            "global_artifacts": {},
            "execution_log": [],
        }

    def _save_state(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def execute_workflow(self, workflow: WorkflowDefinition) -> dict[str, Any]:
        print(f"Workflow: {workflow.name}")
        print(f"Session: {workflow.session_id}")
        print(f"Stages: {len(workflow.stages)}")
        self.state["workflow_name"] = workflow.name
        self._save_state()

        executed: set[str] = set()
        results: dict[str, Any] = {}

        while len(executed) < len(workflow.stages):
            ready = [
                stage for stage in workflow.stages
                if stage.name not in executed
                and all(dep in executed for dep in stage.depends_on)
                and self._check_condition(stage.condition)
            ]
            if not ready:
                pending = [stage.name for stage in workflow.stages if stage.name not in executed]
                raise RuntimeError(f"Cannot proceed. Stages stuck: {pending}")

            for stage in ready:
                result = self._execute_stage(stage, workflow.session_id)
                results[stage.name] = result
                executed.add(stage.name)
                if stage.output_artifact and result.get("output_path"):
                    self._register_artifact(stage.output_artifact, result["output_path"], f"Output from {stage.name}")
                if result["status"] == "failed" and not stage.can_retry:
                    raise RuntimeError(f"Stage {stage.name} failed and cannot retry.")

        return results

    def _check_condition(self, condition: str | None) -> bool:
        if not condition:
            return True
        if condition.startswith("output_exists:"):
            return condition.split(":", 1)[1] in self.state["global_artifacts"]
        if condition.startswith("status:"):
            target, expected = condition.split(":", 1)[1].split("==", 1)
            return self.state["stages"].get(target, {}).get("status") == expected
        return False

    def _execute_stage(self, stage: StageDefinition, session_id: str) -> dict[str, Any]:
        print(f"\nStage: {stage.name}")
        print(f"Model: {stage.model}")
        print(f"Task: {stage.task_type}")

        self.state["stages"][stage.name] = {
            "status": StageStatus.IN_PROGRESS.value,
            "model": stage.model,
            "task_type": stage.task_type,
        }
        self._save_state()

        for artifact_name in stage.required_artifacts:
            if artifact_name not in self.state["global_artifacts"]:
                error = f"Missing artifact: {artifact_name}"
                self.state["stages"][stage.name]["status"] = StageStatus.FAILED.value
                self.state["stages"][stage.name]["error"] = error
                self._save_state()
                return {"status": "failed", "error": error}

        prompt = self._build_prompt(stage)
        result = self._call_wrapper(stage, prompt, session_id)

        if result["status"] == "failed" and stage.can_retry and stage.retry_models:
            for retry_model in stage.retry_models:
                retry_stage = StageDefinition(
                    name=f"{stage.name}_retry_{retry_model}",
                    model=retry_model,
                    task_type=stage.task_type,
                    prompt_template=stage.prompt_template,
                    depends_on=stage.depends_on,
                    condition=stage.condition,
                    required_artifacts=stage.required_artifacts,
                    output_artifact=stage.output_artifact,
                    max_tokens=stage.max_tokens,
                    can_retry=False,
                    read_artifact=stage.read_artifact,
                )
                result = self._call_wrapper(retry_stage, prompt, session_id)
                if result["status"] == "completed":
                    break

        self.state["stages"][stage.name]["status"] = result["status"]
        self.state["stages"][stage.name]["output_path"] = result.get("output_path")
        self.state["stages"][stage.name]["bytes_written"] = result.get("bytes_written", 0)
        self.state["stages"][stage.name]["was_truncated"] = result.get("was_truncated", False)
        if result.get("error"):
            self.state["stages"][stage.name]["error"] = result["error"]
        self.state["execution_log"].append(
            {
                "stage": stage.name,
                "model": stage.model,
                "status": result["status"],
                "output_path": result.get("output_path"),
                "truncated": result.get("was_truncated", False),
            }
        )
        self._save_state()
        return result

    def _build_prompt(self, stage: StageDefinition) -> str:
        prompt = stage.prompt_template
        for artifact_name in stage.required_artifacts:
            artifact = self.state["global_artifacts"].get(artifact_name)
            if not artifact:
                continue
            artifact_path = Path(artifact["path"])
            prompt = prompt.replace(f"{{{artifact_name}_path}}", str(artifact_path))
            prompt = prompt.replace(f"{{{artifact_name}_PATH}}", str(artifact_path))
            try:
                prompt = prompt.replace(f"{{{artifact_name}}}", artifact_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return prompt

    def _call_wrapper(self, stage: StageDefinition, prompt: str, session_id: str) -> dict[str, Any]:
        output_path = self.artifacts_dir / f"{stage.name}_output.md"
        wrapper_path = Path(__file__).parent / "ai_wrappers" / "universal_wrapper.py"
        cmd = [
            "python",
            str(wrapper_path),
            "--model",
            stage.model,
            "--task",
            stage.task_type,
            "--write-file",
            str(output_path),
            "--session-id",
            session_id,
            "--stage-name",
            stage.name,
            "--prompt",
            prompt,
        ]
        if stage.max_tokens:
            cmd.extend(["--max-tokens", str(stage.max_tokens)])
        if stage.read_artifact:
            artifact = self.state["global_artifacts"].get(stage.read_artifact)
            if artifact:
                cmd.extend(["--read-file", str(artifact["path"])])

        print(f"Executing: {' '.join(cmd)}")

        if self.dry_run:
            output_path.write_text(f"[DRY RUN]\n\n{prompt}", encoding="utf-8", newline="\n")
            return {"status": "completed", "output_path": str(output_path), "bytes_written": output_path.stat().st_size}

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Timeout after 10 minutes"}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

        if result.returncode != 0:
            return {"status": "failed", "error": result.stderr.strip() or result.stdout.strip()}

        was_truncated = "Warning: Output appears truncated" in result.stdout
        return {
            "status": "completed" if output_path.exists() and not was_truncated else "failed",
            "output_path": str(output_path) if output_path.exists() else None,
            "bytes_written": output_path.stat().st_size if output_path.exists() else 0,
            "was_truncated": was_truncated,
            "stdout": result.stdout,
        }

    def _register_artifact(self, name: str, path: str, description: str) -> None:
        self.state["global_artifacts"][name] = {
            "path": str(path),
            "description": description,
        }
        self._save_state()

    def get_summary(self) -> dict[str, Any]:
        stages = self.state["stages"]
        completed = sum(1 for s in stages.values() if s["status"] == "completed")
        failed = sum(1 for s in stages.values() if s["status"] == "failed")
        truncated = sum(1 for s in stages.values() if s.get("was_truncated"))
        total = len(stages) or 1
        return {
            "workflow_name": self.state["workflow_name"],
            "total_stages": len(stages),
            "completed": completed,
            "failed": failed,
            "truncated": truncated,
            "success_rate": f"{completed / total * 100:.1f}%",
            "artifacts": list(self.state["global_artifacts"].keys()),
        }


def create_nature_review_workflow(session_id: str) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="nature_review_multiscale",
        description="Write Nature Review paper on neural-silicon convergence with multi-model collaboration",
        session_id=session_id,
        stages=[
            StageDefinition(
                name="foundation_analysis",
                model="qwen",
                task_type="reason",
                prompt_template="""Analyze the outline for writing a Nature Review paper.

Input file: {outline_path}

Provide reasoning on:
1. Overall structure and narrative coherence
2. Word count allocation per section
3. Reference distribution strategy
4. Potential challenges and mitigation strategies

Focus on the three-scale framework (BCI/MEA/Organoids) and the structural homogeneity argument.""",
                required_artifacts=["outline"],
                read_artifact="outline",
                output_artifact="foundation_reasoning",
                max_tokens=4000,
            ),
            StageDefinition(
                name="draft_phase_a",
                model="deepseek",
                task_type="write",
                prompt_template="""Write a Nature Review paper following the outline.

Input file: {outline_path}

Use the foundation reasoning as guidance:
{foundation_reasoning}

Write the following parts in a single complete draft:
1. Abstract (<=200 words)
2. Section 1: The Neural-Silicon Interface Imperative (~1500 words)
3. Section 2: BCI at the Macroscale (~2000 words)
4. Section 3: MEA Interfaces at the Mesoscale (~2000 words)

Requirements:
- Title: Neural-silicon convergence: from brain-computer interfaces to organoid intelligence
- Use three-scale framework as interconnected windows, not parallel topics
- AI workflow: dimensionality reduction -> dynamics modeling -> closed-loop control
- Include Box 1: Three-scale terminology table
- Include partial citations using [1], [2] format
- Write for Nature broad audience, narrative style
- Complete all sections fully before stopping

Output format: Complete markdown with proper section headers.""",
                depends_on=["foundation_analysis"],
                required_artifacts=["outline", "foundation_reasoning"],
                read_artifact="outline",
                output_artifact="draft_phase_a",
                max_tokens=8000,
                retry_models=["glm", "claude"],
            ),
            StageDefinition(
                name="draft_phase_b",
                model="deepseek",
                task_type="continue",
                prompt_template="""Continue writing the Nature Review paper.

Input file: {draft_phase_a_path}

Write the following parts to complete the paper:
5. Section 4: Brain Organoids at the Microscale (~1500 words)
6. Section 5: Cross-Scale Integration and Future Directions (~1000 words)
7. Section 6: Conclusions (~500 words)
8. Box 2: Manifold hypothesis explanation
9. Box 3: Neuropixels technology overview
10. Table 1: Technology comparison across scales
11. Table 2: BCI systems comparison
12. Table 3: Organoid-MEA interfaces comparison

Requirements:
- Maintain narrative coherence with previous sections
- Continue from exactly where Phase A left off
- Complete all sections fully
- Include all Boxes and Tables
- Add remaining citations from the outline
- Total target word count: 8000-10000 words

Output format: Append to existing draft, creating complete paper.""",
                depends_on=["draft_phase_a"],
                required_artifacts=["draft_phase_a"],
                read_artifact="draft_phase_a",
                output_artifact="draft_complete",
                max_tokens=8000,
                retry_models=["glm", "qwen"],
            ),
            StageDefinition(
                name="review_structure",
                model="glm",
                task_type="review",
                prompt_template="""Review the complete draft for Nature Review standards.

Input file: {draft_complete_path}

Review criteria:
1. Narrative coherence across all six sections
2. Technical accuracy of scientific claims
3. Citation formatting and completeness
4. Word count and scope coverage
5. Adherence to Nature Review style
6. Overall quality assessment

Provide specific, actionable feedback. Mark any sections that need revision.""",
                depends_on=["draft_phase_b"],
                required_artifacts=["draft_complete"],
                read_artifact="draft_complete",
                output_artifact="review_structure",
                max_tokens=5000,
            ),
            StageDefinition(
                name="final_integration",
                model="claude",
                task_type="execute",
                prompt_template="""Integrate the reviewed draft into a final paper.

Draft: {draft_complete}

Review: {review_structure}

Tasks:
1. Incorporate review feedback into the draft
2. Finalize references and formatting
3. Produce a polished final manuscript""",
                depends_on=["review_structure"],
                required_artifacts=["draft_complete", "review_structure"],
                read_artifact="draft_complete",
                output_artifact="final_paper",
                max_tokens=6000,
            ),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-model workflow orchestrator")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workflow", default="nature_review")
    parser.add_argument("--outline")
    args = parser.parse_args()

    session_dir = SESSION_ROOT / args.session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    orchestrator = WorkflowOrchestrator(session_dir, dry_run=args.dry_run)

    if args.outline:
        outline_path = Path(args.outline)
        if outline_path.exists():
            orchestrator.state["global_artifacts"]["outline"] = {
                "path": str(outline_path.absolute()),
                "description": "Original outline file",
            }
            orchestrator._save_state()

    if args.workflow != "nature_review":
        raise ValueError(f"Unknown workflow: {args.workflow}")
    workflow = create_nature_review_workflow(args.session_id)

    try:
        orchestrator.execute_workflow(workflow)
        summary = orchestrator.get_summary()
        print("\nWORKFLOW COMPLETE")
        for key, value in summary.items():
            print(f"{key}: {value}")
        return 0
    except Exception as exc:
        print(f"Workflow failed: {exc}", file=sys.stderr)
        print(f"Current state saved to: {orchestrator.state_file}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
