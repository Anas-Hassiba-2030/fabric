#!/usr/bin/env python3
"""Phase 5 — Dual-signal feedback loop (OpsRAG thesis contribution O5).

Provides execution-gated graph admission vs user-feedback-only admission, and a longitudinal
study harness that replays simulated query streams to demonstrate that execution-gated admission
avoids the popularity-bias drift that user-feedback-only admission accumulates over time.

Architecture:
  InteractionRecord — one logged query-response-feedback event
  record_interaction() — creates a record from a query/SUT-response/oracle-result/user-vote
  execution_gated_admit() — admits a runbook pattern to the typed graph ONLY if oracle says correct
  user_gated_admit() — admits only if user accepted (baseline; vulnerable to popularity bias)
  run_longitudinal_study() — replays N interactions, logging accuracy+graph stats every STEP queries
  ablation() — runs both strategies on the same query stream and compares the trajectories
  popularity_bias_stream() — generates a biased stream where the most common question is often
    answered wrongly but users still accept (simulates a popular misconception scenario)

Admits to graph via: distilling a Runbook node into the typed graph (same contract as Phase 2
bootstrap; authored=False since it is machine-learned, not curated).
"""
import json
import os
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class InteractionRecord:
    interaction_id: str
    question_id: str
    question_text: str
    category: str
    difficulty: str
    sut_name: str
    answer: str
    commands: List[Dict]
    oracle_correct: Optional[bool]   # None if oracle not applicable (non-fault question)
    oracle_executable: bool
    user_accepted: bool
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "interaction_id": self.interaction_id,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "category": self.category,
            "difficulty": self.difficulty,
            "sut_name": self.sut_name,
            "oracle_correct": self.oracle_correct,
            "oracle_executable": self.oracle_executable,
            "user_accepted": self.user_accepted,
            "timestamp": self.timestamp,
        }


_interaction_counter = [0]


def record_interaction(
    question: Dict,
    sut_response: Dict,
    oracle_result: Optional[Dict],
    user_accepted: bool,
    sut_name: str = "unknown",
) -> InteractionRecord:
    """Create an InteractionRecord from one query-response-feedback event."""
    _interaction_counter[0] += 1
    iid = f"i-{_interaction_counter[0]:06d}"
    exec_ok = oracle_result.get("executable", False) if oracle_result else False
    correct = oracle_result.get("diagnosis_correct") if oracle_result else None
    return InteractionRecord(
        interaction_id=iid,
        question_id=question.get("id", "?"),
        question_text=question.get("question", ""),
        category=question.get("category", "?"),
        difficulty=question.get("difficulty", "recall"),
        sut_name=sut_name,
        answer=sut_response.get("answer", ""),
        commands=sut_response.get("commands", []),
        oracle_correct=correct,
        oracle_executable=exec_ok,
        user_accepted=user_accepted,
        timestamp=time.time(),
    )


# ---------------------------------------------------------------------------
# Graph admission — the two strategies
# ---------------------------------------------------------------------------

def _distil_to_graph(graph, record: InteractionRecord) -> bool:
    """Add a Runbook node to the typed graph from an interaction record.

    Mirrors the logic in bootstrap.py: creates a Runbook node with authored=False
    (machine-learned, not curated) so it is distinguishable from hand-crafted patterns.
    Returns True if the node was newly added, False if it already existed.
    """
    from .schema import Node, Provenance

    node_id = f"runbook:{record.question_id}:{record.interaction_id}"
    if node_id in graph.nodes:
        return False

    node = Node(
        id=node_id,
        type="Runbook",
        name=f"Auto-distilled: {record.question_text[:80]}",
        provenance=Provenance(
            source=f"feedback/{record.sut_name}",
            confidence=0.8 if record.oracle_correct else 0.5,
            authored=False,
        ),
        attrs={
            "commands": [c.get("cmd", "") for c in record.commands],
            "category": record.category,
            "answer_summary": record.answer[:200],
            "admitted_by": "execution-gated" if record.oracle_correct else "user-gated",
        },
    )
    graph.nodes[node_id] = node
    return True


def execution_gated_admit(graph, record: InteractionRecord) -> bool:
    """Admit to the graph ONLY if the oracle confirmed diagnosis_correct=True.

    This is the thesis's contribution: execution outcome, not user opinion, gates
    what enters the knowledge base. A plausible-sounding but incorrect runbook
    is never admitted regardless of how many users accepted it.
    """
    if record.oracle_correct is True:
        return _distil_to_graph(graph, record)
    return False


def user_gated_admit(graph, record: InteractionRecord) -> bool:
    """Admit to the graph if the user accepted the answer.

    Baseline strategy. Vulnerable to popularity bias: an incorrect answer that is
    confidently delivered and commonly asked will accumulate in the graph.
    """
    if record.user_accepted:
        return _distil_to_graph(graph, record)
    return False


# ---------------------------------------------------------------------------
# Accuracy + coherence measurement helpers
# ---------------------------------------------------------------------------

def _measure_graph_coherence(graph) -> float:
    """Fraction of Runbook nodes in the graph with oracle_correct semantic.

    A 'coherent' graph has only nodes that were admitted by execution-gated policy
    (authored=False, admitted_by=execution-gated). Nodes admitted by user-gated policy
    may include incorrect information — measured as incoherence.
    """
    rb_nodes = [n for n in graph.nodes.values() if n.type == "Runbook" and not n.provenance.authored]
    if not rb_nodes:
        return 1.0  # no machine-learned nodes → trivially coherent
    good = sum(1 for n in rb_nodes if n.attrs.get("admitted_by") == "execution-gated")
    return good / len(rb_nodes)


def _measure_retrieval_accuracy(graph, questions: List[Dict]) -> float:
    """Fraction of questions where the graph contains a relevant node.

    Proxy: category-match — a question's category should appear in at least one node's
    attrs['category']. This is a lightweight proxy for retrieval precision; Phase 6
    replaces with proper MRR/nDCG over embedding retrieval.
    """
    if not questions or not graph.nodes:
        return 0.0
    hits = 0
    for q in questions:
        cat = q.get("category", "")
        for n in graph.nodes.values():
            if n.attrs.get("category") == cat:
                hits += 1
                break
    return hits / len(questions)


# ---------------------------------------------------------------------------
# Longitudinal study harness
# ---------------------------------------------------------------------------

STEP = 100  # log a snapshot every STEP interactions


@dataclass
class LongitudinalSnapshot:
    step: int
    n_interactions: int
    graph_size: int
    coherence: float
    retrieval_accuracy: float
    admitted_count: int
    rejected_count: int


def run_longitudinal_study(
    query_stream: List[Tuple[Dict, Dict, Optional[Dict], bool]],
    admit_fn: Callable,
    graph=None,
    step: int = STEP,
) -> Dict:
    """Replay a query stream and log graph evolution snapshots.

    Args:
        query_stream: list of (question, sut_response, oracle_result, user_accepted) tuples.
        admit_fn: execution_gated_admit or user_gated_admit.
        graph: an OpsRAG Graph to populate (creates a fresh one if None).
        step: snapshot interval in interactions.

    Returns:
        {
          "snapshots": [...],
          "final_graph_size": int,
          "final_coherence": float,
          "final_retrieval_accuracy": float,
          "admitted": int,
          "rejected": int,
        }
    """
    from .schema import Graph

    if graph is None:
        graph = Graph()

    snapshots: List[LongitudinalSnapshot] = []
    admitted = 0
    rejected = 0

    all_questions = [t[0] for t in query_stream]

    for i, (question, sut_response, oracle_result, user_accepted) in enumerate(query_stream):
        record = record_interaction(question, sut_response, oracle_result, user_accepted)
        was_admitted = admit_fn(graph, record)
        if was_admitted:
            admitted += 1
        else:
            rejected += 1

        if (i + 1) % step == 0 or i == len(query_stream) - 1:
            snapshots.append(LongitudinalSnapshot(
                step=i + 1,
                n_interactions=i + 1,
                graph_size=len(graph.nodes),
                coherence=_measure_graph_coherence(graph),
                retrieval_accuracy=_measure_retrieval_accuracy(graph, all_questions),
                admitted_count=admitted,
                rejected_count=rejected,
            ))

    return {
        "snapshots": [
            {
                "step": s.step,
                "graph_size": s.graph_size,
                "coherence": round(s.coherence, 3),
                "retrieval_accuracy": round(s.retrieval_accuracy, 3),
                "admitted": s.admitted_count,
                "rejected": s.rejected_count,
            }
            for s in snapshots
        ],
        "final_graph_size": len(graph.nodes),
        "final_coherence": round(_measure_graph_coherence(graph), 3),
        "final_retrieval_accuracy": round(
            _measure_retrieval_accuracy(graph, all_questions), 3
        ),
        "admitted": admitted,
        "rejected": rejected,
    }


# ---------------------------------------------------------------------------
# Ablation — compare execution-gated vs user-gated on the same stream
# ---------------------------------------------------------------------------

def ablation(
    query_stream: List[Tuple[Dict, Dict, Optional[Dict], bool]],
    step: int = STEP,
) -> Dict:
    """Run both strategies on the same query stream and compare trajectories.

    Returns a dict with 'execution', 'user', and 'delta' keys for the thesis
    ablation table (Table 5 in the draft chapter outline).
    """
    from .schema import Graph

    exec_result = run_longitudinal_study(
        query_stream, execution_gated_admit, Graph(), step=step
    )
    user_result = run_longitudinal_study(
        query_stream, user_gated_admit, Graph(), step=step
    )

    exec_coh = exec_result["final_coherence"]
    user_coh = user_result["final_coherence"]
    exec_ra = exec_result["final_retrieval_accuracy"]
    user_ra = user_result["final_retrieval_accuracy"]

    return {
        "execution_gated": exec_result,
        "user_gated": user_result,
        "delta": {
            "coherence": round(exec_coh - user_coh, 3),
            "retrieval_accuracy": round(exec_ra - user_ra, 3),
            "admitted_delta": exec_result["admitted"] - user_result["admitted"],
        },
        "verdict": (
            "execution-gated dominates"
            if exec_coh > user_coh
            else "user-gated dominates"
            if user_coh > exec_coh
            else "tie"
        ),
    }


# ---------------------------------------------------------------------------
# Query stream generators
# ---------------------------------------------------------------------------

def uniform_stream(
    questions: List[Dict],
    sut_fn: Callable,
    n: int = 1000,
    oracle_hit_rate: float = 0.85,
    user_accept_rate: float = 0.70,
    rng_seed: int = 42,
) -> List[Tuple[Dict, Dict, Optional[Dict], bool]]:
    """Generate N interactions by sampling uniformly from the benchmark.

    oracle_hit_rate: probability that an oracle-applicable question returns diagnosis_correct=True.
    user_accept_rate: probability that a user accepts the answer (independent of correctness).
    """
    rng = random.Random(rng_seed)
    stream = []
    for _ in range(n):
        q = rng.choice(questions)
        resp = sut_fn(q)
        fid = q.get("fault_id")
        if fid:
            correct = rng.random() < oracle_hit_rate
            oracle_result = {"executable": bool(resp.get("commands")), "diagnosis_correct": correct}
        else:
            oracle_result = {"executable": bool(resp.get("commands")), "diagnosis_correct": None}
        user_accepted = rng.random() < user_accept_rate
        stream.append((q, resp, oracle_result, user_accepted))
    return stream


def popularity_bias_stream(
    questions: List[Dict],
    sut_fn: Callable,
    n: int = 1000,
    popular_fraction: float = 0.40,
    popular_wrong_rate: float = 0.60,
    popular_accept_rate: float = 0.80,
    other_oracle_hit_rate: float = 0.85,
    other_accept_rate: float = 0.65,
    rng_seed: int = 99,
) -> List[Tuple[Dict, Dict, Optional[Dict], bool]]:
    """Biased stream where the most popular question is often answered WRONGLY but accepted.

    Models the 'confident wrong answer' scenario: the SUT gives a plausible-sounding but
    incorrect runbook for a common query, and users (lacking deep expertise) accept it.
    The user-gated strategy will admit these wrong runbooks; the execution-gated strategy
    will reject them because the oracle is honest.

    popular_fraction: fraction of interactions that are the single most-asked question.
    popular_wrong_rate: fraction of those popular interactions where oracle says incorrect.
    popular_accept_rate: fraction of popular interactions where user accepts anyway.
    """
    rng = random.Random(rng_seed)
    popular_q = questions[0]  # first question as the 'popular' one for reproducibility
    other_qs = [q for q in questions if q.get("id") != popular_q.get("id")]
    if not other_qs:
        other_qs = questions

    stream = []
    for _ in range(n):
        if rng.random() < popular_fraction:
            q = popular_q
            resp = sut_fn(q)
            fid = q.get("fault_id")
            is_wrong = rng.random() < popular_wrong_rate
            if fid:
                oracle_result = {"executable": bool(resp.get("commands")),
                                 "diagnosis_correct": not is_wrong}
            else:
                oracle_result = {"executable": bool(resp.get("commands")),
                                 "diagnosis_correct": None}
            user_accepted = rng.random() < popular_accept_rate
        else:
            q = rng.choice(other_qs)
            resp = sut_fn(q)
            fid = q.get("fault_id")
            if fid:
                oracle_result = {"executable": bool(resp.get("commands")),
                                 "diagnosis_correct": rng.random() < other_oracle_hit_rate}
            else:
                oracle_result = {"executable": bool(resp.get("commands")),
                                 "diagnosis_correct": None}
            user_accepted = rng.random() < other_accept_rate

        stream.append((q, resp, oracle_result, user_accepted))
    return stream


# ---------------------------------------------------------------------------
# Summary formatter for the thesis table
# ---------------------------------------------------------------------------

def format_ablation_table(result: Dict) -> str:
    """Render the ablation comparison as a plain-text table for the thesis appendix."""
    eg = result["execution_gated"]
    ug = result["user_gated"]
    d = result["delta"]
    lines = [
        "Ablation: execution-gated vs user-feedback-only",
        "-" * 55,
        f"{'Metric':<30} {'Exec-gated':>10} {'User-gated':>10} {'Delta':>8}",
        "-" * 55,
        f"{'Final graph size':<30} {eg['final_graph_size']:>10} {ug['final_graph_size']:>10} {eg['final_graph_size']-ug['final_graph_size']:>+8}",
        f"{'Final coherence':<30} {eg['final_coherence']:>10.3f} {ug['final_coherence']:>10.3f} {d['coherence']:>+8.3f}",
        f"{'Retrieval accuracy':<30} {eg['final_retrieval_accuracy']:>10.3f} {ug['final_retrieval_accuracy']:>10.3f} {d['retrieval_accuracy']:>+8.3f}",
        f"{'Admitted':<30} {eg['admitted']:>10} {ug['admitted']:>10} {d['admitted_delta']:>+8}",
        "-" * 55,
        f"Verdict: {result['verdict']}",
    ]
    return "\n".join(lines)
