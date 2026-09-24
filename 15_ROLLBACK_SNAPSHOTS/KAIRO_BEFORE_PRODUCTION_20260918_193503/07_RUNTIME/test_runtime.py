import sys
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(RUNTIME_ROOT))

from Events.event_bus import EventBus
from State.runtime_state import RuntimeState
from Task_Manager.task_manager import TaskManager


def main() -> None:

    state = RuntimeState()
    events = EventBus()
    tasks = TaskManager(state, events)

    print("================================")
    print("       KAIRO RUNTIME V1")
    print("================================")

    print()
    print("RUNTIME STATE")
    print(state.snapshot())

    print()
    print("CREATING TASK")

    task = tasks.create("Test KAIRO Runtime")

    print(task)

    print()
    print("TASKS")

    for item in tasks.list_tasks():
        print(item)

    print()
    print("EVENTS")

    for event in events.recent():
        print(event)


if __name__ == "__main__":
    main()