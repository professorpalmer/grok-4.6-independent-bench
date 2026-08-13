from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
WAVES = (
    JOBS / "grok46-tb3-slash",
    JOBS / "grok46-tb3-errors",
    JOBS / "grok46-tb3-errors2",
)
OUT = ROOT / "terminal-bench-v3-grok-4.6.json"
COQ_LOSS = "coq-block-bound"
NO_NETWORK = "batched-eval-parity"


def task_name(trial_id: str) -> str:
    return trial_id.split("__")[0]


def trial_tokens(job_dir: Path, trial_id: str) -> dict:
    trial = job_dir / trial_id
    result_path = trial / "result.json"
    if not result_path.exists():
        matches = list(job_dir.glob(task_name(trial_id) + "__*"))
        if matches:
            result_path = matches[0] / "result.json"
    if not result_path.exists():
        return {}
    result = json.loads(result_path.read_text())
    agent = result.get("agent_result") or {}
    return {
        "n_input_tokens": agent.get("n_input_tokens"),
        "n_cache_tokens": agent.get("n_cache_tokens"),
        "n_output_tokens": agent.get("n_output_tokens"),
        "n_agent_steps": result.get("n_agent_steps") or agent.get("n_agent_steps"),
    }


def harvest(job_dir: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    graded: dict[str, dict] = {}
    errors: dict[str, dict] = {}
    result_path = job_dir / "result.json"
    if not result_path.exists():
        return graded, errors
    raw = json.loads(result_path.read_text())
    evals = (raw.get("stats") or {}).get("evals") or {}
    if not evals:
        return graded, errors
    ev = next(iter(evals.values()))
    rewards = ((ev.get("reward_stats") or {}).get("reward") or {})
    for key, trial_ids in rewards.items():
        try:
            value = float(key)
        except (TypeError, ValueError):
            continue
        for trial_id in trial_ids:
            name = task_name(trial_id)
            graded[name] = {
                "status": "graded",
                "task": name,
                "reward": 1 if value >= 1.0 else 0,
                "reward_raw": value,
                **trial_tokens(job_dir, trial_id),
            }
    for exc, trial_ids in (ev.get("exception_stats") or {}).items():
        for trial_id in trial_ids or []:
            name = task_name(trial_id)
            if name in graded:
                continue
            errors[name] = {"task": name, "exception": exc, "source": job_dir.name}
    return graded, errors


def mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 1) if xs else None


def main() -> None:
    merged: dict[str, dict] = {}
    unresolved: dict[str, dict] = {}
    for job_dir in WAVES:
        graded, errors = harvest(job_dir)
        for task, row in graded.items():
            merged[task] = {**row, "source": job_dir.name}
            unresolved.pop(task, None)
        for task, row in errors.items():
            if task not in merged:
                unresolved[task] = row

    merged[COQ_LOSS] = {
        "status": "graded",
        "task": COQ_LOSS,
        "reward": 0,
        "reward_raw": 0,
        "source": "agent_timeout_counted_fail",
    }
    unresolved.pop(COQ_LOSS, None)
    if NO_NETWORK not in merged:
        unresolved[NO_NETWORK] = {
            "task": NO_NETWORK,
            "exception": "Docker cannot honor network_mode=no-network",
            "source": "environment",
        }

    passes = [r for r in merged.values() if r.get("reward") == 1]
    fails = [r for r in merged.values() if r.get("reward") != 1]
    n = len(passes) + len(fails)
    payload = {
        "benchmark": "Terminal-Bench v3.0",
        "model": "Grok 4.6 High",
        "date": "2026-08-13",
        "framework": "harbor",
        "environment": "docker",
        "n_tasks": 70,
        "n_gpu_excluded": 4,
        "score": {
            "n_graded": n,
            "n_pass": len(passes),
            "n_fail": len(fails),
            "n_unresolved_infra": len(unresolved),
            "pass_rate": round(len(passes) / n, 4) if n else None,
        },
        "efficiency": {
            "mean_output_tokens": mean([r.get("n_output_tokens") for r in merged.values()]),
            "mean_agent_steps": mean([r.get("n_agent_steps") for r in merged.values()]),
            "mean_input_tokens": mean([r.get("n_input_tokens") for r in merged.values()]),
        },
        "comparators": {
            "note": "Same test: Terminal-Bench v3.0 from the xAI 2026-08-12 card",
            "gpt-5.6-sol-max": {"pass": 0.346},
            "claude-fable-5-max": {"pass": 0.341},
            "xai_card_grok-4.6-high": {"pass": 0.26, "source": "https://x.ai/news/grok-4-6"},
            "grok-4.5-high": {"pass": 0.157},
        },
        "tasks": sorted(merged.values(), key=lambda r: r["task"]),
        "unresolved_infra": sorted(unresolved.values(), key=lambda r: r["task"]),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", OUT, "graded", n, "pass", len(passes), "fail", len(fails), "unresolved", len(unresolved))


if __name__ == "__main__":
    main()
