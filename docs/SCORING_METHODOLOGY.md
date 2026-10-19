# Scoring Methodology: Estimated Resume–Job Match Score

## 1. Ethical & Regulatory Principles

- **No False Claims**: This engine does not claim to represent any employer's proprietary ATS algorithm, guarantee interview selection, or validate hiring suitability. It calculates a deterministic, explainable heuristic proxy labeled **"Estimated Resume–Job Match Score"**.
- **Non-Discrimination**: The scoring engine never penalizes candidates for protected characteristics (age, gender, ethnicity, location, disability status) and does not infer sensitive personal traits.
- **Honesty in Recommendations**: Improvement recommendations strictly encourage candidates to highlight genuine, existing competencies. They never encourage fabricating qualifications or misrepresenting work history.

---

## 2. Category Weight Allocation (0 to 100 Points)

| Category | Weight | Description |
| :--- | :---: | :--- |
| **Job-Relevant Keyword Coverage** | **35 pts** | Unique keyword alignment across normalized job vocabulary. |
| **Required & Preferred Skills Match** | **25 pts** | Exact & synonym skill matches, weighting mandatory vs preferred skills. |
| **Relevant Experience Evidence** | **20 pts** | Action verbs, quantified impact metrics, duration & section integrity. |
| **Education & Qualifications** | **10 pts** | Degree levels, relevant fields of study, and formal education section. |
| **Document Structure & Readability** | **10 pts** | Standard ATS-readable section headings, formatting, and content length. |
| **Total Maximum Score** | **100 pts** | Deterministic score strictly bounded within $[0.0, 100.0]$. |

---

## 3. Mathematical Formulation & Normalization

### 3.1 Job-Relevant Keyword Coverage ($W_1 = 35$)

- **Vocabulary Extraction**: Filters out common English stopwords, numbers, and boilerplate recruitment language from the job description to produce a target set of unique keywords $K_{\text{job}} = \{k_1, k_2, \dots, k_N\}$.
- **Binary Term Match**: For each $k_i \in K_{\text{job}}$, the system evaluates whether $k_i$ (or any of its known synonyms) is present in the normalized resume text.
- **Repeated Keyword Protection**:
  $$\text{Matched Keywords} = \sum_{k_i \in K_{\text{job}}} \mathbb{I}(\text{term } k_i \text{ exists in resume})$$
  Repeated mentions of the same keyword in the resume do **not** increase the score, preventing keyword stuffing.
- **Score Calculation**:
  $$\text{Score}_{\text{kw}} = \min\left(35.0, \text{round}\left(35.0 \times \frac{|\text{Matched Keywords}|}{|K_{\text{job}}|}, 2\right)\right)$$

### 3.2 Required & Preferred Skills Match ($W_2 = 25$)

- **Skills Classification**:
  - **Mandatory Requirements ($M$)**: Extracted from "Minimum Qualifications", "Requirements", or bullet items with "must"/"required". Weight: 70% of category ($17.5$ pts).
  - **Preferred Requirements ($P$)**: Extracted from "Preferred Qualifications", "Nice to have", or "Bonus". Weight: 30% of category ($7.5$ pts).
  - If preferred requirements are not explicitly delineated in the job description, the full 25 points are allocated to mandatory/detected core competencies.
- **Evidence Strength Grading**:
  - Term located within an explicit "Skills" or "Work Experience" section: full credit ($1.0$).
  - Term located in incidental body text: partial evidence credit ($0.75$).

### 3.3 Relevant Experience Evidence ($W_3 = 20$)

Evaluates the qualitative depth of professional history:
1. **Experience Section Presence (5.0 pts)**: Detects standard professional history headers (`Work Experience`, `Professional Experience`, `Employment History`).
2. **Action Verbs Diversity (5.0 pts)**: Evaluates high-impact past-tense verbs demonstrating active ownership (e.g., `Architected`, `Engineered`, `Optimized`, `Spearheaded`).
   - $\ge 5$ distinct verbs: $5.0$ pts
   - $3 - 4$ verbs: $3.5$ pts
   - $1 - 2$ verbs: $2.0$ pts
   - $0$ verbs: $0.0$ pts
3. **Quantified Impact & Metrics (5.0 pts)**: Identifies tangible achievement metrics (percentages, monetary savings/budgets, user scaling counts, latency reductions).
   - $\ge 3$ quantified metrics: $5.0$ pts
   - $1 - 2$ metrics: $3.0$ pts
   - $0$ metrics: $0.0$ pts
4. **Experience Duration Alignment (5.0 pts)**: Compares required years of experience against candidate timeline indicators. Full credit ($5.0$ pts) if stated threshold is met.

### 3.4 Education & Qualifications ($W_4 = 10$)

1. **Education Section Presence (4.0 pts)**: Identifies dedicated academic credentials section.
2. **Degree Alignment (6.0 pts)**:
   - Matches stated degree requirements (Associate, Bachelor's, Master's, Ph.D.).
   - If job requires a Bachelor's degree and candidate holds a Bachelor's or Master's: $6.0$ pts.
   - If job does not specify a mandatory degree level, any documented post-secondary degree earns $6.0$ pts.

### 3.5 Document Structure & Readability ($W_5 = 10$)

1. **Section Organization (4.0 pts)**: Detects standard ATS-recognized section headers (Experience, Education, Skills, Projects, Summary). $\ge 3$ sections: $4.0$ pts.
2. **Content Length & Density (3.0 pts)**: Optimal professional resume length is $250 - 1500$ words ($3.0$ pts). Sparse documents ($<150$ words) or overly verbose documents ($>2500$ words) receive reduced marks.
3. **Bullet Point Structure (3.0 pts)**: Rewards scannable bullet points over dense, unformatted paragraphs. $\ge 5$ bullets: $3.0$ pts.

---

## 4. Match Tier Classification

| Overall Score Range | Match Tier | Guidance |
| :---: | :---: | :--- |
| **85.0 – 100.0** | **Exceptional Match** | High alignment across keywords, core skills, experience metrics, and formatting. |
| **70.0 – 84.9** | **Strong Match** | Solid candidate profile meeting primary qualifications with minor keyword/formatting gaps. |
| **55.0 – 69.9** | **Good Match** | Core competencies are evidenced, but specific secondary requirements or metrics need polish. |
| **40.0 – 54.9** | **Fair Match** | Noticeable gaps in required skills, experience alignment, or document structure. |
| **0.0 – 39.9** | **Low Match** | Significant mismatch with job requirements or minimal document evidence. |

---

## 5. Synonym Resolution and Boundary Protection

The engine utilizes a normalized synonym dictionary mapping common abbreviations and variant spellings to canonical concepts:
- Example: `k8s` $\rightarrow$ `kubernetes`, `py` $\rightarrow$ `python`, `js` $\rightarrow$ `javascript`, `postgres` $\rightarrow$ `postgresql`.
- Uses word boundary regex patterns (`\b...\b`) to avoid false-positive substrings (e.g., ensuring `c` does not match `cloud`, or `go` does not match `good`).
