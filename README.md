# I4Twins Multi-Skill Agent

Early prototype for the I4Twins AI Engineer technical task.

## Task scope

The final agent must implement exactly four skills:

- Summarizer
- Translator
- Calculator
- General Chat

The router must accept a free-form user request and return a structured, validated decision. A request may select one skill or at most two skills. Persian input/output must be supported. The calculator will use a real computational tool rather than relying on LLM arithmetic.

The assignment explicitly prioritizes routing correctness, prompt engineering, graph design, code clarity, documentation, Persian handling, and edge cases over production infrastructure.

## Milestone 2: safe calculator

The routing skeleton is preserved, and the calculator skill now performs real,
deterministic arithmetic. The other three skills and multi-skill orchestration
remain placeholders.

Current flow:

    START
      |
      v
    router  -- structured Pydantic RouterDecision
      |
      +--> summarizer      (placeholder)
      +--> translator      (placeholder)
      +--> calculator
             |
             +--> normalize digits/operators
             +--> extract arithmetic expression
             +--> restricted AST evaluator
      +--> general_chat    (placeholder / fallback)
      +--> multi_skill     (orchestration placeholder)
      |
      v
     END

The router returns:

- one or two skill names from the exact four-skill vocabulary;
- an execution mode: single, sequential, or parallel;
- validation that prevents more than two skills, duplicate skills, and inconsistent execution modes.

For two-skill requests, the router distinguishes dependency from independence. For example, "summarize this and translate the summary" is sequential, while an unrelated translation plus calculation can be parallel. The actual two-skill execution strategy will be implemented in a later milestone.

## Project structure

    app/
      graph.py
      llm.py
      router.py
      state.py
      prompts/
        router.py
      skills/
        summarizer.py
        translator.py
        calculator.py
        general_chat.py
    tests/
      test_calculator.py
      test_routing.py
      test_router_schema.py
    docs/
      AI_USAGE.md
    main.py
    requirements.txt
    .env.example

## Setup

Create and activate a Python virtual environment, then install dependencies:

    pip install -r requirements.txt

Copy the environment template:

    cp .env.example .env

On Windows PowerShell:

    Copy-Item .env.example .env

Set OPENROUTER_API_KEY and LLM_MODEL in .env. The final model must be available on a free tier and have no more than 35 billion parameters. The concrete model will be frozen and documented after provider/model verification and routing evaluation.

Run the schema tests:

    pytest

Run the current CLI skeleton:

    python main.py

## Design decisions

### Structured routing

Router output is represented by a Pydantic model rather than parsing free-form model text. This directly supports validation and makes routing failures observable and testable.

### General Chat fallback

Requests that do not clearly require summarization, translation, or calculation route to General Chat. Requests that clearly target a specialized skill but omit necessary information should later be handled inside that skill with a concise clarification rather than being silently reclassified.

### Persian support

The routing prompt explicitly requires understanding both Persian and English.
The calculator normalizes Persian and Arabic digits, Persian decimal and
thousands separators, and a deliberately small set of written operators. For
example, `حاصل ۱۲۵ ضربدر ۳۸ چقدر است؟` is interpreted as `125*38` and evaluated
as `4750`. This is not a complete Persian mathematical-language parser.

### Calculator safety

Natural-language interpretation is separated from computation. The current
interpreter normalizes common English/Persian operator phrases and extracts an
arithmetic expression. The evaluator parses that expression with Python's AST
module and recursively executes only numeric literals, parentheses, unary
`+`/`-`, and binary `+`, `-`, `*`, `/`, `**`, and `%`.

The evaluator never calls `eval`. Names, function calls, attributes,
collections, comparisons, floor division, bitwise operations, booleans, and
other Python syntax are rejected. Expression length, AST node count, exponent
size, result magnitude, and finite numeric results are bounded to reduce
resource-exhaustion risk. Division and modulo by zero return a controlled error.

### Model configuration

The provider/model is environment-configured. Before submission, the exact free-tier provider, model ID, and documented parameter count will be recorded here as required by the brief.

## Next milestones

1. Review the calculator implementation before proceeding.
2. Implement Summarizer, Translator, and General Chat prompts/nodes.
3. Implement sequential and parallel two-skill orchestration.
4. Add 10-15 English/Persian evaluation prompts and report exact routing accuracy.
5. Document prompt-improvement experiments, limitations, assumptions, and production extensions.

## AI usage disclosure

AI assistance is disclosed in docs/AI_USAGE.md, as requested by the task brief.
