"""
Visualization Evaluator - validates Manim scripts against audio narration
"""
from __future__ import annotations
import ast
import re
from typing import List, Tuple, Optional
from utils.llm_client import LLMClient
from utils.prompt_loader import PromptLoader
from utils.file_manager import FileManager
from pipeline.rag_client import RAGClient
import config


class VisualizationEvaluator:
    """Evaluates Manim scripts for quality, correctness, and audio alignment."""

    def __init__(self, llm_client: LLMClient, prompt_loader: PromptLoader):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.system_prompt = self.prompt_loader.load_prompt(config.VISUAL_EVALUATOR_PROMPT_PATH)
        self.rag_client = None
        if getattr(config, "RAG_ENABLED", False):
            try:
                self.rag_client = RAGClient()
                print("✓ RAG Client initialized for visualization evaluation")
            except Exception:
                print("⚠ RAG Client unavailable for visualization evaluation")

    def evaluate(
        self,
        audio_script: str,
        manim_script: str,
        segment_results: Optional[List[dict]],
        file_manager: FileManager,
        attempt: int = 1,
    ) -> Tuple[bool, str, str]:
        """Run a quality and correctness review of the Manim script."""
        print(f"\n{'='*60}")
        print(f"MANIM EVALUATOR - Attempt {attempt}")
        print(f"{'='*60}")

        timing_summary = self._summarize_timing(segment_results)
        run_times = self._extract_run_times(manim_script)
        expected_phrases = self._count_phrases(segment_results)
        syntax_note = self._check_python_syntax(manim_script)
        rag_context = self._get_rag_context(audio_script)

        payload = f"""
SESSION OVERVIEW:
- Attempt: {attempt}
- Timing data available: {'yes' if segment_results else 'no'}
- Expected phrase count: {expected_phrases}
- Detected run_time count: {len(run_times)}
- Detected run_times (seconds): {run_times if run_times else 'None found'}
- Python syntax pre-check: {syntax_note}

TIMING SUMMARY (from TTS):
{timing_summary if timing_summary else 'No timing data available. Focus on structure and intent.'}

AUDIO SCRIPT (narration):
{audio_script}

MANIM SCRIPT (to evaluate):
{manim_script}

RAG CONTEXT (examples/best practices):
{rag_context if rag_context else 'RAG disabled or unavailable.'}
"""

        evaluation = self.llm_client.generate_response(
            system_prompt=self.system_prompt,
            query=payload,
            temperature=getattr(config, "TEMPERATURE_VISUAL_EVALUATOR", 0.1),
        )

        filename = f"visual_evaluation_attempt_{attempt}.txt"
        filepath = file_manager.save_text(evaluation, filename, "video")
        print(f"✓ Visualization evaluation saved: {filepath}")

        is_approved = self._parse_verdict(evaluation)
        if is_approved:
            print("✓ Manim script APPROVED")
        else:
            print("✗ Manim script needs revision")

        return is_approved, evaluation, filepath

    def _parse_verdict(self, evaluation: str) -> bool:
        """Parse LLM verdict to decide approval status."""
        verdict_match = re.search(r"overall verdict:\s*\[?(approved|revise|reject)\]?", evaluation, re.IGNORECASE)
        if verdict_match:
            return verdict_match.group(1).lower() == "approved"

        # Fallback: look for pass/fail language
        lower_eval = evaluation.lower()
        if "approved" in lower_eval and "not approved" not in lower_eval:
            return True
        if "pass" in lower_eval and "fail" not in lower_eval:
            return True
        return False

    def _summarize_timing(self, segment_results: Optional[List[dict]]) -> str:
        if not segment_results:
            return ""
        summary_lines = []
        for seg in segment_results:
            seg_num = seg.get("segment_number", "?")
            duration = seg.get("duration", 0)
            phrases = seg.get("phrases", []) or []
            summary_lines.append(f"SEGMENT {seg_num}: total {duration:.2f}s, phrases: {len(phrases)}")
            for idx, phrase in enumerate(phrases, start=1):
                text = phrase.get("text", "").strip().replace("\n", " ")
                text = text[:140] + ("..." if len(text) > 140 else "")
                summary_lines.append(f"  - P{idx} ({phrase.get('duration', 0):.2f}s): {text}")
        return "\n".join(summary_lines)

    def _extract_run_times(self, manim_script: str) -> List[float]:
        return [float(m) for m in re.findall(r"run_time\s*=\s*([0-9]*\.?[0-9]+)", manim_script)]

    def _count_phrases(self, segment_results: Optional[List[dict]]) -> int:
        if not segment_results:
            return 0
        return sum(len(seg.get("phrases", []) or []) for seg in segment_results)

    def _check_python_syntax(self, manim_script: str) -> str:
        try:
            ast.parse(manim_script)
            return "No syntax errors detected by ast.parse()"
        except SyntaxError as exc:
            return f"Syntax issue near line {exc.lineno}: {exc.msg}"
        except Exception as exc:  # pragma: no cover - defensive
            return f"Syntax check failed: {exc}"

    def _get_rag_context(self, audio_script: str) -> str:
        if not self.rag_client:
            return ""
        topic_hint = self._infer_topic(audio_script)
        query = f"manim 3b1b style animation patterns for {topic_hint} with timing and cleanup"
        try:
            return self.rag_client.retrieve_context(query=query, top_k=3)
        except Exception as exc:  # pragma: no cover - defensive
            return f"RAG retrieval failed: {exc}"

    def _infer_topic(self, audio_script: str) -> str:
        if not audio_script:
            return "mathematics concept"
        # Use first sentence as a hint to steer RAG retrieval.
        snippet = audio_script.strip().split(".")[0]
        return snippet[:120]
