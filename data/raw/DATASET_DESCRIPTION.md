# Dataset Card: Mizoram-MCQ-Bench (LLM Evaluation Benchmark)

## 1. Dataset Overview
**`Mizoram-MCQ-Bench`** is a standardized, high-stakes evaluation benchmark designed to measure the regional factual knowledge, cultural understanding, and reasoning capabilities of Large Language Models (LLMs) on indigenous and regional domain knowledge of Mizoram, Northeast India.

- **Primary File**: `mizoram_mcq_with_answers.json`
- **Full Benchmark (Multi-format)**: `mizoram_llm_eval_benchmark.json`
- **File Format**: JSON (`UTF-8`), 1.70 MB
- **Task Type**: 4-Option Multiple Choice Question Answering (MCQ-QA), Chain-of-Thought (CoT) Reasoning, Cultural Alignment Evaluation

---

## 2. Key Dataset Metrics

| Metric | Value |
| :--- | :--- |
| **Total Benchmark MCQs** | **2,400** |
| **Ground-Truth Answer Key Coverage** | **100.0% (2,400 / 2,400)** |
| **Answer Text Coverage** | **100.0% (2,400 / 2,400)** |
| **Reference Explanation Coverage** | **100.0% (2,400 / 2,400)** |
| **Language Distribution** | English (97.9%), Mizo language items (2.1%) |
| **Current Affairs Contamination** | **0.0%** (All ephemeral/news questions strictly filtered out) |

---

## 3. Knowledge Domain Taxonomy

The dataset is categorized across **8 core knowledge domains**:

| Category | Questions | % Share | Focus Areas / Topics |
| :--- | :---: | :---: | :--- |
| **History** | **650** | 27.1% | Chieftainship era, British annexation, Lushai Hills district, 1986 Mizoram Peace Accord, 1987 Statehood, MNF movement, historical figures. |
| **General Knowledge** | **604** | 25.2% | State symbols (*Vavu*, *Saza*, *Senhri*, *Herhse*), state firsts, civilian/gallantry awards, notable state landmarks and milestones. |
| **Law & Acts** | **403** | 16.8% | Mizo Customary Law, MLPC Act, Mizoram Shops & Establishment Act, Village Council enactments, State Civil Service regulations. |
| **Geography** | **256** | 10.7% | Major rivers (*Tlawng*, *Tuirial*, *Chhimtuipui/Kolodyne*), mountain peaks (*Phawngpui*), 11 district boundaries, international borders (Myanmar & Bangladesh). |
| **Culture & Literature** | **239** | 10.0% | Cultural festivals (*Chapchar Kut*, *Pawl Kut*, *Mim Kut*), social customs (*Tlawmngaihna*, *Zawlbuk*), folklore, Mizo literature, poetry, and grammar. |
| **Polity & Governance** | **112** | 4.7% | Sixth Schedule of Indian Constitution, Autonomous District Councils (CADC, LADC, MADC), Village Councils, State Legislative Assembly. |
| **Economy & Agriculture** | **90** | 3.8% | Jhum cultivation (*Hnunpui/Hnuhhram lak*), horticulture, bamboo flowering (*Mautam*, *Thingtam*), border trade (*Zokhawthar*), state infrastructure. |
| **Environment & Wildlife** | **46** | 1.9% | Protected areas and Wildlife Sanctuaries (*Dampa*, *Murlen*, *Lengteng*, *Ngengpui*, *Phawngpui*), endemic flora and fauna. |
| **Total** | **2,400** | **100.0%** | |

---

## 4. Source & Ground-Truth Provenance
- **Authentic Statutory Source**: All questions originate from official civil service and competitive examinations in Mizoram (including the Mizoram Public Service Commission / MPSC, Mizoram Civil Services / MCS, Departmental Selection Examinations, and Engineering/Technical Services).
- **Official Ground Truth**: All answers and explanations correspond to official verified examiner answer keys.
- **Static Evaluation Integrity**: To prevent temporal decay and benchmark obsolescence, all time-sensitive Current Affairs questions and temporary administrative appointments have been purged.

---

## 5. JSON Schema & Data Format

Each item in `mizoram_mcq_with_answers.json` follows this standard schema:

```json
{
  "id": "c1a63c6c-ddfc-444f-9e79-ddae5bfa2fb5",
  "category": "Culture & Literature",
  "sub_category": "Mizoram Culture/Language",
  "language": "English",
  "question": "From the linguistic point of view, the Mizo language belongs to the —",
  "choices": {
    "A": "Tibeto-Burman family",
    "B": "The Mongoloid family",
    "C": "Dravidians family",
    "D": "Aryan family"
  },
  "answer": "A",
  "answer_text": "Tibeto-Burman family",
  "explanation": "Mizo belongs to the Tibeto-Burman branch of the Sino-Tibetan language family.",
  "source_exam": "MPSC Combined Competitive Exam",
  "source_paper": "General Studies Paper I",
  "source_year": 2022
}
```

### Field Definitions:
- `id` *(string, UUID)*: Unique identifier for the benchmark item.
- `category` *(string)*: Primary knowledge domain (one of the 8 standardized domains).
- `sub_category` *(string)*: Granular sub-topic within the domain.
- `language` *(string)*: Primary language of the question text (`"English"` or `"Mizo"`).
- `question` *(string)*: The question prompt.
- `choices` *(object)*: Map of choice labels (`"A"`, `"B"`, `"C"`, `"D"`) to choice text.
- `answer` *(string)*: The ground-truth correct option letter (`"A"`, `"B"`, `"C"`, or `"D"`).
- `answer_text` *(string)*: The exact text of the correct choice.
- `explanation` *(string)*: Reference rationale for Chain-of-Thought (CoT) and multi-step reasoning validation.
- `source_exam` *(string)*: Originating examination.
- `source_paper` *(string)*: Exam paper name.
- `source_year` *(integer)*: Examination year.

---

## 6. Recommended Evaluation Protocols

1. **Zero-Shot Prompting**:
   ```
   Question: {question}
   Options:
   A. {choices[A]}
   B. {choices[B]}
   C. {choices[C]}
   D. {choices[D]}

   Answer with the correct option letter (A, B, C, or D) only.
   ```
2. **Chain-of-Thought (CoT) / Reasoning Evaluation**:
   Prompt the LLM to output step-by-step reasoning before generating the final answer tag `[ANSWER: X]`, comparing the generated rationale against the `explanation` field.
3. **Retrieval-Augmented Generation (RAG) Evaluation**:
   Evaluate LLMs with and without domain retrieval context (e.g. Mizoram state acts, gazettes, history documents) to measure hallucination reduction and retrieval efficiency.
