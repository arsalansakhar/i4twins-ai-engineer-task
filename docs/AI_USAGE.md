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


For Milestone 7, ChatGPT was used to help:

- design the 15-case English/Persian routing evaluation set;
- implement the live evaluation harness and strict routing metrics;
- add offline validation tests for evaluation coverage;
- research a current free-tier <=35B model candidate and document the evaluation workflow.


Milestone 7 live-evaluation follow-up:
- the first Gemma run was dominated by free-tier/upstream HTTP 429 failures and one non-schema output;
- ChatGPT helped separate provider availability from routing-quality metrics;
- the evaluator was updated with spacing, conservative retry/backoff, and incomplete-run reporting;
- the candidate was changed to Qwen3.8 27B free because the current OpenRouter endpoint is <=35B and supports JSON-schema structured outputs.


Second Milestone 7 live-evaluation follow-up:
- repeated 429s persisted on the Qwen free endpoint despite spacing and retry/backoff;
- the candidate was switched to Liquid LFM2.5-2.6B free, which is <=35B and currently advertises JSON-schema structured outputs on OpenRouter.


Third Milestone 7 live-evaluation follow-up:
- the LFM2.5-2.6B diagnostic run returned 14/15 structured decisions;
- 13/14 completed routes were fully correct (92.9%), but the run remained incomplete;
- one translated-question case violated the one-skill/single-mode invariant;
- one Persian summarize-then-translate case missed the second operation;
- ChatGPT refined only those observed failure modes while keeping the 15-case evaluation set unchanged.
