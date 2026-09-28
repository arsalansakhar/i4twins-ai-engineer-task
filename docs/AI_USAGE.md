# AI Usage Disclosure

AI-assisted development is permitted by the task brief and is disclosed here.

For Milestone 1, ChatGPT was used to help:

- review the take-home specification;
- propose the initial LangGraph architecture;
- define the Pydantic routing contract;
- draft the first routing prompt and repository scaffold;
- review design choices against the task requirements.

The repository will keep this disclosure current as additional AI-assisted work is performed. The candidate remains responsible for understanding, testing, validating, and explaining the submitted implementation.

For Milestone 2, Codex was used to help:

- add mocked tests for the existing router node and graph paths;
- design and implement the restricted AST calculator evaluator;
- add deterministic, adversarial, and Persian-input calculator tests;
- document the calculator architecture, restrictions, and limitations.


For Milestone 3, ChatGPT was used to help:

- design and implement the source-grounded summarizer prompt and node;
- wire the shared LLM instance into the summarizer graph path;
- add mocked English/Persian summarizer tests;
- document prompt-engineering improvements and limitations.


For Milestone 4, ChatGPT was used to help:

- design and implement the faithful translator prompt and node;
- add prompt-injection-resistant translation rules for question-like and instruction-like source text;
- wire the shared LLM instance into the translator path;
- add mocked English/Persian translator tests and documentation.


For Milestone 5, ChatGPT was used to help:

- design and implement the scoped General Chat prompt and node;
- wire the shared LLM instance into the General Chat path;
- add mocked English/Persian greeting and general-question tests;
- document fallback behavior and prompt-scoping rationale.


For Milestone 6, ChatGPT was used to help:

- design and implement the two-skill orchestration control node;
- implement dependent sequential handoff and genuine concurrent parallel execution;
- add orchestration and graph-path tests;
- document execution semantics and calculator-specific handoff safety.
