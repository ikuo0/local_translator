#!/usr/bin/env python3
"""
SR1000 Progress Monitor
リアルタイムでSR1000の進捗を表示
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from collections import defaultdict

from impl_translator.src.libs import job


def monitor_sr1000(working_dir: Path, follow: bool = True, filter_phase: str = None):
    """
    SR1000 の進捗をリアルタイム表示
    
    Args:
        working_dir: SR1000 ワーキングディレクトリ
        follow: tail -f のように追従するか
        filter_phase: 特定フェーズだけを表示（sf001, sf002, sf003, sf004）
    """
    working_dir = Path(working_dir)
    
    # Log file を探す（job/log.txt か log.txt）
    log_file = None
    if (working_dir / "job" / "log.txt").exists():
        log_file = working_dir / "job" / "log.txt"
    elif (working_dir / "log.txt").exists():
        log_file = working_dir / "log.txt"
    
    if log_file is None:
        print(f"Log file not found in {working_dir}", file=sys.stderr)
        return 1

    # 表示フォーマット
    phase_names = {
        "sf001": "PDF→HTML",
        "sf002": "前処理",
        "sf003": "翻訳",
        "sf004": "復元",
    }
    
    page_status = defaultdict(lambda: {"phase": None, "details": None})
    
    def process_line(line):
        """ログ行を処理して表示"""
        line = line.strip()
        if not line:
            return
        
        # ログ行をパース: [時間] [レベル] メッセージ
        if "[INFO]" not in line and "[WARNING]" not in line and "[ERROR]" not in line:
            return
        
        # ページIDを抽出
        if "[page_" not in line:
            return
        
        # ページIDを抽出
        page_id = None
        if "[page_" in line:
            try:
                start = line.index("[page_")
                end = line.index("]", start)
                page_id = line[start+1:end]
            except:
                return
        
        if not page_id:
            return
        
        # 大分類フェーズの判定（大文字で検索）
        for step_lower, step_upper in [("sf001", "SF001"), ("sf002", "SF002"), ("sf003", "SF003"), ("sf004", "SF004")]:
            if step_upper in line or step_lower in line.lower():
                phase_name = phase_names.get(step_lower, step_lower)
                
                # フェーズフィルタ
                if filter_phase and step_lower not in filter_phase:
                    return
                
                # 処理内容を抽出
                if "Completed" in line:
                    status = "✅"
                    detail = "完了"
                elif "Failed" in line or "failed" in line:
                    status = "❌"
                    detail = "失敗"
                elif "Batch" in line and "/" in line:
                    # Batch の進捗を抽出
                    try:
                        batch_part = line[line.index("Batch"):]
                        # "Batch N/M" の形式を抽出
                        words = batch_part.split()
                        if len(words) >= 2:
                            detail = f"{words[0]} {words[1]}"
                            status = "🔄"
                        else:
                            detail = phase_name
                            status = "🔄"
                    except:
                        detail = phase_name
                        status = "🔄"
                else:
                    detail = phase_name
                    status = "🔄"
                
                # 表示
                print(f"{status} {page_id:15} {phase_name:8} {detail}")
                
                page_status[page_id]["phase"] = step_lower
                page_status[page_id]["details"] = detail
                return
    
    print(f"Monitoring: {log_file}")
    print("=" * 70)
    print()
    
    try:
        if follow:
            # tail -f でリアルタイム追従
            cmd = ["tail", "-f", str(log_file)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            try:
                for line in process.stdout:
                    process_line(line)
            finally:
                process.terminate()
        else:
            # 既存ログをすべて表示
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    process_line(line)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        return 0


def show_page_summary(working_dir: Path):
    """ページ処理状態のサマリーを表示"""
    working_dir = Path(working_dir)

    if (working_dir / "job.yaml").is_file():
        data = job.load(working_dir.parent, working_dir.name)["data"]
        summary = data.get("summary")
        if summary is not None:
            print_page_summary(
                summary["total"], summary["complete"], summary["error"],
                summary["progress"], summary["pending"],
            )
            return

    # Job directory を探す（job_id/states か states）
    states_dir = None

    # まず job_id/states を試す
    if (working_dir / "job" / "states").exists():
        states_dir = working_dir / "job" / "states"
    # 後方互換性のため、直接 states も試す
    elif (working_dir / "states").exists():
        states_dir = working_dir / "states"
    
    if states_dir is None:
        print("No states directory found")
        return
    
    completed = 0
    failed = 0
    pending = 0
    running = 0
    
    for state_file in sorted(states_dir.glob("*.json")):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            status = state.get("status", "pending")
            if status == "completed":
                completed += 1
            elif status == "failed":
                failed += 1
            elif status == "pending":
                pending += 1
            else:
                running += 1
        except:
            pending += 1
    
    print_page_summary(completed + failed + pending + running, completed, failed, running, pending)


def print_page_summary(total: int, completed: int, failed: int, running: int, pending: int):
    print("\nPage Summary:")
    print(f"  Total:     {total}")
    print(f"  Completed: {completed} ✅")
    print(f"  Failed:    {failed} ❌")
    print(f"  Running:   {running} 🔄")
    print(f"  Pending:   {pending} ⏳")
    print()


def main():
    parser = argparse.ArgumentParser(description="Monitor SR1000 progress")
    parser.add_argument("--working-dir", type=Path, required=True, help="SR1000 working directory")
    parser.add_argument("--job-id", help="Job ID under --working-dir")
    parser.add_argument("--follow", action="store_true", default=True, help="Follow log (default: True)")
    parser.add_argument("--no-follow", dest="follow", action="store_false", help="Don't follow log")
    parser.add_argument("--filter", choices=["sf001", "sf002", "sf003", "sf004"], help="Filter by phase")
    parser.add_argument("--summary", action="store_true", help="Show page summary and exit")
    
    args = parser.parse_args()
    working_dir = args.working_dir
    if args.job_id is not None:
        try:
            working_dir = job.job_directory(working_dir, args.job_id)
        except ValueError as error:
            parser.error(str(error))
        if not working_dir.is_dir():
            parser.error(f"Job does not exist: {args.job_id}")

    if args.summary:
        show_page_summary(working_dir)
        return 0

    return monitor_sr1000(working_dir, follow=args.follow, filter_phase=args.filter)


if __name__ == "__main__":
    sys.exit(main())
