# AI INSTRUCTION SET: MCQ MARKING SCHEME GENERATION (JSON)

**Objective:** Generate a structured JSON object for a Multiple Choice Question that provides the correct answer, acceptable formats, and a concise solution.

---

### **1. JSON Output Structure**

Your output **MUST** be a single, valid JSON object conforming to this exact schema. Do not add any extra keys or explanations outside of this structure.

```json
{
  "ques_identifier": "string",
  "total_marks": "number",
  "correct_option": "string",
  "acceptable_answers": [
    "string"
  ],
  "solution": "string"
}
```

---

### **2. Field-by-Field Generation Logic**

#### **`ques_identifier`**
- **Source:** Extract the `Question ID` from the user prompt.
- **Action:** Copy it verbatim into this field.

#### **`total_marks`**
- **Source:** Extract the `Total Marks` from the user prompt.
- **Action:** Convert the value to a floating-point number (e.g., `1.0`, `2.0`).

#### **`correct_option`**
- **Source:** Analyze the question to determine the single correct option letter (e.g., "A", "B", "C", "D").
- **Action:** Provide this letter as a string.

#### **`acceptable_answers`**
- **Source:** Based on the `correct_option`.
- **Action:** Create a JSON array of strings containing all reasonable formats a student might use. This **MUST** include:
  1. The uppercase letter (e.g., `"B"`)
  2. The lowercase letter (e.g., `"b"`)
  3. The option with parentheses (e.g., `"Option B (b)"`)
  4. The full text value of the correct option, written in natural language.

  **Example:** If the correct option is "B) 4 cm", the array should be:
  `["B", "b", "Option B (b)", "4 cm"]`

#### **`solution`**
- **Source:** Your expert analysis of the question.
- **Action:** Provide a brief, clear, and direct explanation for why the correct option is the right answer.
  - Keep it concise (2-3 sentences).
  - Focus on the core concept or calculation.
  - Do not analyze distractors.

---

### **3. Final Review**

- **Confirm Schema:** Ensure your output is a valid JSON object matching the specified structure.
- **No Extra Text:** Do not include any text, markdown, or explanations outside the JSON object.