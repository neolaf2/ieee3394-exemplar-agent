---
name: quiz-generator
description: Creates practice questions, flashcards, and self-assessment quizzes to test understanding
triggers:
  - "quiz me"
  - "test my knowledge"
  - "practice questions"
  - "make flashcards"
  - "self-test"
  - "review questions"
---

# Quiz Generator

Create effective practice assessments for active recall learning.

## Quiz Types

### 1. Quick Check (5 questions)
Fast verification of basic understanding:
- Definition recall
- Simple application
- True/False with explanation

### 2. Comprehensive Review (10-15 questions)
Thorough topic coverage:
- Mix of difficulty levels
- Multiple question types
- Covers all key concepts

### 3. Exam Simulation
Match actual exam conditions:
- Time pressure
- Question format matching real exam
- No hints until completed

### 4. Spaced Repetition Cards
For memorization-heavy content:
- Front: prompt/question
- Back: answer + explanation
- Difficulty rating for scheduling

## Question Types

| Type | Best For | Example |
|------|----------|---------|
| Multiple Choice | Concepts, recognition | "Which of these is an example of..." |
| Short Answer | Definitions, formulas | "Define photosynthesis in your own words" |
| Problem Solving | Application, math | "Calculate the derivative of..." |
| Explain Why | Deep understanding | "Why does X cause Y?" |
| Compare/Contrast | Relationships | "How does mitosis differ from meiosis?" |
| Case Study | Real-world application | "Given this scenario, what would you..." |

## Difficulty Progression

1. **Recall**: What is X?
2. **Understand**: Explain X in your own words
3. **Apply**: Use X to solve this problem
4. **Analyze**: Why does X work this way?
5. **Evaluate**: Is this use of X appropriate?
6. **Create**: Design a new application of X

## Feedback Mode

After each answer:
- ✅ Correct: Brief reinforcement + fun fact
- ❌ Incorrect: Gentle correction + explanation + retry option
- 🤔 Partial: Acknowledge what's right, guide to complete answer

## Example Session

```
📝 Quiz: Organic Chemistry - Functional Groups
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Difficulty: Mixed | Questions: 5 | Time: ~10 min

Q1. [Recall]
What functional group is characterized by a carbon
double-bonded to an oxygen (C=O)?

Your answer: _____

[After answering]
✅ Correct! Carbonyl group.
💡 Fun fact: The carbonyl is so important it appears
in aldehydes, ketones, carboxylic acids, and more!

Q2. [Apply]
Identify all functional groups in this molecule:
CH₃-CH₂-OH

Your answer: _____
```

## Adaptive Behavior

- If student struggles: offer hints, simplify
- If student excels: increase difficulty, add challenge questions
- Track patterns: focus on weak areas in subsequent quizzes
