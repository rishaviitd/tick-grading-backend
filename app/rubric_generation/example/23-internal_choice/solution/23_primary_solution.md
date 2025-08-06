# Solution for 23_primary

**Question:** 23. (a) Find the smallest number which is divisible by both 644 and 462.

**Question Type:** Subjective

---

**Reasoning:**
- This question has no sub-parts. It is worth 2 marks, requiring [2 to 4] steps for the entire solution. **I will strictly adhere to this step count for each method.**
- Bloom's Level: Applying.

**Method solution:**
- Method 1: The plan is to find the prime factorization of each number, identify the highest power of each prime factor present in either factorization, and then multiply these to find the LCM.
- Method 2: The plan is to first find the GCD of the two numbers using the Euclidean algorithm, then calculate the product of the two numbers, and finally use the formula LCM(a, b) = (a × b) / GCD(a, b) to find the LCM.

---
**Method 1: Prime Factorization Approach**
---
- Step 1:
  - Step ID: 1
  - Teacher Expectation: Performs the prime factorization of 644.
  - Pass if: Correctly states the prime factorization of 644 as 2² × 7 × 23.
  - Fail if: Makes an error in the prime factorization process or the resulting factors.
  - Mark Type: M
- Step 2:
  - Step ID: 2
  - Teacher Expectation: Performs the prime factorization of 462.
  - Pass if: Correctly states the prime factorization of 462 as 2 × 3 × 7 × 11.
  - Fail if: Makes an error in the prime factorization process or the resulting factors.
  - Mark Type: M
- Step 3:
  - Step ID: 3
  - Teacher Expectation: Identifies the highest power of each prime factor present in the factorizations of 644 and 462.
  - Pass if: Correctly identifies the required prime factors and their highest powers: 2² (from 644), 3¹ (from 462), 7¹ (common to both), 11¹ (from 462), 23¹ (from 644).
  - Fail if: Misses any prime factor, uses incorrect powers, or incorrectly identifies common factors.
  - Mark Type: M
- Step 4:
  - Step ID: 4
  - Teacher Expectation: Calculates the Least Common Multiple (LCM) by multiplying the identified highest powers of prime factors.
  - Pass if: Correctly calculates the LCM as 2² × 3 × 7 × 11 × 23 = 21252.
  - Fail if: Makes a calculation error in multiplying the prime factors.
  - Mark Type: A

---
**Method 2: Using GCD Formula**
---
- Step 1:
  - Step ID: 1
  - Teacher Expectation: Calculates the GCD of 644 and 462 using the Euclidean Algorithm.
  - Pass if: Correctly performs the divisions and identifies the GCD as 14 (e.g., 644 = 1×462 + 182, 462 = 2×182 + 98, 182 = 1×98 + 84, 98 = 1×84 + 14, 84 = 6×14 + 0; GCD=14).
  - Fail if: Makes an error in the Euclidean algorithm or incorrectly identifies the GCD.
  - Mark Type: M
- Step 2:
  - Step ID: 2
  - Teacher Expectation: Calculates the product of the two numbers, 644 and 462.
  - Pass if: Correctly calculates 644 × 462 = 297528.
  - Fail if: Makes a calculation error in the multiplication.
  - Mark Type: M
- Step 3:
  - Step ID: 3
  - Teacher Expectation: States and correctly applies the formula LCM(a, b) = (a × b) / GCD(a, b).
  - Pass if: Sets up the calculation as LCM = 297528 / 14.
  - Fail if: Uses an incorrect formula or substitutes incorrect values.
  - Mark Type: M
- Step 4:
  - Step ID: 4
  - Teacher Expectation: Computes the final LCM by dividing the product by the GCD.
  - Pass if: Correctly calculates the LCM as 297528 / 14 = 21252.
  - Fail if: Makes a calculation error in the division.
  - Mark Type: A