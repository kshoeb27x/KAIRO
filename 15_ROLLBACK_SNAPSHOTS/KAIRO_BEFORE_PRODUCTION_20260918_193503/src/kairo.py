"""KAIRO V1 entry point."""

from __future__ import annotations

from src.core.kairo_core import KairoCore


def main() -> None:
    kairo = KairoCore()

    print("================================")
    print("        KAIRO V1 ONLINE")
    print("================================")
    print("Type 'status' to check system status.")
    print("Type 'exit' to shut down KAIRO.")
    print()

    while True:
        try:
            message = input("YOU > ")
        except (KeyboardInterrupt, EOFError):
            print("\nKAIRO > Shutting down.")
            break

        response = kairo.respond(message)

        if response == "__EXIT__":
            print("KAIRO > Shutting down.")
            break

        print(f"KAIRO > {response}")


if __name__ == "__main__":
    main()
