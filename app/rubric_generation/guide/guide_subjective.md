

# `<Mandatory_Cognitive_Workflow>`

You must follow this exact four-phase process for EACH method provided in the `solution_outline`.

### **Phase 1: Mathematical Mark Calculation**

1.  **Identify Inputs**:
    *   Let `m` = `marks_analysis` (total marks for the question).
    *   Count the total number of steps (`n`) in the current method's `Solution_outline`.

2.  **Calculate Mark Distribution**: You must perform this calculation to determine the number of 1-mark and 0.5-mark steps.
    *   Let `a` = number of 1-mark steps.
    *   Let `b` = number of 0.5-mark steps.
    *   The formulas are:
        *   `a = 2 * m - n`
        *   `b = 2 * n - 2 * m`

3.  **Verify and State the Result**: You must perform a verification calculation and explicitly state the outcome.
    *   **Verification**: Confirm that `(a * 1) + (b * 0.5)` equals `m`.
    *   **State the Plan**: Clearly state the values and your plan in your internal thought process. This is a mandatory checkpoint.
    *   **Example**: "Internal Checkpoint: m=5, n=7. Calculation: a = 2*5 - 7 = 3; b = 2*7 - 2*5 = 4. Verification: (3 * 1) + (4 * 0.5) = 3 + 2 = 5. This matches m. Correct. I will assign 1 mark to exactly 3 steps and 0.5 marks to exactly 4 steps."

### **Phase 2: Strategic Allocation Plan**

1.  **Analyze Assessment Intent**: Deeply analyze the `assessment_intent` and the `ques_text`. What is the most critical skill being tested? Is it the final answer? The application of a specific formula? The initial setup?

2.  **Select and Prioritize Steps**: Review all `n` steps. You must select **exactly `a`** of the most crucial steps to be awarded 1 mark. The remaining **`b`** steps will be awarded 0.5 marks. Your selection must be based on which steps most directly reflect the core `assessment_intent`.
    *   **High-Priority Steps (Candidates for 1 Mark)**:
        *   The final, correct answer.
        *   The critical calculation or logical leap that is central to the solution.
        *   Correct application of a complex formula.
        *   A step that demonstrates significant understanding or synthesis of concepts.
    *   **Lower-Priority Steps (Candidates for 0.5 Marks)**:
        *   Initial setup or data extraction.
        *   Substitution of values into a formula.
        *   Intermediate, straightforward calculations.
        *   Stating a known formula.

3.  **Create and Justify the Plan**: Write a clear, step-by-step allocation plan. For each of the `a` steps you've chosen for 1 mark, provide a brief but explicit justification linking it to the `assessment_intent`.
    *   **Example Justification**: "Allocation Plan: I will assign 1 mark to Step 4 and Step 5. Step 4 gets 1 mark because it represents the correct application of the quadratic formula, which is the core `assessment_intent`. Step 5 gets 1 mark as it is the final, correct answer. The remaining steps (1, 2, 3) will receive 0.5 marks as they are preparatory."

### **Phase 3: Step-by-Step Mark Assignment**

1.  **Execute the Plan**: Iterate through each step of the method and assign the `marks` value ("1" or "0.5") according to your allocation plan from Phase 2.
2.  **Transfer Data**: Directly transfer the following fields from the solution outline step to the corresponding JSON `markingPoints` object:
    *   `stepId`
    *   `MarkType`
    *   `Teacher Expectation`
    *   `Pass if`
    *   `Fail if`
3.  **Generate Annotations**: For each step, write a concise and practical `guidance` comment. This string **MUST** provide actionable advice for the marker by referencing and applying the terminology and principles from the `<CIE_Marking_Glossary>` (e.g., soi...', 'Apply ecf from step 2.', 'cao').

<CIE_Marking_Glossary>
ft or ecf: Follow Through / Error Carried Forward. The core principle of fairness. Penalize a mistake only once at the point it is made. If a student uses their incorrect value correctly in subsequent steps, award all applicable M and A ft marks. This applies only to marks explicitly annotated with ft or ecf.
cao: Correct Answer Only. No variations are accepted.
cso: Correct Solution Only. The entire working leading to the answer must be free of errors.
dep: Dependent. This mark can only be awarded if a specified previous mark has been awarded.
isw: Ignore Subsequent Working. If a student provides a correct answer and then continues with incorrect working, do not penalize the correct part.
oe: Or Equivalent. Alternative correct answers, wordings, or methods are acceptable.
soi: Seen or Implied. The evidence for the mark is either written explicitly or can be logically inferred from the student's subsequent steps.
www: Without Wrong Working. The mark is awarded only if the correct answer has not been arrived at from incorrect logic.
SC: Special Case. Used to define credit for a specific, common non-standard response that shows some understanding.
nfww: Not From Wrong Working.

### **Phase 4: Final Assembly**

1.  **Construct JSON**: Assemble the processed data from all methods into the final JSON structure as specified in `<Output_JSON_Schema>`.
2.  **Generate Question Notes**: Write a high-level `Question_specific_notes` string. This should provide overall guidance for grading the entire question, such as common pitfalls, acceptable alternative approaches, or the importance of checking for "Error Carried Forward" (ecf).

---

# `<Output_JSON_Schema>`

The final output **MUST** be a single JSON object that strictly adheres to this schema.

```json
{
    "type": "object",
    "properties": {
        "ques_identifier": {"type": "string"},
        "methods": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "methodName": {"type": "string"},
                    "markingPoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "stepId": {"type": "string"},
                                "MarkType": {"type": "string", "enum": ["B", "M", "A"]},
                                "marks": {"type": "string", "enum": ["0.5", "1"]},
                                "Teacher Expectation": {"type": "string"},
                                "Pass if": {"type": "string"},
                                "Fail if": {"type": "string"},
                                "guidance": {"type": "string"}
                            },
                            "required": ["stepId", "MarkType", "marks", "Teacher Expectation", "Pass if", "Fail if", "guidance"]
                        }
                    }
                },
                "required": ["methodName", "markingPoints"]
            }
        },
        "Question_specific_notes": {"type": "string"}
    },
    "required": ["ques_identifier", "methods", "Question_specific_notes"]
}
```