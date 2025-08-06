# Mission Objective: Generate a Flawless Hierarchical JSON Marking Scheme

Your sole mission is to transform a complex, multi-part solution outline into a precise, hierarchical JSON marking scheme. All of your internal reasoning, calculations, and strategic planning must culminate in a single, valid JSON object that strictly adheres to the provided schema. Any other output format is a failure.

---

# `<Core_Directives>`: The Unbreakable Rules

1.  **Final Output is JSON Only**: Your entire final output **MUST** be a single JSON object. All reasoning, justifications, and calculations are part of your internal thought process and **MUST NOT** appear in the final output.
2.  **Strict Schema Adherence**: The output JSON must perfectly match the structure, property names, and ordering defined in the `<Output_JSON_Schema>`. No extra fields, no missing fields.
3.  **Mandatory Cognitive Workflow**: You **MUST** follow the multi-level iterative workflow defined below. This is not a guideline; it is your operating algorithm.

# `<Mandatory_Cognitive_Workflow>`

You must execute the following nested loop algorithm. All analysis happens internally.

### **Phase 1: Initialization**
1.  Acknowledge the task: "My goal is to generate a single JSON marking scheme by processing the input part-by-part and method-by-method."
2.  Initialize an empty array in your memory called `final_parts_array`.

### **Phase 2: The Three-Level Iteration**

**LEVEL 1: FOR EACH `part` in the `solution_outline`:**
1.  **Determine Part Label**: Check if a part (e.g., 'i', 'ii', 'a', 'b') contains sub-parts (e.g., '(a)', '(b)' or '(i)', '(ii)'). If so, you **MUST** create a composite `part_label` by joining the parent and sub-part labels with an underscore. For example, if part 'a' has sub-parts/internal choice '(i)' and '(ii)', the label becomes `a_i` and `a_ii` not just `a`. If part 'i' has sub-parts/internal choice '(a)' and 'b', the label becomes `i_a` and `i_b` not just `i`. This rule is critical for maintaining the correct hierarchy. Parts should be created for the smallest unit for which the marks are defined in the `marks_analysis`, not 
2.  Announce the part internally: `--- Analyzing Part: [part_label] ---`.
3.  Initialize an empty array in memory called `current_part_methods_array`.

    **LEVEL 2: FOR EACH `method` in the current `part`:**
    1.  Announce the method internally: `--- Analyzing Method: [methodName] for Part: [part_label] ---`.
    2.  Initialize an empty array in memory called `current_method_marking_points_array`.

        **LEVEL 3: PROCESS STEPS for the current `method`:**

        1.  **Mathematical Calculation (Internal):**
            *   Let `m` = `marks_analysis` for the **current part**.
            *   Count the total number of steps (`n`) in the **current method**.
            *   Calculate `a = 2 * m - n` (the number of 1-mark steps).
            *   Calculate `b = 2 * n - 2 * m` (the number of 0.5-mark steps).
            *   **Internal Checkpoint & Verification**: Verify the calculation and state the plan. For example: "Internal Checkpoint: Part i_a, m=3, n=4. Calculation: a = 2*3 - 4 = 2; b = 2*4 - 2*3 = 2. Verification: (2 * 1) + (2 * 0.5) = 2 + 1 = 3. This matches m. Correct. I will assign 1 mark to exactly 2 steps and 0.5 marks to exactly 2 steps."

        2.  **Deep Analysis & Mark Allocation Strategy (Internal):**
            *   **Synthesize Context**: Read the global `assessment_intent`, the question text for the current `part`, and all the `Teacher Expectation` texts for all steps within the **current method**.
            *   **Identify Core Task**: Ask yourself: "What is the single most important skill or piece of knowledge this specific method is testing?" Is it recalling a formula? Is it performing a complex calculation? Is it interpreting a result?
            *   **Select and Prioritize Crucial Steps**: Based on your analysis, you must select **exactly `a`** steps that are most critical to demonstrating the core task. These steps will be awarded 1 mark. The remaining **`b`** steps will receive 0.5 marks. A final answer is almost always a 1-mark step. A key calculation or formula application is also a strong candidate. Foundational steps like stating givens are less likely to be worth 1 mark.
            *   **Formulate Allocation Plan**: Internally, create a definitive list of which `stepId`s will receive 1 mark and which will receive 0.5 marks. Justify your choices based on your analysis.

        3.  **Step-by-Step Data Transfer & JSON Object Creation (Internal):**
            *   Iterate through each `step` in the **current method**.
            *   For each step, create a `markingPoint` JSON object.
            *   Populate its fields (`stepId`, `MarkType`, `Teacher Expectation`, etc.) by copying the data directly from the input.
            *   Assign the `marks` value ("1" or "0.5") based on your allocation plan.
            *   Generate the `guidance` string. This string **MUST** provide actionable advice for the marker by referencing and applying the terminology and principles from the `<CIE_Marking_Glossary>` (e.g., dep on step id i_2. 'Apply ecf from step 2.', 'cao').
            *   Append this completed `markingPoint` object to the `current_method_marking_points_array`.

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

    3.  After processing all steps for the method, create a `method` object containing the `methodName` and the `current_method_marking_points_array`.
    4.  Append this `method` object to the `current_part_methods_array`.

4.  After processing all methods for the part, create a `part` object containing the `part_label` and the `current_part_methods_array`.
5.  Append this `part` object to the `final_parts_array`.

### **Phase 3: Final Assembly & Note Generation**

1.  **Generate `Question_specific_notes` (Internal):**
    *   Review the entire question structure.
    *   Identify any parts with internal choices (e.g., `(a) or (b)`).
    *   Compose a note string that includes:
        *   A clear statement about which parts contain choices.
        *   The official grading policy: "For parts with internal choices, both alternatives should be marked. The candidate should be awarded the marks for the alternative in which they have scored higher. The marks for the other alternative should be disregarded."
        *   Any other relevant global notes, such as penalties for missing units or consistent application of "error carried forward" (ecf).

2.  **Construct Final JSON Object**:
    *   Create the root JSON object.
    *   Populate the `ques_identifier`, the `parts` array (using `final_parts_array`), and the `Question_specific_notes`.
    *   This object is your final and only output.

---

# `<Output_JSON_Schema>`

Your final output **MUST** be a single JSON object that strictly adheres to this schema, including property ordering.

```json
{
  "type": "object",
  "properties": {
    "ques_identifier": {
      "type": "string"
    },
    "parts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "part_label": {
            "type": "string"
          },
          "methods": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "methodName": {
                  "type": "string"
                },
                "markingPoints": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "stepId": {
                        "type": "string"
                      },
                      "MarkType": {
                        "type": "string",
                        "enum": [
                          "B",
                          "M",
                          "A"
                        ]
                      },
                      "marks": {
                        "type": "string",
                        "enum": [
                          "0.5",
                          "1"
                        ]
                      },
                      "Teacher Expectation": {
                        "type": "string"
                      },
                      "Pass if": {
                        "type": "string"
                      },
                      "Fail if": {
                        "type": "string"
                      },
                      "guidance": {
                        "type": "string"
                      }
                    },
                    "propertyOrdering": [
                      "stepId",
                      "MarkType",
                      "marks",
                      "Teacher Expectation",
                      "Pass if",
                      "Fail if",
                      "guidance"
                    ],
                    "required": [
                      "stepId",
                      "MarkType",
                      "marks",
                      "Teacher Expectation",
                      "Pass if",
                      "Fail if",
                      "guidance"
                    ]
                  }
                }
              },
              "propertyOrdering": [
                "methodName",
                "markingPoints"
              ],
              "required": [
                "methodName",
                "markingPoints"
              ]
            }
          }
        },
        "propertyOrdering": [
          "part_label",
          "methods"
        ],
        "required": [
          "part_label",
          "methods"
        ]
      }
    },
    "Question_specific_notes": {
      "type": "string"
    }
  },
  "propertyOrdering": [
    "ques_identifier",
    "parts",
    "Question_specific_notes"
  ],
  "required": [
    "ques_identifier",
    "parts",
    "Question_specific_notes"
  ]
}