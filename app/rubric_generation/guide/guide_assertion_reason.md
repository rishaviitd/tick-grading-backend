# AI INSTRUCTION SET: ASSERTION-REASON MARKING SCHEME (JSON)

**Objective:** Analyze an Assertion-Reason question and generate a structured JSON object containing the correct option, acceptable formats, and a concise explanation.

---

### **1. Analysis Workflow**

1.  **Analyze Assertion (A):** Independently evaluate the truthfulness of the Assertion statement. Determine if it is **True** or **False** and note the reasoning.
2.  **Analyze Reason (R):** Independently evaluate the truthfulness of the Reason statement. Determine if it is **True** or **False** and note the reasoning.
3.  **Analyze Relationship:**
    *   If **both A and R are True**, determine if R is the correct and direct explanation for A.
    *   If either statement is False, this analysis is not applicable.
4.  **Determine Correct Option:** Based on your analysis, select the correct option (A, B, C, or D) using the standard definitions.

---

### **2. JSON Output Structure**

Your output **MUST** be a single, valid JSON object conforming to this exact schema.

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

### **3. Field-by-Field Generation Logic**

#### **`ques_identifier`**
- **Source:** Extract the `Question ID` from the user prompt.
- **Action:** Copy it verbatim into this field.

#### **`total_marks`**
- **Source:** Extract the `Total Marks` from the user prompt.
- **Action:** Convert the value to a floating-point number (e.g., `1.0`).

#### **`correct_option`**
- **Source:** Your final determination from the **Analysis Workflow**.
- **Action:** Provide the correct option letter ("A", "B", "C", or "D") as a string.

#### **`acceptable_answers`**
- **Source:** Based on the `correct_option`.
- **Action:** Create a JSON array of strings with all reasonable formats. This **MUST** include:
  1. The uppercase letter (e.g., `"A"`)
  2. The lowercase letter (e.g., `"a"`)
  3. The option with parentheses (e.g., `"Option A (a)"`)
  4. The full text of the correct option's definition (e.g., `"Both A and R are true and R is the correct explanation of A"`).

#### **`solution`**
- **Source:** Your expert analysis from the **Analysis Workflow**.
- **Action:** Provide a brief, clear, and direct explanation for the correct option. The explanation should state the truthfulness of both the Assertion and the Reason and explain their relationship.
  - **Example for Option A:** "Assertion (A) is true because... Reason (R) is also true because... and R correctly explains A because..."
  - **Example for Option C:** "Assertion (A) is true because... However, Reason (R) is false because..."

---

### **4. Final Review**

- **Confirm Schema:** Ensure your output is a valid JSON object matching the specified structure.
- **No Extra Text:** Do not include any text, markdown, or explanations outside the JSON object.