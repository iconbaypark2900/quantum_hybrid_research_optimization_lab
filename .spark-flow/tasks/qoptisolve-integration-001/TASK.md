# Task: qoptisolve-integration-001

## Description

Integrate qOptiSolve optimizer modules into quantum_hybrid_research_optimization_lab

## Human-in-the-loop rule

Each agent writes its phase result to:

`.spark-flow/tasks/qoptisolve-integration-001/outbox/<phase>.md`

The human reviews it and runs:

`spark-flow approve <phase>`

or:

`spark-flow reject <phase> "reason"`
