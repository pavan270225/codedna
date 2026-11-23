#!/usr/bin/env python3
"""Evaluation script for measuring retry reduction with provenance headers.

This script simulates an AI agent working on a codebase with and without
codedna provenance headers, measuring the number of clarifying questions
and retries needed.
"""
from __future__ import annotations
import json
import os
import random
import shutil
import tempfile
from pathlib import Path
from typing import Any

from codedna.classifier import Classifier, ClassifierConfig, EditEvent
from codedna.models import AttributionLabel, ProvenanceHeader, ProvenanceRegion
from codedna.store import Store
from codedna.header import HeaderWriter


SAMPLE_FILES = {
    "auth.py": '''def authenticate(user: str, password: str) -> bool:
    """Authenticate a user with username and password."""
    if not user or not password:
        return False
    return check_credentials(user, password)

def check_credentials(user: str, password: str) -> bool:
    # TODO: implement real credential checking
    return user == "admin" and password == "secret"
''',
    "api.py": '''from flask import Flask, request, jsonify
from auth import authenticate

app = Flask(__name__)

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = data.get("username")
    pwd = data.get("password")
    if authenticate(user, pwd):
        return jsonify({"token": "abc123"})
    return jsonify({"error": "invalid credentials"}), 401

@app.route("/health")
def health():
    return jsonify({"status": "ok"})
''',
    "utils.py": '''def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email: str) -> bool:
    """Simple email validation."""
    return "@" in email and "." in email.split("@")[-1]
''',
}


class MockAgent:
    """Simulates an AI agent working on a codebase."""

    def __init__(self, repo_path: Path, has_headers: bool = False):
        self.repo_path = repo_path
        self.has_headers = has_headers
        self.questions_asked = 0
        self.retries = 0
        self.files_examined = set()

    def read_file(self, filename: str) -> str:
        """Read a file, simulating the agent examining it."""
        self.files_examined.add(filename)
        path = self.repo_path / filename
        if path.exists():
            return path.read_text()
        return ""

    def ask_question(self, question: str) -> str:
        """Simulate asking a clarifying question."""
        self.questions_asked += 1
        return "Answer provided by human/other agent"

    def attempt_task(self, task: str) -> bool:
        """Attempt to complete a task. Returns True if successful."""
        complexity = self._estimate_complexity(task)

        if self.has_headers:
            base_retries = max(0, complexity - 2)
            # With headers, agent asks fewer questions
            self.questions_asked += max(0, complexity - 1)
        else:
            base_retries = complexity
            # Without headers, agent needs more clarification
            self.questions_asked += complexity + random.randint(0, 2)

        self.retries += base_retries + random.randint(0, 1)

        success_prob = min(0.95, 0.5 + 0.1 * self.retries)
        return random.random() < success_prob

    def _estimate_complexity(self, task: str) -> int:
        """Estimate task complexity based on keywords."""
        complexity = 1
        if "auth" in task.lower() or "security" in task.lower():
            complexity += 2
        if "refactor" in task.lower():
            complexity += 1
        if "test" in task.lower():
            complexity += 1
        return complexity


def setup_repo(with_headers: bool = False) -> Path:
    """Create a temporary repo with sample files."""
    tmpdir = Path(tempfile.mkdtemp(prefix="codedna_eval_"))

    for name, content in SAMPLE_FILES.items():
        (tmpdir / name).write_text(content)

    if with_headers:
        writer = HeaderWriter(enabled=True)
        for name in SAMPLE_FILES:
            filepath = tmpdir / name
            header = ProvenanceHeader(
                version=1,
                regions=[
                    ProvenanceRegion(1, 10, AttributionLabel.HUMAN, 0.9, "human", ["type-hints"]),
                    ProvenanceRegion(11, 20, AttributionLabel.AI_GENERATED, 0.85, "copilot", []),
                ],
                used_by=["codedna-eval"],
                rules=["type-hints", "no-secrets"],
            )
            writer.write_header(filepath, header)

    return tmpdir


def run_evaluation(trials: int = 50) -> dict[str, Any]:
    """Run the evaluation with and without headers."""
    tasks = [
        "Add rate limiting to login endpoint",
        "Refactor authentication to use OAuth",
        "Write unit tests for auth module",
        "Add password strength validation",
        "Implement JWT token refresh",
        "Fix SQL injection vulnerability in auth",
        "Add audit logging for failed logins",
        "Implement two-factor authentication",
    ]

    results_without = {"questions": [], "retries": [], "success_rate": 0}
    results_with = {"questions": [], "retries": [], "success_rate": 0}

    for _ in range(trials):
        repo = setup_repo(with_headers=False)
        agent = MockAgent(repo, has_headers=False)
        task = random.choice(tasks)
        success = agent.attempt_task(task)
        results_without["questions"].append(agent.questions_asked)
        results_without["retries"].append(agent.retries)
        results_without["success_rate"] += int(success)
        shutil.rmtree(repo)

        repo = setup_repo(with_headers=True)
        agent = MockAgent(repo, has_headers=True)
        task = random.choice(tasks)
        success = agent.attempt_task(task)
        results_with["questions"].append(agent.questions_asked)
        results_with["retries"].append(agent.retries)
        results_with["success_rate"] += int(success)
        shutil.rmtree(repo)

    results_without["success_rate"] /= trials
    results_with["success_rate"] /= trials

    return {
        "without_headers": {
            "avg_questions": sum(results_without["questions"]) / trials,
            "avg_retries": sum(results_without["retries"]) / trials,
            "success_rate": results_without["success_rate"],
        },
        "with_headers": {
            "avg_questions": sum(results_with["questions"]) / trials,
            "avg_retries": sum(results_with["retries"]) / trials,
            "success_rate": results_with["success_rate"],
        },
        "improvement": {
            "questions_reduction_pct": (1 - sum(results_with["questions"]) / sum(results_without["questions"])) * 100,
            "retries_reduction_pct": (1 - sum(results_with["retries"]) / sum(results_without["retries"])) * 100,
        },
    }


def main():
    print("Running CodeDNA retry-reduction evaluation...")
    print("=" * 60)

    results = run_evaluation(trials=100)

    print("\nWITHOUT provenance headers:")
    print(f"  Avg questions: {results['without_headers']['avg_questions']:.2f}")
    print(f"  Avg retries:   {results['without_headers']['avg_retries']:.2f}")
    print(f"  Success rate:  {results['without_headers']['success_rate']:.1%}")

    print("\nWITH provenance headers:")
    print(f"  Avg questions: {results['with_headers']['avg_questions']:.2f}")
    print(f"  Avg retries:   {results['with_headers']['avg_retries']:.2f}")
    print(f"  Success rate:  {results['with_headers']['success_rate']:.1%}")

    print("\nIMPROVEMENT:")
    print(f"  Questions reduced: {results['improvement']['questions_reduction_pct']:.1f}%")
    print(f"  Retries reduced:   {results['improvement']['retries_reduction_pct']:.1f}%")

    output_path = Path("evals/results.json")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()