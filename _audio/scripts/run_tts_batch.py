#!/usr/bin/env python3
"""Plan and run bounded parallel TTS synthesis across collection folders.

Planning is offline and writes no audio. A paid run consumes that exact plan,
revalidates every collection, and delegates each collection to
``synthesize_tts_chunks.py`` with its own request and cost confirmations.

Examples:
    python3 run_tts_batch.py recitation --dry-run --write-plan /tmp/recitation-plan.json
    python3 run_tts_batch.py --plan /tmp/recitation-plan.json \
      --confirm-plan <planSha256> --confirm-cost-usd <maximumCostUsd> \
      --max-cost-usd <approved-ceiling> --workers 4
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthesize_tts_chunks as synth  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIO_ROOT = REPO_ROOT / "_audio" / "audio"
DEFAULT_LEDGER_DIR = REPO_ROOT / "_audio" / "ledger"
COLLECTIONS = ("recitation", "ayah", "summary", "surah")
PLAN_SCHEMA_VERSION = 1


def discover_collection_dirs(
    audio_root: Path, collection: str, surah_ids: list[str] | None,
) -> list[Path]:
    root = (audio_root / collection).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Collection root does not exist: {root}")
    if surah_ids:
        if len(set(surah_ids)) != len(surah_ids):
            raise ValueError("Duplicate --surah-id values are not allowed")
        directories = [root / surah_id for surah_id in surah_ids]
    else:
        directories = [
            path
            for path in root.iterdir()
            if path.is_dir()
            and (
                path.name.startswith("S")
                or (collection == "recitation" and path.name == "besmele")
            )
        ]
    directories = sorted(directories, key=lambda path: (path.name != "besmele", path.name))
    missing = [str(path) for path in directories if not path.is_dir()]
    if missing:
        raise ValueError("Missing collection directories: " + ", ".join(missing))
    if not directories:
        raise ValueError(f"No collection directories found under {root}")
    return directories


def plan_digest(plan_without_digest: dict) -> str:
    return synth.sha256_text(synth.stable_json(plan_without_digest))


def preflight_item(
    directory: Path,
    *,
    limit: int | None,
    force: bool,
    reconcile_unknown: bool,
    project_id: str,
) -> dict:
    preflight = synth.preflight_collection(
        directory,
        limit=limit,
        force=force,
        reconcile_unknown=reconcile_unknown,
        project_id=project_id,
    )
    return {
        "directory": str(preflight["surahDir"]),
        "collection": preflight["manifest"]["collection"],
        "surahId": preflight["manifest"]["surahId"],
        "limit": limit,
        "targetChunks": len(preflight["targetChunks"]),
        "remoteChunks": len(preflight["remoteChunks"]),
        "requestSetSha256": preflight["requestDigest"],
        "maximumCostUsd": str(preflight["maximumCostUsd"]),
    }


def build_plan(
    directories: list[Path],
    *,
    workers: int,
    limit: int | None,
    force: bool,
    reconcile_unknown: bool,
    project_id: str,
) -> dict:
    items = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                preflight_item,
                directory,
                limit=limit,
                force=force,
                reconcile_unknown=reconcile_unknown,
                project_id=project_id,
            ): directory
            for directory in directories
        }
        for future in as_completed(futures):
            directory = futures[future]
            try:
                items.append(future.result())
            except Exception as error:
                raise ValueError(f"Preflight failed for {directory}: {error}") from error

    items.sort(key=lambda item: (item["collection"], item["surahId"]))
    total_cost = sum(
        (Decimal(item["maximumCostUsd"]) for item in items), Decimal("0")
    )
    plan = {
        "schemaVersion": PLAN_SCHEMA_VERSION,
        "projectId": project_id,
        "force": force,
        "reconcileUnknown": reconcile_unknown,
        "collections": items,
        "totals": {
            "collections": len(items),
            "targetChunks": sum(item["targetChunks"] for item in items),
            "remoteChunks": sum(item["remoteChunks"] for item in items),
            "maximumCostUsd": str(total_cost),
        },
    }
    plan["planSha256"] = plan_digest(plan)
    return plan


def load_plan(path: Path) -> dict:
    path = path.expanduser().resolve()
    try:
        plan = synth.strict_json_loads(path.expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Batch plan does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid batch plan JSON: {path}: {error}") from error
    if not isinstance(plan, dict) or plan.get("schemaVersion") != PLAN_SCHEMA_VERSION:
        raise ValueError("Unsupported batch plan schema")
    stored_digest = plan.get("planSha256")
    unsigned = dict(plan)
    unsigned.pop("planSha256", None)
    if stored_digest != plan_digest(unsigned):
        raise ValueError("Batch plan digest does not match its contents")
    items = plan.get("collections")
    if not isinstance(items, list) or not items:
        raise ValueError("Batch plan has no collections")
    directories = [item.get("directory") for item in items if isinstance(item, dict)]
    if len(directories) != len(items) or len(set(directories)) != len(directories):
        raise ValueError("Batch plan collection directories must be unique strings")
    return plan


def revalidate_plan(plan: dict, workers: int) -> None:
    expected_items = plan["collections"]
    actual = build_plan(
        [Path(item["directory"]) for item in expected_items],
        workers=workers,
        limit=expected_items[0].get("limit"),
        force=bool(plan.get("force")),
        reconcile_unknown=bool(plan.get("reconcileUnknown")),
        project_id=plan["projectId"],
    )
    actual_items = actual["collections"]
    if actual_items != expected_items:
        raise ValueError(
            "Prepared requests or cached responses changed after planning; create and review a new plan"
        )
    if actual["totals"] != plan.get("totals"):
        raise ValueError("Batch plan totals do not match current preflight")


def sender_command(item: dict, plan: dict, ledger_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "synthesize_tts_chunks.py"),
        item["directory"],
        "--project-id",
        plan["projectId"],
        "--ledger-dir",
        str(ledger_dir.expanduser().resolve()),
    ]
    if item.get("limit") is not None:
        command.extend(["--limit", str(item["limit"])])
    if plan.get("force"):
        command.extend(["--force", "--confirm-force"])
    if plan.get("reconcileUnknown"):
        command.append("--reconcile-unknown")
    if item["remoteChunks"]:
        command.extend(
            [
                "--confirm-remote",
                item["requestSetSha256"],
                "--confirm-cost-usd",
                item["maximumCostUsd"],
                "--max-cost-usd",
                item["maximumCostUsd"],
            ]
        )
    return command


def run_item(item: dict, plan: dict, ledger_dir: Path) -> tuple[str, int]:
    label = f"{item['collection']}/{item['surahId']}"
    print(f"START {label}", flush=True)
    result = subprocess.run(sender_command(item, plan, ledger_dir), check=False)
    print(f"DONE  {label} exit={result.returncode}", flush=True)
    return label, result.returncode


def run_plan(plan: dict, workers: int, ledger_dir: Path) -> int:
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_item, item, plan, ledger_dir): item
            for item in plan["collections"]
        }
        for future in as_completed(futures):
            label, returncode = future.result()
            if returncode:
                failures.append((label, returncode))
    if failures:
        for label, returncode in sorted(failures):
            print(f"FAILED {label} exit={returncode}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", nargs="?", choices=COLLECTIONS)
    parser.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--surah-id", action="append", dest="surah_ids")
    parser.add_argument("--limit", type=int, help="Per-collection chunk limit for a canary plan")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", synth.DEFAULT_PROJECT_ID),
    )
    parser.add_argument("--ledger-dir", type=Path, default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--reconcile-unknown", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--confirm-plan", metavar="PLAN_SHA256")
    parser.add_argument("--confirm-cost-usd", type=synth.decimal_argument)
    parser.add_argument("--max-cost-usd", type=synth.decimal_argument)
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    if args.plan:
        if args.collection or args.dry_run or args.write_plan or args.surah_ids or args.limit:
            parser.error("--plan cannot be combined with planning arguments")
        if args.force or args.reconcile_unknown:
            parser.error("force/reconciliation settings come from the reviewed plan")
        try:
            plan = load_plan(args.plan)
            if args.project_id != plan["projectId"]:
                raise ValueError(
                    f"Plan project {plan['projectId']!r} does not match --project-id {args.project_id!r}"
                )
            if args.confirm_plan != plan["planSha256"]:
                raise PermissionError(
                    f"--confirm-plan must exactly match {plan['planSha256']}"
                )
            total_cost = Decimal(plan["totals"]["maximumCostUsd"])
            if args.confirm_cost_usd != total_cost:
                raise PermissionError(
                    f"--confirm-cost-usd must exactly match {total_cost}"
                )
            if args.max_cost_usd is None or total_cost > args.max_cost_usd:
                raise PermissionError(
                    f"Batch maximum cost {total_cost} exceeds or lacks --max-cost-usd"
                )
            revalidate_plan(plan, args.workers)
        except (OSError, PermissionError, ValueError) as error:
            print(f"Batch execution refused: {error}", file=sys.stderr)
            return 1
        return run_plan(plan, args.workers, args.ledger_dir)

    if not args.collection or not args.dry_run:
        parser.error("planning requires COLLECTION and --dry-run")
    try:
        directories = discover_collection_dirs(
            args.audio_root, args.collection, args.surah_ids
        )
        plan = build_plan(
            directories,
            workers=args.workers,
            limit=args.limit,
            force=args.force,
            reconcile_unknown=args.reconcile_unknown,
            project_id=args.project_id,
        )
        if args.write_plan:
            synth.atomic_write_text(
                args.write_plan.expanduser().resolve(),
                json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            )
    except (OSError, ValueError) as error:
        print(f"Batch preflight failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
