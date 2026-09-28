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

## Milestone 7: evaluation suite

The routing skeleton, all four required skills, and sequential/parallel two-skill orchestration are present. A committed 15-case routing evaluation suite now measures live skill detection and execution-mode accuracy against the configured provider.

Current flow:

    START
      |
      v
    router  -- structured Pydantic RouterDecision
      |
      +--> summarizer      (LLM-backed, source-grounded)
      +--> translator      (LLM-backed, faithful transformation)
      +--> calculator
             |
             +--> normalize digits/operators
             +--> extract arithmetic expression
             +--> restricted AST evaluator
      +--> general_chat    (LLM-backed fallback/general Q&A)
      +--> multi_skill
             |
             +--> sequential: skill A -> handoff -> skill B
             +--> parallel: skill A || skill B -> ordered combination
      |
      v
     END

The router returns:

- one or two skill names from the exact four-skill vocabulary;
- an execution mode: single, sequential, or parallel;
- validation that prevents more than two skills, duplicate skills, and inconsistent execution modes.

For two-skill requests, the router distinguishes dependency from independence. `summarize this and translate the summary` is sequential: the first skill result becomes the content processed by the second skill. An independent request such as `translate hello to Persian and calculate 12 * 9` is parallel: both selected skills receive the original request and execute concurrently, then their results are combined in router-selected order.

## Project structure

    app/
      graph.py
      llm.py
      router.py
      state.py
      orchestration.py
      prompts/
        router.py
        summarizer.py
        translator.py
        general_chat.py
      skills/
        summarizer.py
        translator.py
        calculator.py
        general_chat.py
    tests/
      test_calculator.py
      test_routing.py
      test_summarizer.py
      test_translator.py
      test_general_chat.py
      test_orchestration.py
      test_router_schema.py
      test_evaluation_cases.py
    evaluation/
      __init__.py
      evaluation_cases.json
      run_routing_eval.py
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

Set `OPENROUTER_API_KEY` in `.env`; never commit the real key. The current evaluation candidate is `liquid/lfm-2.5-2.6b:free` (LFM2.5-2.6B, 2.6B parameters). It satisfies the assignment's <=35B constraint, is currently available as a free OpenRouter endpoint, and supports JSON-schema structured outputs. The model will be frozen as the final submission model only after the live routing evaluation succeeds.

Run the offline test suite:

    python -m pytest -v

Run the live routing evaluation after configuring `.env`:

    python -m evaluation.run_routing_eval --output evaluation/latest_results.json

The default evaluator delay is 4 seconds between cases to stay below the free-tier per-minute request ceiling.

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

### Summarizer prompt engineering

The summarizer sends the original user request to a dedicated LLM node with a source-grounded system prompt. It preserves important names, numbers, dates, conditions, technical terms, and conclusions; avoids unsupported additions; keeps the source language by default; supports Persian and English; and treats instructions embedded inside source material as content rather than commands.

An initial weak prompt such as `Summarize the user's text clearly and concisely.` leaves important behavior underspecified. The improved prompt explicitly defines factual grounding, preservation of critical details, language behavior, embedded-instruction handling, and user-controlled summary length/style. These additions reduce hallucination, accidental information loss, and prompt-injection-like behavior in text being summarized.

### Translator prompt engineering

The translator treats the source text as data to transform rather than instructions to execute. Its prompt explicitly says not to answer questions, solve tasks, or follow instructions that appear inside source content. It preserves meaning, tone, names, numbers, dates, units, technical terms, and formatting where practical; supports Persian and English; and asks a concise clarification when the target language is genuinely missing.

A weak translation prompt such as `Translate the user's text to the requested language.` does not define how to handle question-like source text or embedded instructions. The improved prompt separates transformation from task execution and adds fidelity, clarification, and formatting rules. For example, `Translate to Persian: What is the capital of France?` should produce a Persian translation of the question rather than answer it.

### General Chat behavior

General Chat handles greetings, small talk, general questions, and requests that do not clearly match the other specialized skills. Its prompt defaults to the user's language, supports Persian and English, keeps casual interactions concise, answers general questions directly, and asks a short clarification when the request is genuinely unclear. It also avoids exposing internal routing or graph details unless explicitly asked.

A weak prompt such as `Be a helpful assistant.` is too broad for a routed multi-skill architecture because it can blur skill boundaries. The final prompt scopes General Chat to fallback/general interaction and explicitly avoids pretending that specialized summarization, translation, or deterministic calculation has occurred.

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

### Multi-skill execution

The graph keeps exactly four user-facing skills. `multi_skill` is a control/orchestration node, not a fifth skill.

For `sequential` decisions, the orchestrator executes the first selected skill, constructs a constrained handoff containing the intermediate result, and invokes the second skill. The final user-visible response is the second skill's result. Calculator handoff is intentionally stricter: only the intermediate result is passed to the calculator so its deterministic extractor cannot accidentally combine numbers from orchestration instructions.

For `parallel` decisions, the two selected skill nodes run concurrently with a two-worker thread pool on the same original request. Their outputs are combined in the router-selected order. This keeps the implementation simple while demonstrating genuine concurrent execution for independent tasks.

### Routing evaluation

The committed evaluation set contains 15 prompts covering all four skills, English and Persian, sequential and parallel two-skill requests, translation of question-like text, a missing-target-language translation case, and a general fallback case.

The live evaluator reports four metrics:

- ordered skill accuracy: exact skill list and order;
- skill-set accuracy: correct selected skills regardless of order;
- execution-mode accuracy: `single`, `sequential`, or `parallel`;
- full-route accuracy: exact ordered skills plus the correct execution mode.

Provider/API failures are reported separately from routing mistakes. Accuracy is calculated only for cases that return a valid structured `RouterDecision`, and the evaluator marks the run incomplete until all 15 cases complete. The runner spaces requests by default and retries one transient rate-limit failure with backoff so free-tier infrastructure problems are not misreported as routing quality.

### Model configuration

The provider/model is environment-configured. Before submission, the exact free-tier provider, model ID, and documented parameter count will be recorded here as required by the brief.

## Next milestones

1. Run the offline suite for the evaluation branch.
2. Run the 15-case live routing evaluation with LFM2.5-2.6B free after the free-tier rate-limit window has reset.
3. Inspect failures and refine the router prompt only when evidence supports a change.
4. Freeze and document the final <=35B model and measured routing accuracy.
5. Run end-to-end smoke cases, then complete assumptions, limitations, production extensions, and the final submission audit.

## AI usage disclosure

AI assistance is disclosed in docs/AI_USAGE.md, as requested by the task brief.
