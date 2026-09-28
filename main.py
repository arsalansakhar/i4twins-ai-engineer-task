"""Minimal CLI entry point for the prototype."""

from app.graph import build_graph


def main() -> None:
    graph = build_graph()
    print("I4Twins Multi-Skill Agent -- Milestone 1")
    print("Type 'exit' to quit.")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        result = graph.invoke({"user_input": user_input})
        print(f"Assistant: {result['final_response']}")


if __name__ == "__main__":
    main()
