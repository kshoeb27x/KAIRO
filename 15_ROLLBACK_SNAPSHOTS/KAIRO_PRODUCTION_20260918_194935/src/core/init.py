"""Interactive KAIRO V1 launcher."""

from __future__ import annotations

from src.core import KairoCore


def main() -> None:
    kairo = KairoCore()

    print("=" * 56)
    print("                    KAIRO V1")
    print("              AI SYSTEM CORE ONLINE")
    print("=" * 56)

    status = kairo.status()

    print(f"System   : {status['system']}")
    print(f"Version  : {status['version']}")
    print(f"Core     : {status['core']}")
    print(f"Security : {status['security']}")
    print(f"Mode     : {status['mode']}")
    print()
    print("Type 'exit' to close KAIRO.")
    print()

    while True:
        try:
            user_input = input("YOU   > ")
        except (KeyboardInterrupt, EOFError):
            print("\nKAIRO shutting down.")
            break

        response = kairo.respond(user_input)

        if response == "__EXIT__":
            print("KAIRO  > Shutting down safely.")
            break

        print(f"KAIRO  > {response}")


if __name__ == "__main__":
    main()
    