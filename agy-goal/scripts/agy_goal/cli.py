import argparse
import sys
from pathlib import Path
from agy_goal.core.work_api import WorkAPI

USAGE_HELP = """Usage:
  agy-goal.sh <path/to/plan.md> [--remote <target>]   Implement a plan file via /goal
  agy-goal.sh continue [instructions...]               Continue plan implementation or supply feedback
  agy-goal.sh status                                   Show active session status
  agy-goal.sh sync                                     Synchronize remote changes to local workspace
  agy-goal.sh reset                                    Clear active session state
  agy-goal.sh -h, --help                               Show this help message
"""

def main():
    if len(sys.argv) < 2:
        print(USAGE_HELP, file=sys.stderr)
        sys.exit(1)

    first_arg = sys.argv[1]
    if first_arg in ("-h", "--help", "help"):
        print(USAGE_HELP)
        sys.exit(0)

    api = WorkAPI()

    try:
        if first_arg == "continue":
            instructions = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
            sys.exit(api.continue_plan(instructions))
        elif first_arg == "status":
            st = api.get_status()
            print("Active:          ", st["active"])
            print("Mode:            ", st["mode"])
            if st["target"]:
                print("Target:          ", st["target"])
            print("Branch:          ", st["branch"])
            print(f"Rounds:           {st['round']} / {st['max_rounds']}")
            if st["conversation_id"]:
                print("Conversation ID: ", st["conversation_id"])
            sys.exit(0)
        elif first_arg == "sync":
            api.sync()
            sys.exit(0)
        elif first_arg == "reset":
            api.reset()
            sys.exit(0)
        else:
            plan_parser = argparse.ArgumentParser(
                prog="agy-goal.sh",
                description="agy-goal: Multi-turn runner for AGY plan execution (Local & Remote)",
                add_help=True,
            )
            plan_parser.add_argument("plan", help="Path to implementation plan markdown file")
            plan_parser.add_argument("--remote", help="Remote target ID/node for gt exec")
            args = plan_parser.parse_args(sys.argv[1:])
            sys.exit(api.start_plan(args.plan, remote_target=args.remote))
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
